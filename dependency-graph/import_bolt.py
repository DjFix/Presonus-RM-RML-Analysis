"""Bounded transactional import for identical Neo4j/Memgraph online workloads."""
import argparse
import csv
import json
import pathlib
import time

from neo4j import GraphDatabase


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True)
    parser.add_argument('--host', required=True)
    parser.add_argument('--backend', choices=('neo4j', 'memgraph'), required=True)
    parser.add_argument('--batch', type=int, default=2000)
    args = parser.parse_args()
    run = pathlib.Path(args.run)
    result_path = run / (args.backend + '-online-import.json')
    if result_path.exists():
        raise ValueError('Do not overwrite import receipt')
    driver = GraphDatabase.driver(f'bolt://{args.host}:7687', auth=None)
    counts = {}
    start = time.perf_counter()
    with driver.session() as session:
        session.run('MATCH(g:ContextGeneration {id:"active"}) SET g.state="refreshing"').consume()
        assert session.run('MATCH (n) RETURN count(n) AS n').single()['n'] == 0
        if args.backend == 'neo4j':
            session.run('CREATE CONSTRAINT artifact_id FOR (n:Artifact) REQUIRE n.id IS UNIQUE').consume()
            session.run('CALL db.awaitIndexes(120)').consume()
        else:
            session.run('CREATE CONSTRAINT ON (n:Artifact) ASSERT n.id IS UNIQUE').consume()
            session.run('CREATE INDEX ON :Artifact(id)').consume()
        for name in ('nodes', 'edges'):
            phase = time.perf_counter()
            total = 0
            with (run / (name + '.csv')).open() as stream:
                reader = csv.DictReader(stream)
                batch = []

                def flush():
                    if name == 'nodes':
                        session.run('''UNWIND $rows AS row CREATE (:Artifact {
                          id:row.id, kind:row.kind, label:row.label, metadata:row.metadata})''',
                                    rows=batch).consume()
                    else:
                        for kind in sorted({r['kind'] for r in batch}):
                            if kind not in {'compiles', 'compiler_input', 'link_input',
                                            'proof_binding', 'validation_binding'}:
                                raise ValueError('Unexpected relationship type')
                            session.run('''UNWIND $rows AS row
                              MATCH (s:Artifact {id:row.src}), (d:Artifact {id:row.dst})
                              CREATE (s)-[:''' + kind + ''' {evidence:row.evidence}]->(d)''',
                                        rows=[r for r in batch if r['kind'] == kind]).consume()
                for row in reader:
                    batch.append(row)
                    total += 1
                    if len(batch) == args.batch:
                        flush()
                        batch = []
                if batch:
                    flush()
            counts[name] = {'rows': total, 'seconds': time.perf_counter() - phase}
            print(json.dumps({name: counts[name]}), flush=True)
    result_path.write_text(json.dumps({'backend': args.backend, 'phases': counts,
                                       'seconds': time.perf_counter() - start,
                                       'batch': args.batch}, indent=2) + '\n')
    driver.close()


if __name__ == '__main__':
    main()
