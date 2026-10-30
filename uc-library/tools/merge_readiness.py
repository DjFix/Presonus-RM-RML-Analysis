#!/usr/bin/env python3
"""Admit source-bound worker proofs after shared build/format validation."""
import argparse
import hashlib
import json
import stat
from collections import OrderedDict
from pathlib import Path


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


class ValidationCache:
    """Fresh, operation-local file checks, with final path/stat race guards."""
    def __init__(self):
        self.paths = {}
        self.files = {}
        self.json = OrderedDict()
        self.repository_domains = {}

    @staticmethod
    def fingerprint(value):
        return (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns)

    def resolve(self, path):
        path = Path(path).absolute()
        if path not in self.paths:
            self.paths[path] = path.resolve()
        return self.paths[path]

    def is_file(self, path):
        return self.resolve(path).is_file()

    def sha(self, path):
        path = self.resolve(path)
        if path not in self.files:
            before = path.stat()
            assert stat.S_ISREG(before.st_mode), f'not a regular evidence file: {path}'
            digest = hashlib.sha256()
            with path.open('rb') as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b''):
                    digest.update(block)
            after = path.stat()
            assert self.fingerprint(before) == self.fingerprint(after), f'evidence changed while hashing: {path}'
            self.files[path] = (digest.hexdigest(), self.fingerprint(after))
        return self.files[path][0]

    def read_json(self, path):
        path = self.resolve(path)
        if path in self.json:
            self.json.move_to_end(path)
            return self.json[path]
        expected = self.sha(path)
        raw = path.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == expected, f'evidence changed while parsing: {path}'
        value = json.loads(raw)
        self.json[path] = value
        if len(self.json) > 8:
            self.json.popitem(last=False)
        return value

    def unchanged(self):
        for original, resolved in self.paths.items():
            assert original.resolve() == resolved, f'evidence path changed: {original}'
        for path, (_, before) in self.files.items():
            assert self.fingerprint(path.stat()) == before, f'evidence changed after validation: {path}'


def repository_sources_match(library, entry, cache=None):
    """Check pinned Core source dependencies with an explicit repository anchor."""
    sources = entry.get('repository_sources', {})
    if not isinstance(sources, dict):
        return False
    if not sources:
        return True
    if cache is not None and id(sources) in cache.repository_domains:
        return cache.repository_domains[id(sources)] is sources
    resolve = cache.resolve if cache is not None else lambda path: path.resolve()
    digest_file = cache.sha if cache is not None else sha
    repository = next((parent for parent in resolve(library).parents
                       if (parent/'third_party/ccl-framework/core').is_dir()), None)
    if repository is None:
        return False
    core = resolve(repository/'third_party/ccl-framework/core')
    for name, digest in sources.items():
        relative = Path(name)
        if relative.is_absolute() or relative.parts[:3] != ('third_party','ccl-framework','core'):
            return False
        path = resolve(repository/relative)
        if not path.is_relative_to(core) or not path.is_file() or digest_file(path) != digest:
            return False
    if cache is not None:
        cache.repository_domains[id(sources)] = sources
    return True


def proof_covers(proof,entry):
    passed=proof.get('cpp_differential_passed',proof.get('arm_differential_passed',False))
    checked=proof.get('compiled_mangled_names_matched',proof.get('compiled_original_mangled_names_matched',proof.get('mangling_namespace_checked',False)))
    detailed=proof.get('functions',[])
    names=proof.get('mangled_names',[item.get('mangled') for item in detailed if isinstance(item,dict)] or [proof.get('mangled')])
    if passed is not True or checked is not True or proof.get('portable_ready',True) is not True or entry['mangled'] not in names:
        return False
    if any(isinstance(item,dict) and 'original_elf_sha256' in item for item in detailed):
        return any(isinstance(item,dict) and item.get('mangled')==entry['mangled'] and item.get('original_elf_sha256')==entry['original_elf_sha256'] for item in detailed)
    return True


def main():
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent/'registry'))
    import adapter
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--library',type=Path,required=True)
    p.add_argument('--registry-db',type=Path,help='Explicit SQLite working registry; defaults to ACTIVE.json')
    p.add_argument('--fragment',type=Path,action='append',default=[])
    p.add_argument('--sealed-index',type=Path,action='append',default=[])
    p.add_argument('--pending',type=Path,action='append',default=[])
    p.add_argument('--demote',type=Path,action='append',default=[],
                   help='Explicit guarded ready-to-pending transition manifest; requires fresh pending proof')
    p.add_argument('--dry-run',action='store_true',help='Validate without changing SQLite; legacy JSON is never written')
    a=p.parse_args()
    library=a.library.resolve()
    cache=ValidationCache()
    read_json=cache.read_json
    with adapter.snapshot(library,a.registry_db) as current:
        previous_ready=current.ready
        previous_pending=current.pending
        expected_guard=current.guard
        database=current.db
    formatting=read_json(library/'validation/formatting.json')
    integration=read_json(library/'validation/integration.json')
    assert formatting['format_check_passed'] and integration['ctest_passed']
    for name,digest in integration['files'].items():
        assert cache.sha(library/name)==digest,f'integration evidence stale: {name}'
    originals={}
    for role in ('client','server'):
        root=library/'recovered-all'/role
        manifest=read_json(root/'manifest.json')
        for sym in read_json(root/'symbols.json'):
            if sym['kind']=='STT_FUNC' and isinstance(sym['section'],int) and sym['size']:
                originals.setdefault((manifest['sha256'],sym['mangled']),[]).append(sym['address'])
    checked_sources={}
    def check_sources(sources):
        assert isinstance(sources,dict), 'source bindings must be a dictionary'
        if checked_sources.get(id(sources)) is sources:
            return
        for name,digest in sources.items():
            path=cache.resolve(library/name)
            assert path.is_relative_to(library) and path.is_file(),f'source outside current library: {name}'
            assert cache.sha(path)==digest,f'stale source seal: {name}'
            if path.suffix in ('.cpp','.hpp','.h'):
                assert formatting['files'].get(name)==digest,f'source not format-checked: {name}'
        checked_sources[id(sources)]=sources
    candidates=[]
    for relative in a.fragment:
        candidates.extend(read_json(library/relative)['functions'])
    for relative in a.sealed_index:
        index=read_json(library/relative)
        for entry in index['records']:
            proof=read_json(library/entry['validation'])
            candidates.append(dict(mangled=entry['mangled'],original_elf_sha256=proof['original_elf_sha256'],
                validation=entry['validation'],validation_sha256=entry['validation_sha256'],sources=proof['sources'],
                domain=proof['domain'],portable_ready=proof['portable_ready']))
    new_keys={(entry['original_elf_sha256'],entry['mangled']) for entry in candidates}
    demotions={}
    demotion_inputs={}
    for relative in a.demote:
        path=cache.resolve(library/relative)
        assert path.is_relative_to(library) and path.is_file(),'demotion manifest outside library'
        payload=read_json(path)
        for entry in payload['demotions']:
            key=(entry['original_elf_sha256'],entry['mangled'])
            assert key not in demotions and key not in new_keys,'conflicting ready/demotion input'
            assert isinstance(entry.get('reason'),str) and entry['reason'].strip()
            assert isinstance(entry.get('previous_validation_sha256'),str)
            demotions[key]=entry
        demotion_inputs[str(relative)]=cache.sha(path)
    demotions_checked=set()
    stale_previous=[]
    if previous_ready:
        for entry in previous_ready.get('functions',[]):
            key=(entry['original_elf_sha256'],entry['mangled'])
            if key in demotions:
                assert entry['validation_sha256']==demotions[key]['previous_validation_sha256'],'demotion previous proof changed'
                demotions_checked.add(key)
                continue
            if key in new_keys:continue
            try:
                check_sources(entry['sources'])
                assert repository_sources_match(library,entry,cache), 'upstream source dependency changed'
                assert cache.sha(library/entry['validation'])==entry['validation_sha256']
            except (AssertionError,FileNotFoundError):
                stale_previous.append(entry['mangled'])
                continue
            candidates.append(entry)
    assert demotions_checked==set(demotions),'demotion must identify an existing ready entry'
    records={}
    for entry in candidates:
        assert isinstance(entry.get('domain'),str) and entry['domain'].strip(), 'ready record must state its bounded validation domain'
        key=(entry['original_elf_sha256'],entry['mangled'])
        assert key in originals,f'no original symbol for proof: {key}'
        if 'original_address' in entry:assert entry['original_address'] in originals[key]
        path=library/entry['validation']
        assert cache.sha(path)==entry['validation_sha256'],f'proof digest mismatch: {path}'
        proof=read_json(path)
        assert proof_covers(proof,entry),'proof does not cover this original ELF/symbol pair with passing checks'
        assert entry.get('portable_ready') is True and proof.get('portable_ready',True) is True
        check_sources(entry['sources'])
        assert repository_sources_match(library,entry,cache), 'upstream source dependency changed'
        entry=dict(entry)
        entry.update(original_function_verified=False,hardware_verified=False,
                     declaration_uncertainties=entry.get('declaration_uncertainties',entry.get('method_declaration_uncertainties',proof.get('declaration_uncertainties',proof.get('return_declaration_choices',proof.get('limitations',[]))))),
                     formatting_reference='validation/formatting.json',
                     formatting_sha256=cache.sha(library/'validation/formatting.json'))
        records[key]=entry
    compiled_map={}
    for relative in a.pending:
        path=library/relative
        payload=read_json(path)
        pending_entries=payload.get('functions',[]) if isinstance(payload,dict) else payload
        assert isinstance(pending_entries,list),'pending proof must contain function records'
        for entry in pending_entries:
            key=(entry['original_elf_sha256'],entry['mangled'])
            assert key in originals and entry.get('portable_ready') is False
            assert entry.get('cpp_compiled') is True and entry.get('mangling_namespace_checked') is True
            check_sources(entry['sources'])
            assert repository_sources_match(library,entry,cache), 'upstream source dependency changed'
            if entry.get('validation'):
                assert cache.sha(library/entry['validation'])==entry['validation_sha256'],'pending compile evidence digest mismatch'
                entry=dict(entry,behavior_validation=entry['validation'],behavior_validation_sha256=entry['validation_sha256'])
            compiled_map[key]=dict(entry,validation=str(relative),validation_sha256=cache.sha(path))
    assert set(demotions)<=set(compiled_map),'demotion requires a fresh validated pending fragment'
    assert not set(records)&set(compiled_map),'same symbol supplied as ready and pending'
    promoted_pending=[]
    stale_pending=[]
    if previous_pending:
        for entry in previous_pending.get('functions',[]):
            key=(entry['original_elf_sha256'],entry['mangled'])
            if key in compiled_map:continue
            if key in new_keys:
                assert key in records
                promoted_pending.append(dict(original_elf_sha256=key[0],mangled=key[1]))
                continue
            try:
                check_sources(entry['sources'])
                assert repository_sources_match(library,entry,cache), 'upstream source dependency changed'
                assert cache.sha(library/entry['validation'])==entry['validation_sha256']
            except (AssertionError,FileNotFoundError):
                stale_pending.append(dict(original_elf_sha256=key[0],mangled=key[1]))
                continue
            compiled_map[key]=entry
    assert not set(records)&set(compiled_map),'canonical ready and pending ledgers must be disjoint'
    compiled=[compiled_map[key] for key in sorted(compiled_map)]
    demoted=[dict(demotions[key]) for key in sorted(demotions)]
    assert not stale_previous and not stale_pending, (
        'Stale admitted records require fresh replacement proofs or explicit guarded review; '
        f'ready={stale_previous}, pending={stale_pending}')
    cache.unchanged()
    if a.dry_run:
        print(json.dumps({'validated_only':True,'portable_ready_entries':len(records),
            'unique_mangled_methods':len({key[1] for key in records}),
            'compiled_declaration_pending_entries':len(compiled),
            'stale_previous_entries':stale_previous,'demoted_entries':demoted,
            'promoted_pending_entries':promoted_pending},indent=2))
        return
    # Do not silently erase a previously admitted symbol when evidence is stale.
    # The complete prior generation remains in the DB/backup; explicit guarded
    # classification transitions are separate from source freshness failures.
    ready_metadata={key:value for key,value in previous_ready.items() if key!='functions'}
    ready_metadata.update(integration_reference='validation/integration.json',original_full_verification=False)
    pending_metadata={key:value for key,value in previous_pending.items() if key!='functions'}
    committed=adapter.commit_snapshot(
        [records[key] for key in sorted(records)],compiled,expected_guard,library=library,db=database,
        actor='merge_readiness.py',reason='Source-bound admission after full current proof validation',
        demotions=demoted,promotions=promoted_pending,
        metadata={'ready':ready_metadata,'pending':pending_metadata},
        demotion_manifests=demotion_inputs,
        operation_metadata={'integration_reference':'validation/integration.json',
                            'formatting_sha256':cache.sha(library/'validation/formatting.json')},
        precommit_guard=cache.unchanged)
    print(json.dumps({'portable_ready_entries':len(records),'unique_mangled_methods':len({k[1] for k in records}),
                      'compiled_declaration_pending_entries':len(compiled),'stale_previous_entries':stale_previous,
                      'demoted_entries':demoted,'promoted_pending_entries':promoted_pending,
                      'full_original_verification':False,'sqlite_commit':committed},indent=2))


if __name__=='__main__':main()
