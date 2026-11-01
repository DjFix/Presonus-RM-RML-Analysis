"""Idempotent, resumable full observation delta into isolated graph services."""
import argparse
import csv
import hashlib
import json
import pathlib
import re
import time

from neo4j import GraphDatabase


def sha(path):
    return hashlib.file_digest(path.open('rb'), 'sha256').hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run', required=True)
    p.add_argument('--host', required=True)
    p.add_argument('--backend', required=True, choices=('neo4j', 'memgraph'))
    p.add_argument('--qualified', action='store_true')
    a = p.parse_args()
    run = pathlib.Path(a.run)
    receipt = run / (a.backend + '-full-load.json')
    assert not receipt.exists(), 'Already completed; never overwrite receipt'
    state_path = run / (a.backend + '-full-load-state.json')
    prefix = 'qualified-' if a.qualified else 'delta-'
    inputs = {name: sha(run / (prefix + name + '.csv')) for name in ('nodes', 'edges')}
    state = json.loads(state_path.read_text()) if state_path.exists() else {
        'inputs': inputs, 'nodes': 0, 'edges': 0}
    assert state['inputs'] == inputs, 'Changed input; cannot resume'
    driver = GraphDatabase.driver('bolt://' + a.host + ':7687', auth=None)
    start = time.perf_counter()
    with driver.session() as session:
        session.run('MATCH(g:ContextGeneration {id:"active"}) SET g.state="refreshing"').consume()
        # The baseline case overlay lacked the provenance property; preserve it explicitly.
        session.run("MATCH ()-[r:DEFINES]->() WHERE r.evidence IS NULL SET r.evidence=''").consume()
        for phase in ('nodes', 'edges'):
            with (run / (prefix + phase + '.csv')).open() as stream:
                reader = csv.DictReader(stream)
                batch = []
                consumed = 0

                def flush():
                    if phase == 'nodes':
                        grouped = {}
                        for row in batch:
                            meta = json.loads(row['metadata'])
                            row['mangled'] = meta.get('mangled')
                            row['path'] = meta.get('path') or meta.get('source')
                            kind = {'file': 'File', 'symbol': 'OriginalSymbol'}.get(row['kind'], row['kind'])
                            assert re.fullmatch('[A-Za-z_][A-Za-z_0-9]*', kind)
                            grouped.setdefault(kind, []).append(row)
                        for kind, rows in grouped.items():
                            session.run('''UNWIND $rows AS row MERGE (n:Artifact {id:row.id})
                              SET n:''' + kind + ''' SET n.kind=row.kind,n.label=row.label,
                              n.metadata=row.metadata,n.mangled=row.mangled,n.path=row.path''', rows=rows).consume()
                    else:
                        for kind in sorted({r['kind'] for r in batch}):
                            assert re.fullmatch('[A-Za-z_][A-Za-z_0-9]*', kind)
                            session.run('''UNWIND $rows AS row
                              MATCH (s:Artifact {id:row.src}),(d:Artifact {id:row.dst})
                              MERGE (s)-[:''' + kind + ''' {evidence:row.evidence}]->(d)''',
                                        rows=[r for r in batch if r['kind'] == kind]).consume()
                    state[phase] = consumed
                    temporary = state_path.with_suffix('.new')
                    temporary.write_text(json.dumps(state, sort_keys=True) + '\n')
                    temporary.replace(state_path)

                for row in reader:
                    consumed += 1
                    if consumed <= state[phase]:
                        continue
                    batch.append(row)
                    if len(batch) == 1000:
                        flush()
                        batch = []
                if batch:
                    flush()
            print(json.dumps({'phase': phase, 'completed': state[phase]}), flush=True)
        node_counts = {r['kind']: r['n'] for r in session.run(
            'MATCH (n:Artifact) RETURN n.kind AS kind,count(n) AS n')}
        edge_counts = {r['kind']: r['n'] for r in session.run(
            'MATCH ()-[r]->() RETURN type(r) AS kind,count(r) AS n')}
        expected = json.loads((run / ('full-graph-qualified.json' if a.qualified else 'full-graph.json')).read_text())
        assert node_counts == expected['node_kinds'], (node_counts, expected['node_kinds'])
        assert edge_counts == expected['edge_kinds'], (edge_counts, expected['edge_kinds'])
    receipt.write_text(json.dumps({'backend': a.backend, 'input_sha256': inputs,
                                  'node_counts': node_counts, 'edge_counts': edge_counts,
                                  'seconds': time.perf_counter() - start, 'exact_counts_match': True}, indent=2) + '\n')
    print(json.dumps({'backend': a.backend, 'exact_counts_match': True,
                      'seconds': time.perf_counter() - start}))
    driver.close()


if __name__ == '__main__':
    main()
