"""Three alternating samples on the complete corpus; not a load benchmark."""
import argparse
import json
import pathlib
import sqlite3
import statistics
import time

from neo4j import GraphDatabase
from full_queries import QUERIES, sql_closure, graph_closure

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--run', required=True)
a = p.parse_args()
run = pathlib.Path(a.run)
output = run / 'full-query-timings.json'
assert not output.exists()
c = sqlite3.connect((run / 'graph.sqlite').resolve().as_uri() + '?mode=ro', uri=True)
drivers = {b: GraphDatabase.driver('bolt://dependency-graph-' + b + ':7687', auth=None)
           for b in ('neo4j','memgraph')}
sessions = {b: d.session() for b,d in drivers.items()}
result = []
for name in ('_ZNK8Presonus5Panel16ControlRegistrar5countEv', '_ZNK8Presonus5Panel16ControlRegistrar2atEi'):
    seed = 'function:' + name
    for question in ('callees','callers','tests','call_closure','reading_context'):
        samples = {b: [] for b in ('sqlite','neo4j','memgraph')}
        expected = None
        for iteration in range(3):
            for backend in (tuple(samples) if iteration % 2 == 0 else tuple(reversed(samples))):
                start = time.perf_counter()
                if question in ('call_closure','reading_context'):
                    actual = (sql_closure(c,seed,context=question=='reading_context') if backend=='sqlite'
                              else graph_closure(sessions[backend],seed,context=question=='reading_context'))
                elif backend == 'sqlite':
                    actual = {r[0] for r in c.execute(QUERIES[question].sql, {'seed':seed})}
                else:
                    actual = {r['id'] for r in sessions[backend].run(QUERIES[question].cypher,seed=seed)}
                samples[backend].append(time.perf_counter()-start)
                if expected is None:
                    expected = actual
                assert expected == actual
        result.append({'seed':seed,'query':question,'count':len(expected),'samples_seconds':samples,
                       'median_ms':{b:statistics.median(v)*1000 for b,v in samples.items()},'parity':True})
for s in sessions.values():s.close()
for d in drivers.values():d.close()
output.write_text(json.dumps({'results':result,'disk_cold':False,
                             'bolt_network_included':True,'repeats':3},indent=2)+'\n')
print(json.dumps({'queries':len(result),'all_parity':True}))
