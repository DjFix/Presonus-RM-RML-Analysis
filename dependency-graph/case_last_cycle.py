"""Replay the last cycle's agent-reading scope, with exact cross-backend parity."""
import argparse
import hashlib
import json
import pathlib
import sqlite3
import statistics
import time

from neo4j import GraphDatabase

ROOT = pathlib.Path(__file__).resolve().parents[1]
INPUT = 'file:uc-library/include/presonus/surface_panel/ControlHelpers.hpp'
SQL = '''SELECT source,original_id,mangled FROM affected_original_symbols
         WHERE input_id=? ORDER BY source,original_id'''
CYPHER = '''MATCH (tu:TranslationUnit)-[:compiler_input|compiles]->(:Artifact {id:$input_id})
WITH DISTINCT tu
OPTIONAL MATCH (tu)-[:DEFINES]->(symbol:OriginalSymbol)
RETURN tu.source AS source, symbol.id AS original_id, symbol.mangled AS mangled
ORDER BY source,original_id'''


def ro(path):
    return sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True)
    parser.add_argument('--host', required=True)
    parser.add_argument('--backend', choices=('neo4j', 'memgraph'), required=True)
    args = parser.parse_args()
    run = pathlib.Path(args.run)
    output = run / ('case-last-cycle-' + args.backend + '.json')
    if output.exists():
        raise ValueError('Never overwrite a case receipt')
    c = ro(run / 'ownership.sqlite')
    c.execute('ATTACH DATABASE ? AS code', ((run / 'graph.sqlite').resolve().as_uri() + '?mode=ro',))
    c.executescript('''CREATE TEMP VIEW affected_translation_units AS
      SELECT DISTINCT e.dst AS input_id,o.id AS object_id,o.source
      FROM code.edges e JOIN objects o ON o.id=e.src
      WHERE e.kind IN ('compiler_input','compiles');
      CREATE TEMP VIEW affected_original_symbols AS
      SELECT tu.input_id,tu.source,s.id AS original_id,s.mangled
      FROM affected_translation_units tu
      LEFT JOIN definitions d ON d.object_id=tu.object_id
      LEFT JOIN original_symbols s ON s.mangled=d.mangled
      WHERE s.id IS NOT NULL;''')
    expected = set(c.execute(SQL, (INPUT,)))
    units = sorted({row[0] for row in expected})
    original_ids = {row[1] for row in expected}
    assert len(units) == 5 and len(original_ids) == 15, (units, len(original_ids))
    new = [row for row in expected if row[2] in (
        '_ZNK8Presonus5Panel16ControlRegistrar5countEv',
        '_ZNK8Presonus5Panel16ControlRegistrar2atEi')]
    assert len(new) == 4
    bound = {row[0] for row in c.execute("SELECT src FROM code.edges WHERE dst=? AND kind='proof_binding'", (INPUT,))}
    assert len(bound) == 131
    baseline_path = ROOT / 'evidence/recovery/2026-10-31/cycle-efficiency-audit/timings.json'
    baseline = json.loads(baseline_path.read_text())['cycle_output']
    assert baseline['incoming_records'] == 464
    objects = [dict(zip(('id', 'source', 'sha256'), row)) for row in c.execute('SELECT * FROM objects')]
    symbols = [dict(zip(('id', 'mangled'), row)) for row in c.execute('SELECT * FROM original_symbols')]
    definitions = [dict(zip(('object_id', 'symbol_id'), row)) for row in c.execute('''
      SELECT d.object_id,s.id FROM definitions d JOIN original_symbols s ON s.mangled=d.mangled''')]
    driver = GraphDatabase.driver('bolt://' + args.host + ':7687', auth=None)
    timings = {'sqlite_views': [], args.backend + '_cypher': []}
    with driver.session() as session:
        session.run('MATCH(g:ContextGeneration {id:"active"}) SET g.state="refreshing"').consume()
        start = time.perf_counter()
        session.run('''UNWIND $rows AS row MATCH (tu:Artifact {id:row.id})
          SET tu:TranslationUnit SET tu.source=row.source,tu.object_sha256=row.sha256''', rows=objects).consume()
        session.run('''UNWIND $rows AS row MATCH (s:Artifact {id:row.id})
          SET s:OriginalSymbol SET s.mangled=row.mangled''', rows=symbols).consume()
        session.run('''UNWIND $rows AS row
          MATCH (tu:Artifact {id:row.object_id}),(s:Artifact {id:row.symbol_id})
          MERGE (tu)-[:DEFINES]->(s)''', rows=definitions).consume()
        overlay_seconds = time.perf_counter() - start
        for iteration in range(5):
            order = tuple(timings) if iteration % 2 == 0 else tuple(reversed(timings))
            for backend in order:
                start = time.perf_counter()
                if backend == 'sqlite_views':
                    actual = set(c.execute(SQL, (INPUT,)))
                else:
                    actual = {(r['source'], r['original_id'], r['mangled'])
                              for r in session.run(CYPHER, input_id=INPUT)}
                timings[backend].append(time.perf_counter() - start)
                assert actual == expected, (backend, actual ^ expected)
    result = {'case': 'ControlHelpers header / registrar access cycle',
              'audit_baseline': baseline,
              'audit_baseline_sha256': hashlib.file_digest(baseline_path.open('rb'), 'sha256').hexdigest(),
              'original_manifest_bound': len(bound), 'selected_production_tus': units,
              'selected_original_records': len(original_ids),
              'selected_unique_mangled_methods': len({r[2] for r in expected}),
              'new_original_records_retained': len(new),
              'existing_original_records_selected': len(original_ids) - len(new),
              'manifest_only_unresolved_not_eagerly_read': sorted(bound - original_ids),
              'exact_original_ids': sorted(original_ids), 'exact_backend_parity': True,
              'samples_seconds': timings,
              'median_seconds': {k: statistics.median(v) for k, v in timings.items()},
              'semantic_overlay_seconds': overlay_seconds,
              'query_sql': SQL, 'query_cypher': CYPHER,
              'reading_scope_reduction_vs_incoming_records': 464 / len(original_ids),
              'reading_scope_reduction_vs_header_bindings': len(bound) / len(original_ids),
              'scope': 'TU-level initial code-reading context, not complete call/type/runtime dependency proof',
              'baseline_agent_reads_measured': False,
              'reconstruction_wall_time_speedup_measured': False,
              'production_validation_policy_changed': False}
    output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('selected_original_records', 'selected_unique_mangled_methods',
                                            'existing_original_records_selected', 'exact_backend_parity',
                                            'median_seconds')}))
    driver.close()


if __name__ == '__main__':
    main()
