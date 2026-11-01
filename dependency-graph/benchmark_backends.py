"""Same graph, same reachability semantics; Neo4j must be isolated/local."""
import argparse
import hashlib
import json
import pathlib
import sqlite3
import statistics
import sys
import time

from graph_query import impact, impact_int

from neo4j import GraphDatabase


def digest(ids):
    return hashlib.sha256(json.dumps(sorted(ids)).encode()).hexdigest()


def neo_closure(session, key, kinds):
    visited = {key}
    frontier = [key]
    rounds = 0
    while frontier:
        rows = session.run('''UNWIND $frontier AS id
          MATCH (d:Artifact {id:id})<-[r]-(s:Artifact)
          WHERE type(r) IN $kinds RETURN DISTINCT s.id AS id''',
                           frontier=frontier, kinds=list(kinds))
        following = {row['id'] for row in rows} - visited
        visited.update(following)
        frontier = sorted(following)
        rounds += 1
    return visited, rounds


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--repeat', type=int, default=5)
    parser.add_argument('--port', type=int, default=17687)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--backend', choices=('neo4j', 'memgraph'), default='neo4j')
    args = parser.parse_args()
    output = pathlib.Path(args.out)
    if output.exists():
        raise ValueError('Output already exists')
    run = pathlib.Path(args.run)
    c = sqlite3.connect((run / 'graph.sqlite').resolve().as_uri() + '?mode=ro', uri=True)
    compact = sqlite3.connect((run / 'csv-import-int.sqlite').resolve().as_uri() + '?mode=ro', uri=True)
    driver = GraphDatabase.driver(f'bolt://{args.host}:{args.port}', auth=None)
    results = []
    with driver.session() as session:
        if args.backend == 'neo4j':
            version = [dict(r) for r in session.run('CALL dbms.components()')]
            session.run('CREATE CONSTRAINT artifact_id IF NOT EXISTS FOR (n:Artifact) REQUIRE n.id IS UNIQUE').consume()
            session.run('CALL db.awaitIndexes(120)').consume()
        else:
            version = 'Record exact image digest/version in container receipt'
        counts = session.run('MATCH (n) RETURN count(n) AS n').single()['n']
        edges = session.run('MATCH ()-[r]->() RETURN count(r) AS n').single()['n']
        assert counts == c.execute('SELECT count(*) FROM nodes').fetchone()[0]
        assert edges == c.execute('SELECT count(*) FROM edges').fetchone()[0]
        scenarios = json.loads((run / 'scenarios.json').read_text())
        for path in scenarios:
            if path not in ('uc-library/include/presonus/surface_panel/ControlHelpers.hpp',
                            'uc-library/src/Presonus/Panel/ControlRegistrarAccess.cpp'):
                continue
            key = 'file:' + path
            for domain, kinds in [('build', ('compiler_input', 'compiles', 'link_input')),
                                  ('proof', ('proof_binding', 'validation_binding'))]:
                times = {'sqlite_text': [], 'sqlite_int': [], 'bolt_bfs': []}
                expected = None
                for iteration in range(args.repeat):
                    # Alternate order to reduce systematic cache/order bias.
                    order = tuple(times) if iteration % 2 == 0 else tuple(reversed(times))
                    for backend in order:
                        start = time.perf_counter()
                        if backend == 'sqlite_text':
                            found = {r[0] for r in impact(c, key, kinds)}
                        elif backend == 'sqlite_int':
                            found = {r[0] for r in impact_int(compact, key, kinds)}
                        else:
                            found, rounds = neo_closure(session, key, kinds)
                        times[backend].append(time.perf_counter() - start)
                        if expected is None:
                            expected = found
                        assert found == expected, (path, domain, backend)
                results.append({'path': path, 'domain': domain, 'reachable': len(expected),
                                'identity_set_sha256': digest(expected), 'exact_parity': True,
                                'samples_seconds': times,
                                'median_seconds': {k: statistics.median(v) for k, v in times.items()}})
    payload = {'backend': args.backend, 'components': version, 'nodes': counts, 'edges': edges,
               'scenarios': results, 'physical_disk_cold': False,
               'neo4j_timing_includes_bolt_roundtrips': True,
               'sqlite_timing_includes_in_process_row_materialization': True,
               'permission_to_skip_checks': False}
    output.write_text(json.dumps(payload, indent=2) + '\n')
    print(json.dumps({'nodes': counts, 'edges': edges, 'scenarios': len(results),
                      'all_exact_parity': True}))
    driver.close()


if __name__ == '__main__':
    main()
