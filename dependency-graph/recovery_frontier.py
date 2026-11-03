"""Recovery-progress priority over immutable complexity observations.

No source/header/lifecycle exclusion. Existing implementation is a planning fact,
never automatic satisfaction of a caller's behavior, declaration or ABI scope.
The SQLite registry remains canonical; this module performs no assignments.
"""
import argparse
import hashlib
import json
import pathlib
import sqlite3
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
POLICY_VERSION = 'recovery-frontier-v1'


def priority(unknown_inputs, recovered_inputs, source_inputs, complexity, work_id):
    return [unknown_inputs, -recovered_inputs, -source_inputs, *complexity, work_id]


def order(c, recovered_keys, source_keys=(), existing_keys=()):
    recovered_keys, source_keys, existing_keys = set(recovered_keys), set(source_keys), set(existing_keys)
    items = {row['id']: dict(row) for row in c.execute('SELECT i.*,s.canonical,s.claimed,e.rank,e.queue FROM items i JOIN states s USING(id) JOIN evaluations e USING(id)')}
    by_native = {}
    for row in items.values():
        row['identities'] = json.loads(row['identities'])
        for identity in row['identities']:
            by_native[identity['native_id']] = (identity['elf_sha256'], identity['original_mangled'])
    requirements = {}
    for row in c.execute("SELECT * FROM requirements WHERE scope IN ('callable_behavior','data_binding_behavior')"):
        requirements.setdefault(row['consumer'], []).append(dict(row))
    result = []
    for ident, item in items.items():
        if item['canonical'] != 'remaining' or item['original_kind'] != 'reconstruct':
            continue
        inputs = {}
        for requirement in requirements.get(ident, []):
            target = requirement['target']
            if target == ident:
                continue
            observed = json.loads(requirement['evidence'])
            native = observed.get('native_dst')
            key = by_native.get(native)
            if key is None:
                # Unknown/unmapped endpoints are retained, never treated as free.
                state = 'unreconstructed'
            elif key in recovered_keys:
                state = 'recovered_implementation'
            elif key in source_keys:
                state = 'source_provided'
            elif key in existing_keys:
                state = 'existing_result_needs_review'
            else:
                state = 'unreconstructed'
            prior = inputs.get(target)
            if prior:
                severity = {'recovered_implementation': 0, 'source_provided': 1,
                            'existing_result_needs_review': 2, 'unreconstructed': 3}
                state = max((state, prior['state']), key=severity.__getitem__)
            inputs[target] = {'target': target, 'state': state,
                              'behavior_requirement_satisfied': bool(requirement['satisfied']) and (prior is None or prior['behavior_requirement_satisfied']),
                              'required_scopes': sorted(set((prior or {}).get('required_scopes', []) + [requirement['scope']])),
                              'evidence': (prior or {}).get('evidence', []) + [observed]}
        unknown = sum(v['state'] == 'unreconstructed' for v in inputs.values())
        recovered = sum(v['state'] == 'recovered_implementation' for v in inputs.values())
        source = sum(v['state'] == 'source_provided' for v in inputs.values())
        existing = sum(v['state'] == 'existing_result_needs_review' for v in inputs.values())
        # Keep original uncertainty/complexity bins intact; recovery work comes first.
        complexity = json.loads(item['rank'])[1:-1]
        own_keys = {(o['elf_sha256'], o['original_mangled']) for o in item['identities']}
        result.append({'work_item_id': ident, 'kind': item['kind'], 'namespace': item['namespace'],
                       'identities': item['identities'], 'claimed': bool(item['claimed']),
                       'context_queue': item['queue'], 'required_inputs': list(inputs.values()),
                       'unreconstructed_inputs': unknown, 'recovered_inputs': recovered,
                       'source_provided_inputs': source, 'existing_inputs_to_review': existing,
                       'own_existing_result': bool(own_keys & existing_keys),
                       'priority': priority(unknown, recovered, source, complexity, ident),
                       'legacy_rank': json.loads(item['rank']), 'dispatch_authorized': False})
    return sorted(result, key=lambda row: (row['kind'], row['priority']))


def run(db, output):
    producer_digest = hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()
    sys.path.insert(0, str(ROOT/'uc-library/tools/registry'))
    from adapter import snapshot
    import ranking
    c = sqlite3.connect(pathlib.Path(db).resolve().as_uri()+'?mode=ro', uri=True)
    c.row_factory = sqlite3.Row
    ranking.check_inputs(c)
    cache = {}
    def digest(path):
        if path not in cache:
            cache[path] = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        return cache[path]
    recovered, existing = set(), set()
    with snapshot(ROOT/'uc-library') as registry:
        provenance = registry.provenance()
        for status in ('ready', 'pending'):
            for record in registry.load_registry(status)['functions']:
                key = (record['original_elf_sha256'], record['mangled'])
                if not record.get('cpp_compiled'):
                    continue
                existing.add(key)
                if (record.get('validation') and digest(ROOT/'uc-library'/record['validation']) == record.get('validation_sha256')
                        and all(digest(ROOT/'uc-library'/path) == value for path, value in record.get('sources', {}).items())
                        and all(digest(ROOT/path) == value for path, value in record.get('repository_sources', {}).items())):
                    recovered.add(key)
    pointer = json.loads((ROOT/'dependency-graph/NATIVE_ACTIVE.json').read_text())
    n = sqlite3.connect(ROOT/pointer['database']); n.row_factory = sqlite3.Row
    # Exact compiled names indicate review/reuse work, not recovered native identities.
    names = set()
    for archive in (ROOT/'temp/core-upstream/root-integration-01').glob('libpresonus_*.a'):
        import subprocess
        text = subprocess.check_output(['/usr/bin/nm', '--defined-only', str(archive)], text=True)
        names.update(line.split()[-1] for line in text.splitlines() if len(line.split()) >= 2)
    for row in c.execute('SELECT identities FROM items'):
        for ident in json.loads(row[0]):
            if ident['original_mangled'] in names:
                existing.add((ident['elf_sha256'], ident['original_mangled']))
    source = set()
    for row in n.execute("SELECT n.metadata,r.evidence_json FROM nodes n JOIN symbol_resolution r ON r.symbol_id=n.id WHERE r.strategy='external_source' AND r.binding_status='verified'"):
        meta = json.loads(row['metadata']); binding = json.loads(row['evidence_json'])
        available = False
        for entry in binding.get('upstream', []):
            path = entry.get('repository_path')
            if not path or digest(ROOT/path) != entry.get('sha256', entry.get('source_sha256')):
                continue
            for definition in [entry, *entry.get('generic_definitions', [])]:
                if not definition.get('definition') or not definition.get('definition_extent_sha256'):
                    continue
                source_path = path if definition is entry else 'third_party/ccl-framework/'+definition['path']
                raw = (ROOT/source_path).read_bytes()
                extent = raw[definition['definition_extent_start']:definition['definition_extent_end']]
                if hashlib.sha256(extent).hexdigest() == definition['definition_extent_sha256']:
                    available = True
        if available:
            source.add((meta['elf_sha256'], meta['mangled']))
    rows = order(c, recovered, source, existing)
    output = pathlib.Path(output); output.mkdir(parents=True, exist_ok=False)
    if digest(pathlib.Path(__file__)) != producer_digest:
        raise ValueError('Frontier producer changed during computation')
    document = {'policy': POLICY_VERSION, 'producer': {'path': str(pathlib.Path(__file__).relative_to(ROOT)), 'sha256': digest(pathlib.Path(__file__))}, 'base_ranking': {'path': str(pathlib.Path(db).resolve().relative_to(ROOT)), 'sha256': digest(pathlib.Path(db).resolve())}, 'registry': provenance,
                'cost': 'Unique unreconstructed required inputs ascending; recovered inputs descending; source-provided inputs descending; unchanged native uncertainty/complexity as tie breakers.',
                'scope': 'Implementation recovery progress is not caller behavior/ABI satisfaction. Zero recovered inputs, missing C++ declarations and lifecycle methods remain in the queue. Claimed work retains its owner; research/context/planning gates remain before any dispatch.',
                'items': rows}
    (output/'FRONTIER.json').write_text(json.dumps(document, indent=2)+'\n')
    lines = ['# Reconstruction frontier', '', document['cost'], '', document['scope'], '', '| Work | Unreconstructed inputs | Recovered inputs | Source inputs | Claimed | Symbol |', '|---|---:|---:|---:|---|---|']
    for row in rows:
        lines.append('|'+row['work_item_id']+'|'+str(row['unreconstructed_inputs'])+'|'+str(row['recovered_inputs'])+'|'+str(row['source_provided_inputs'])+'|'+str(row['claimed'])+'|'+row['identities'][0]['original_mangled']+'|')
    (output/'FRONTIER.md').write_text('\n'.join(lines)+'\n')
    return {'queued': len(rows), 'zero_recovered_inputs_retained': sum(r['recovered_inputs']==0 for r in rows),
            'source_contract_required_before_dispatch': True, 'complexity_policy_changed': False}


def scope_cost(selected, available_rows):
    """Count shared missing work once, including prerequisite closure and cycles."""
    known = {row['work_item_id']: row for row in available_rows}
    work = {row['work_item_id'] for row in selected}
    pending = list(work)
    external = set()
    visited = set()
    while pending:
        ident = pending.pop()
        if ident in visited:
            continue
        visited.add(ident)
        row = known.get(ident)
        if row is None:
            external.add(ident)
            continue
        for dependency in row['required_inputs']:
            if dependency['state'] == 'unreconstructed' and dependency['target'] not in work:
                work.add(dependency['target'])
                pending.append(dependency['target'])
    return {'unique_work_with_prerequisites': len(work), 'work_item_ids': sorted(work),
            'external_inputs_needing_separate_binding_or_research': sorted(external)}


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--db',required=True);p.add_argument('--out',required=True);a=p.parse_args()
    print(json.dumps(run(a.db,a.out)))
