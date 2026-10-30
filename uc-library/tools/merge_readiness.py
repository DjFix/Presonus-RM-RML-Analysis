#!/usr/bin/env python3
"""Admit source-bound worker proofs after shared build/format validation."""
import argparse
import hashlib
import json
from pathlib import Path


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def repository_sources_match(library, entry):
    """Check pinned Core source dependencies with an explicit repository anchor."""
    sources = entry.get('repository_sources', {})
    if not isinstance(sources, dict):
        return False
    if not sources:
        return True
    repository = next((parent for parent in library.resolve().parents
                       if (parent/'third_party/ccl-framework/core').is_dir()), None)
    if repository is None:
        return False
    core = (repository/'third_party/ccl-framework/core').resolve()
    for name, digest in sources.items():
        relative = Path(name)
        if relative.is_absolute() or relative.parts[:3] != ('third_party','ccl-framework','core'):
            return False
        path = (repository/relative).resolve()
        if not path.is_relative_to(core) or not path.is_file() or sha(path) != digest:
            return False
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
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--library',type=Path,required=True)
    p.add_argument('--fragment',type=Path,action='append',default=[])
    p.add_argument('--sealed-index',type=Path,action='append',default=[])
    p.add_argument('--pending',type=Path,action='append',default=[])
    p.add_argument('--demote',type=Path,action='append',default=[],
                   help='Explicit guarded ready-to-pending transition manifest; requires fresh pending proof')
    p.add_argument('--dry-run',action='store_true',help='Validate and report without writing ledgers/history')
    a=p.parse_args()
    library=a.library.resolve()
    formatting=json.loads((library/'validation/formatting.json').read_text())
    integration=json.loads((library/'validation/integration.json').read_text())
    assert formatting['format_check_passed'] and integration['ctest_passed']
    for name,digest in integration['files'].items():
        assert sha(library/name)==digest,f'integration evidence stale: {name}'
    originals={}
    for role in ('client','server'):
        root=library/'recovered-all'/role
        manifest=json.loads((root/'manifest.json').read_text())
        for sym in json.loads((root/'symbols.json').read_text()):
            if sym['kind']=='STT_FUNC' and isinstance(sym['section'],int) and sym['size']:
                originals.setdefault((manifest['sha256'],sym['mangled']),[]).append(sym['address'])
    def check_sources(sources):
        for name,digest in sources.items():
            path=(library/name).resolve()
            assert path.is_relative_to(library) and path.is_file(),f'source outside current library: {name}'
            assert sha(path)==digest,f'stale source seal: {name}'
            if path.suffix in ('.cpp','.hpp','.h'):
                assert formatting['files'].get(name)==digest,f'source not format-checked: {name}'
    candidates=[]
    for relative in a.fragment:
        candidates.extend(json.loads((library/relative).read_text())['functions'])
    for relative in a.sealed_index:
        index=json.loads((library/relative).read_text())
        for entry in index['records']:
            proof=json.loads((library/entry['validation']).read_text())
            candidates.append(dict(mangled=entry['mangled'],original_elf_sha256=proof['original_elf_sha256'],
                validation=entry['validation'],validation_sha256=entry['validation_sha256'],sources=proof['sources'],
                domain=proof['domain'],portable_ready=proof['portable_ready']))
    target=library/'validation/ready-functions.json'
    new_keys={(entry['original_elf_sha256'],entry['mangled']) for entry in candidates}
    demotions={}
    demotion_inputs={}
    for relative in a.demote:
        path=(library/relative).resolve()
        assert path.is_relative_to(library) and path.is_file(),'demotion manifest outside library'
        payload=json.loads(path.read_text())
        for entry in payload['demotions']:
            key=(entry['original_elf_sha256'],entry['mangled'])
            assert key not in demotions and key not in new_keys,'conflicting ready/demotion input'
            assert isinstance(entry.get('reason'),str) and entry['reason'].strip()
            assert isinstance(entry.get('previous_validation_sha256'),str)
            demotions[key]=entry
        demotion_inputs[str(relative)]=sha(path)
    demotions_checked=set()
    stale_previous=[]
    if target.exists():
        for entry in json.loads(target.read_text()).get('functions',[]):
            key=(entry['original_elf_sha256'],entry['mangled'])
            if key in demotions:
                assert entry['validation_sha256']==demotions[key]['previous_validation_sha256'],'demotion previous proof changed'
                demotions_checked.add(key)
                continue
            if key in new_keys:continue
            try:
                check_sources(entry['sources'])
                assert repository_sources_match(library,entry), 'upstream source dependency changed'
                assert sha(library/entry['validation'])==entry['validation_sha256']
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
        assert sha(path)==entry['validation_sha256'],f'proof digest mismatch: {path}'
        proof=json.loads(path.read_text())
        assert proof_covers(proof,entry),'proof does not cover this original ELF/symbol pair with passing checks'
        assert entry.get('portable_ready') is True and proof.get('portable_ready',True) is True
        check_sources(entry['sources'])
        assert repository_sources_match(library,entry), 'upstream source dependency changed'
        entry=dict(entry)
        entry.update(original_function_verified=False,hardware_verified=False,
                     declaration_uncertainties=entry.get('declaration_uncertainties',entry.get('method_declaration_uncertainties',proof.get('declaration_uncertainties',proof.get('return_declaration_choices',proof.get('limitations',[]))))),
                     formatting_reference='validation/formatting.json',
                     formatting_sha256=sha(library/'validation/formatting.json'))
        records[key]=entry
    compiled_map={}
    for relative in a.pending:
        path=library/relative
        payload=json.loads(path.read_text())
        pending_entries=payload.get('functions',[]) if isinstance(payload,dict) else payload
        assert isinstance(pending_entries,list),'pending proof must contain function records'
        for entry in pending_entries:
            key=(entry['original_elf_sha256'],entry['mangled'])
            assert key in originals and entry.get('portable_ready') is False
            assert entry.get('cpp_compiled') is True and entry.get('mangling_namespace_checked') is True
            check_sources(entry['sources'])
            assert repository_sources_match(library,entry), 'upstream source dependency changed'
            if entry.get('validation'):
                assert sha(library/entry['validation'])==entry['validation_sha256'],'pending compile evidence digest mismatch'
                entry=dict(entry,behavior_validation=entry['validation'],behavior_validation_sha256=entry['validation_sha256'])
            compiled_map[key]=dict(entry,validation=str(relative),validation_sha256=sha(path))
    assert set(demotions)<=set(compiled_map),'demotion requires a fresh validated pending fragment'
    assert not set(records)&set(compiled_map),'same symbol supplied as ready and pending'
    old_compiled=library/'validation/compiled-functions.json'
    promoted_pending=[]
    if old_compiled.exists():
        for entry in json.loads(old_compiled.read_text()).get('functions',[]):
            key=(entry['original_elf_sha256'],entry['mangled'])
            if key in compiled_map:continue
            if key in new_keys:
                assert key in records
                promoted_pending.append(dict(original_elf_sha256=key[0],mangled=key[1]))
                continue
            try:
                check_sources(entry['sources'])
                assert repository_sources_match(library,entry), 'upstream source dependency changed'
                assert sha(library/entry['validation'])==entry['validation_sha256']
            except (AssertionError,FileNotFoundError):continue
            compiled_map[key]=entry
    assert not set(records)&set(compiled_map),'canonical ready and pending ledgers must be disjoint'
    compiled=[compiled_map[key] for key in sorted(compiled_map)]
    demoted=[dict(demotions[key]) for key in sorted(demotions)]
    if a.dry_run:
        print(json.dumps({'validated_only':True,'portable_ready_entries':len(records),
            'unique_mangled_methods':len({key[1] for key in records}),
            'compiled_declaration_pending_entries':len(compiled),
            'stale_previous_entries':stale_previous,'demoted_entries':demoted,
            'promoted_pending_entries':promoted_pending},indent=2))
        return
    if target.exists():
        old=target.read_bytes()
        history=library/'validation/history'
        history.mkdir(exist_ok=True)
        (history/f'ready-functions-{hashlib.sha256(old).hexdigest()}.json').write_bytes(old)
    if old_compiled.exists():
        history=library/'validation/history'
        history.mkdir(exist_ok=True)
        old=old_compiled.read_bytes()
        (history/f'compiled-functions-{hashlib.sha256(old).hexdigest()}.json').write_bytes(old)
    target.write_text(json.dumps({'functions':[records[key] for key in sorted(records)],
        'integration_reference':'validation/integration.json','original_full_verification':False},indent=2)+'\n')
    (library/'validation/compiled-functions.json').write_text(json.dumps({'functions':compiled},indent=2)+'\n')
    if demoted or promoted_pending:
        history=library/'validation/history'
        history.mkdir(exist_ok=True)
        change=dict(demoted_entries=demoted,promoted_pending_entries=promoted_pending,
                    demotion_manifests=demotion_inputs,ready_sha256=sha(target),
                    pending_sha256=sha(library/'validation/compiled-functions.json'))
        encoded=(json.dumps(change,indent=2)+'\n').encode()
        (history/f'classification-{hashlib.sha256(encoded).hexdigest()}.json').write_bytes(encoded)
    print(json.dumps({'portable_ready_entries':len(records),'unique_mangled_methods':len({k[1] for k in records}),
                      'compiled_declaration_pending_entries':len(compiled),'stale_previous_entries':stale_previous,
                      'demoted_entries':demoted,'promoted_pending_entries':promoted_pending,
                      'full_original_verification':False},indent=2))


if __name__=='__main__':main()
