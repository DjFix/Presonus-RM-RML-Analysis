"""Actual last-case coverage and maintainable query parity on the full graph."""
import argparse
import hashlib
import json
import pathlib
import sqlite3
import statistics
import time

from neo4j import GraphDatabase
from full_queries import QUERIES, graph_closure, sql_closure

ROOT = pathlib.Path(__file__).resolve().parents[1]
TARGET_NAMES = ('_ZNK8Presonus5Panel16ControlRegistrar5countEv',
                '_ZNK8Presonus5Panel16ControlRegistrar2atEi')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run', required=True)
    p.add_argument('--backend', required=True, choices=('neo4j', 'memgraph'))
    p.add_argument('--host', required=True)
    a = p.parse_args()
    run = pathlib.Path(a.run)
    output = run / (a.backend + '-full-check.json')
    assert not output.exists()
    c = sqlite3.connect((run / 'graph.sqlite').resolve().as_uri() + '?mode=ro', uri=True)
    driver = GraphDatabase.driver('bolt://' + a.host + ':7687', auth=None)
    samples = []
    union_calls = set()
    union_context = set()
    union_callers = set()
    union_references = set()
    tests = set()
    files = set()
    fixture_ids = set()
    unresolved = set()
    with driver.session() as session:
        for name in TARGET_NAMES:
            seed = 'function:' + name
            assert c.execute('SELECT 1 FROM nodes WHERE id=?', (seed,)).fetchone()
            for query_name in ('callees', 'callers', 'references', 'unresolved', 'tests'):
                query = QUERIES[query_name]
                sql_times = []
                graph_times = []
                for repeat in range(3):
                    start = time.perf_counter()
                    expected = {r[0] for r in c.execute(query.sql, {'seed': seed})}
                    sql_times.append(time.perf_counter() - start)
                    start = time.perf_counter()
                    actual = {r['id'] for r in session.run(query.cypher, seed=seed)}
                    graph_times.append(time.perf_counter() - start)
                    assert expected == actual, (query_name, expected ^ actual)
                samples.append({'query': query_name, 'seed': seed, 'count': len(expected),
                                'sqlite_median_seconds': statistics.median(sql_times),
                                'graph_median_seconds': statistics.median(graph_times), 'exact_parity': True})
                if query_name == 'callers':
                    union_callers.update(expected)
                if query_name == 'references':
                    union_references.update(expected)
                if query_name == 'tests':
                    tests.update(expected)
            for context in (False, True):
                start = time.perf_counter()
                expected = sql_closure(c, seed, context=context)
                sql_time = time.perf_counter() - start
                start = time.perf_counter()
                actual = graph_closure(session, seed, context=context)
                graph_time = time.perf_counter() - start
                assert expected == actual
                samples.append({'query': 'reading_context' if context else 'call_closure',
                                'seed': seed, 'count': len(expected), 'sqlite_seconds': sql_time,
                                'graph_seconds': graph_time, 'exact_parity': True})
                (union_context if context else union_calls).update(expected)
        for key in union_context | union_callers:
            expected = {r[0] for r in c.execute(QUERIES['source_files'].sql, {'seed': key})}
            actual = {r['id'] for r in session.run(QUERIES['source_files'].cypher, seed=key)}
            assert expected == actual
            files.update(expected)
            unknown = {r[0] for r in c.execute(QUERIES['unresolved'].sql, {'seed': key})}
            actual = {r['id'] for r in session.run(QUERIES['unresolved'].cypher, seed=key)}
            assert unknown == actual
            unresolved.update(unknown)
        for key in tests:
            expected = {r[0] for r in c.execute(QUERIES['fixtures'].sql, {'seed': key})}
            actual = {r['id'] for r in session.run(QUERIES['fixtures'].cypher, seed=key)}
            assert expected == actual
            fixture_ids.update(expected)
    packet = json.loads((ROOT / 'dependency-graph/runs/baseline-01/control-helpers-agent-reviewed.json').read_text())
    old_files = set(packet['read_files'])
    required_files = {r[0] for key in files for r in c.execute('SELECT label FROM nodes WHERE id=?', (key,))}
    native = json.loads((run / 'native-references.json').read_text())
    assert native['objects_checked'] == 574 and not native['missing']
    assert len(native['target_referencing_units']) == 1
    assert tests == {'test:panel_registrar_access'}
    assert len(union_calls) >= 5
    for name in TARGET_NAMES:
        seed = 'function:' + name
        ast_calls = {r[0] for r in c.execute("SELECT dst FROM edges WHERE src=? AND kind='CALLS'", (seed,))}
        gcc_calls = {r[0] for r in c.execute("SELECT dst FROM edges WHERE src=? AND kind='GCC_CALLS'", (seed,))}
        assert ast_calls == gcc_calls, (name, ast_calls ^ gcc_calls)
    identities = sorted(union_calls | union_context | union_callers | tests | fixture_ids | files)
    result = {'backend': a.backend, 'query_samples': samples,
              'call_closure_functions': sorted(union_calls),
              'call_closure_details': {key: dict(zip(('kind','label','metadata'), c.execute(
                  'SELECT kind,label,metadata FROM nodes WHERE id=?', (key,)).fetchone())) for key in sorted(union_calls)},
              'direct_callers': sorted(union_callers), 'context_nodes': sorted(union_context),
              'all_target_references': sorted(union_references),
              'target_call_edges_match_gcc_and_clang': True,
              'required_source_files': sorted(required_files),
              'files_outside_old_read_first': sorted(required_files - old_files),
              'selected_tests': sorted(tests), 'fixture_ids': sorted(fixture_ids),
              'unresolved_in_target_context': sorted(unresolved),
              'all_results_parity': True,
              'identity_set_sha256': hashlib.sha256(json.dumps(identities).encode()).hexdigest(),
              'old_15_records_are_complete_reading_context': False,
              'scope': 'Selected two methods, selected source build, source/compiler graph; runtime uncertainty remains explicit'}
    output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'backend': a.backend, 'call_functions': len(union_calls),
                      'source_files': len(required_files), 'tests': sorted(tests),
                      'fixtures': sorted(fixture_ids), 'unresolved': len(unresolved), 'parity': True}))
    driver.close()


if __name__ == '__main__':
    main()
