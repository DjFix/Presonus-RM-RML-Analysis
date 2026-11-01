"""Live reversible regression: add/remove source calls and invalidate a shared header."""
import fcntl
import json
import pathlib
import sys
import time

from context_runtime import sha
from memgraph_endpoint import memgraph_uri
from refresh_facts import connect
from refresh_graph import BASE, ROOT, docker, ensure_fresh


def check_graph(out, phase, present):
    script = out / (phase + '.py')
    script.write_text('''from neo4j import GraphDatabase
import json
with GraphDatabase.driver(''' + repr(memgraph_uri(ROOT)) + ''',auth=None) as driver:
 with driver.session() as s:
  n=s.run("MATCH(n:Function) WHERE n.mangled CONTAINS 'dependency_graph_refresh_probe' RETURN count(n) AS n").single()['n']
  e=s.run("MATCH(n:Function)-[r:CALLS|GCC_CALLS]->(m:Function) WHERE n.mangled CONTAINS 'dependency_graph_refresh_probe' AND m.mangled CONTAINS 'dependency_graph_refresh_probe' RETURN count(r) AS n").single()['n']
  print(json.dumps({'functions':n,'call_edges':e}))
  assert ''' + ('n==2 and e==2' if present else 'n==0 and e==0') + '\n')
    docker([str(script)], out, phase)


def main():
    out = ROOT / 'temp/test-work/refresh-graph' / str(time.time_ns()); out.mkdir(parents=True)
    cpp = ROOT / 'uc-library/tests/panel_registrar_access_tests.cpp'
    header = ROOT / 'uc-library/include/presonus/panel/registrar_group_registry.hpp'
    originals = {cpp: cpp.read_bytes(), header: header.read_bytes()}
    for p, content in originals.items(): (out / p.name).write_bytes(content)
    c = connect(BASE / 'state/refresh-index.sqlite')
    dependents = [owner for owner, payload in c.execute('SELECT * FROM units')
                  if str(header) in json.loads(payload)['inputs']]
    c.close()
    receipts = []
    try:
        start = time.perf_counter(); result = ensure_fresh()
        receipts.append({'phase': 'unchanged', 'result': result, 'seconds': time.perf_counter()-start})
        assert not result['refreshed']
        cpp.write_bytes(originals[cpp] + b'\nnamespace dependency_graph_refresh_probe {\nint leaf() { return 7; }\nint caller() { return leaf(); }\n}\n')
        result = ensure_fresh(); receipts.append({'phase': 'cpp-add', 'result': result})
        assert result['recompiled_units'] == 1 and result['reused_units'] == 624
        check_graph(out, 'probe-present', True)
        cpp.write_bytes(originals[cpp])
        header.write_bytes(originals[header] + b'\n// Reversible dependency graph invalidation probe.\n')
        result = ensure_fresh(); receipts.append({'phase': 'cpp-remove-header-change', 'result': result})
        expected = set(dependents) | {'app:0519'}
        assert result['recompiled_units'] == len(expected), (result, expected)
        check_graph(out, 'probe-removed', False)
        header.write_bytes(originals[header])
        result = ensure_fresh(); receipts.append({'phase': 'header-restore', 'result': result})
        assert result['recompiled_units'] == len(dependents)
        start = time.perf_counter(); result = ensure_fresh()
        receipts.append({'phase': 'unchanged-after-restore', 'result': result, 'seconds': time.perf_counter()-start})
        assert not result['refreshed']
    finally:
        for p, content in originals.items():
            if p.read_bytes() != content: p.write_bytes(content)
        (out / 'receipts.json').write_text(json.dumps(receipts, indent=2) + '\n')
    result = {'passed': True, 'header_dependent_units': dependents,
              'source_hashes_restored': {str(p.relative_to(ROOT)): sha(p) for p in originals}, 'receipts': receipts}
    (out / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
    print(str(out / 'results.json'), flush=True)


if __name__ == '__main__':
    with (BASE / 'state/context.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX); main()
