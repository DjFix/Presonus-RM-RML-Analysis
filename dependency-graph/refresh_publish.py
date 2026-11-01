"""Transactional Memgraph delta publication with a durable retry journal."""
import json
import pathlib
import re
import shlex
import sqlite3
import sys
import time

from neo4j import GraphDatabase
from memgraph_endpoint import memgraph_uri
from code_identity import VERSION
from batch_publication import publish
from context_runtime import ContextError, inventory, sha
from context_selector import register
from refresh_facts import connect, external_dependencies, facts, merged_node, replace

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE = ROOT / 'dependency-graph'
BUILD = ROOT / 'temp/core-upstream/root-integration-01'
BUILD_KINDS = ('compiler_input', 'compiles', 'link_input', 'HAS_TEST_TU', 'RUNS', 'USES_FIXTURE')


def build_facts(c, out):
    nodes = {}; edges = set(); inputs = {}
    def node(key, kind, label, meta=None):
        nodes[key] = {'kind': kind, 'label': label, 'metadata': meta or {}}
        return key
    def file(path):
        path = pathlib.Path(path).resolve()
        label = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
        return node('file:' + label, 'file', label)
    source_units = {}; objects = {}; directories = set()
    for owner, payload in c.execute('SELECT * FROM units ORDER BY owner'):
        data = json.loads(payload); row = data['command']; directories.add(pathlib.Path(row['directory']))
        argv = row.get('arguments') or shlex.split(row['command'])
        obj = pathlib.Path(row['directory']) / argv[argv.index('-o') + 1]
        oid = file(obj); objects[oid] = owner
        edges.add((oid, file(row['file']), 'compiles', 'current compile_commands.json'))
        for path, digest in data['inputs'].items():
            if path in inputs and inputs[path] != digest: raise ContextError('Mixed source observations: ' + path)
            inputs[path] = digest
            edges.add((oid, file(path), 'compiler_input', 'current captured compiler/AST input'))
        external = data.get('external_inputs')
        if external is None: external = external_dependencies(ROOT, row)
        for path in external:
            edges.add((oid, file(path), 'compiler_input', 'external include path; compiler environment, not recovered source'))
        tu = [r[0] for r in c.execute('SELECT id FROM node_facts WHERE owner=? AND kind=?', (owner, 'TranslationUnit'))]
        if len(tu) != 1: raise ContextError('Exactly one TU required: ' + owner)
        source_units[oid] = tu[0]
        inputs[data['ast']] = data['ast_sha256']; inputs[data['gcc']] = data['gcc_sha256']
    linked = {}
    for directory in directories:
        for recipe in sorted(directory.glob('CMakeFiles/*/link.txt')):
            inputs[str(recipe)] = sha(recipe)
            argv = shlex.split(recipe.read_text())
            if not argv: continue
            if '-o' in argv: output = argv[argv.index('-o') + 1]
            elif pathlib.Path(argv[0]).name in ('ar', 'gcc-ar', 'llvm-ar'):
                output = next((s for s in argv[1:] if s.endswith('.a')), None)
            else: continue
            if not output: continue
            target = file(directory / output); linked[target] = []
            for token in argv:
                if token.endswith(('.o', '.a')) and token != output:
                    source = file(directory / token)
                    edges.add((target, source, 'link_input', str(recipe)))
                    if source in source_units: linked[target].append(source_units[source])
    tests = json.loads((out / 'ctest-inventory.log').read_text())['tests']
    for test in tests:
        tid = node('test:' + test['name'], 'Test', test['name'], test)
        argv = test.get('command', [])
        if not argv: raise ContextError('Configured test has no resolved CTest command: ' + test['name'])
        executable = file(argv[0]); edges.add((tid, executable, 'RUNS', 'current CTest inventory'))
        for tu in linked.get(executable, []): edges.add((tid, tu, 'HAS_TEST_TU', 'current CMake link operand + CTest command'))
        for arg in argv[1:]:
            p = pathlib.Path(arg)
            if p.is_absolute() and p.is_relative_to(ROOT) and p.is_file():
                digest = sha(p); inputs[str(p)] = digest
                fid = node('file:' + str(p.relative_to(ROOT)), 'Fixture', str(p.relative_to(ROOT)), {'sha256': digest})
                edges.add((tid, fid, 'USES_FIXTURE', 'explicit existing file argument in CTest command'))
    return nodes, edges, inputs


def stage(c, out):
    delta = sqlite3.connect(out / 'delta.sqlite')
    delta.executescript('''CREATE TABLE old_edges(src,dst,kind,evidence,PRIMARY KEY(src,dst,kind,evidence));
      CREATE TABLE new_edges(src,dst,kind,evidence,PRIMARY KEY(src,dst,kind,evidence));
      CREATE TABLE prior_edges(src,dst,kind,evidence,PRIMARY KEY(src,dst,kind,evidence));
      CREATE TABLE settings(key PRIMARY KEY,value);
      CREATE TABLE changed_nodes(id PRIMARY KEY); CREATE TABLE nodes(id,kind,label,metadata);
      CREATE TABLE orphan_nodes(id);''')
    plan = json.loads((out / 'plan.json').read_text())
    selected = json.loads((out / 'units.json').read_text())
    affected = sorted(set(plan['affected_units']) | set(plan['removed_units']) | {'@build'})
    c.execute('BEGIN IMMEDIATE')
    try:
        legacy = not c.execute('SELECT 1 FROM node_facts WHERE owner="@build" LIMIT 1').fetchone()
        delta.execute('INSERT INTO settings VALUES(?,?)', ('replace_legacy_build', int(legacy)))
        old_nodes = {}
        for owner in affected:
            delta.executemany('INSERT OR IGNORE INTO old_edges VALUES(?,?,?,?)',
                              c.execute('SELECT src,dst,kind,evidence FROM edge_facts WHERE owner=?', (owner,)))
            delta.executemany('INSERT OR IGNORE INTO changed_nodes VALUES(?)',
                              c.execute('SELECT id FROM node_facts WHERE owner=?', (owner,)))
        for key, in delta.execute('SELECT id FROM changed_nodes').fetchall():
            old_nodes[key] = merged_node(c, key)
        delta.execute('INSERT INTO prior_edges SELECT * FROM old_edges')
        for owner in affected:
            c.execute('DELETE FROM edge_facts WHERE owner=?', (owner,))
            c.execute('DELETE FROM node_facts WHERE owner=?', (owner,))
            c.execute('DELETE FROM units WHERE owner=?', (owner,))
            c.execute('DELETE FROM current_observations WHERE owner=?', (owner,))
        for owner, row in selected:
            dest = out / 'observations' / owner.replace(':', '-')
            ast, gcc = dest / 'ast.json', dest / '0000.json'
            nodes, edges = facts(ROOT, owner, row, ast, gcc)
            captured = json.loads(ast.read_text()); inputs = captured['input_sha256']
            # GCC's preprocessor dependency list also covers conditional includes
            # not exposed as AST entities. The AST already enumerates all includes.
            replace(c, owner, row, nodes, edges, inputs, ast, gcc, captured['external_inputs'])
        nodes, edges, inputs = build_facts(c, out)
        c.executemany('INSERT INTO node_facts VALUES(?,?,?,?,?)',
                      (('@build', key, v['kind'], v['label'], json.dumps(v['metadata'], sort_keys=True)) for key, v in nodes.items()))
        c.executemany('INSERT OR IGNORE INTO edge_facts VALUES(?,?,?,?,?)', (('@build', *e) for e in edges))
        for owner in affected:
            delta.executemany('INSERT OR IGNORE INTO new_edges VALUES(?,?,?,?)',
                              c.execute('SELECT src,dst,kind,evidence FROM edge_facts WHERE owner=?', (owner,)))
            delta.executemany('INSERT OR IGNORE INTO changed_nodes VALUES(?)',
                              c.execute('SELECT id FROM node_facts WHERE owner=?', (owner,)))
        # An old shared observation disappears only when its last contributor does.
        old = list(delta.execute('SELECT * FROM old_edges'))
        for edge in old:
            if c.execute('SELECT 1 FROM edge_facts WHERE src=? AND dst=? AND kind=? AND evidence=? LIMIT 1', edge).fetchone():
                delta.execute('DELETE FROM old_edges WHERE src=? AND dst=? AND kind=? AND evidence=?', edge)
        # Reuse existing build/source observations instead of re-MERGEing every
        # include edge whenever one TU changes. Only genuinely new tuples travel.
        delta.execute('''DELETE FROM new_edges WHERE EXISTS(SELECT 1 FROM prior_edges p
          WHERE p.src=new_edges.src AND p.dst=new_edges.dst AND p.kind=new_edges.kind
          AND p.evidence=new_edges.evidence)''')
        for key, in delta.execute('SELECT id FROM changed_nodes').fetchall():
            value = merged_node(c, key)
            if value:
                if value != old_nodes.get(key):
                    delta.execute('INSERT INTO nodes VALUES(:id,:kind,:label,:metadata)', value)
            else: delta.execute('INSERT INTO orphan_nodes VALUES(?)', (key,))
        # Configs/commands and CMake generated recipes are captured independently.
        for path in [ROOT / 'uc-library/CMakeLists.txt', *ROOT.glob('uc-library/cmake/**/*.cmake'),
                     BUILD / 'compile_commands.json', BUILD / 'upstream-core/build/compile_commands.json',
                     BUILD / 'CMakeCache.txt', BUILD / 'upstream-core/build/CMakeCache.txt']:
            inputs[str(path)] = sha(path)
        for build in (BUILD, BUILD / 'upstream-core/build'):
            makefile = build / 'CMakeFiles/Makefile.cmake'
            if makefile.exists():
                inputs[str(makefile)] = sha(makefile)
                block = re.search(r'set\(CMAKE_MAKEFILE_DEPENDS\s+(.*?)\)', makefile.read_text(), re.S)
                for token in shlex.split(block[1] if block else ''):
                    path = (build / token).resolve()
                    if path.is_relative_to(ROOT) and path.is_file(): inputs[str(path)] = sha(path)
        for relative in inventory(ROOT):
            path = ROOT / relative
            if path.suffix == '.cmake' or path.name == 'CMakeLists.txt': inputs[str(path)] = sha(path)
        for path, digest in inputs.items():
            if not pathlib.Path(path).is_file() or sha(path) != digest:
                raise ContextError('Inputs changed before publication: ' + path)
        report = {'input_sha256': inputs, 'source_graph_refresh': True,
                  'source_inventory': inventory(ROOT),
                  'producer_sha256': plan.get('producer_sha256', {}),
                  'observation_provenance': plan.get('observation_provenance', {}),
                  'runtime_or_original_firmware_callgraph_complete': False}
        (out / 'refresh-report.json').write_text(json.dumps(report, indent=2) + '\n')
        delta.commit()
        c.execute('INSERT OR REPLACE INTO meta VALUES(?,?)', ('pending', str(out)))
        c.commit()
    except BaseException:
        c.rollback(); raise
    finally: delta.close()


def batches(cursor, size=500):
    while True:
        batch = cursor.fetchmany(size)
        if not batch: return
        yield [dict(r) for r in batch]


def apply(tx, d):
    # One-time conversion removes legacy unowned build edges. Later generations
    # retract exact old tuples; unchanged build links never cross Bolt again.
    settings = d.execute("SELECT 1 FROM sqlite_master WHERE name='settings'").fetchone()
    legacy = not settings or d.execute('SELECT value FROM settings WHERE key="replace_legacy_build"').fetchone()[0]
    if legacy:
        for kind in BUILD_KINDS:
            print('publication: retract legacy ' + kind, flush=True)
            tx.run('MATCH ()-[r:' + kind + ']->() DELETE r').consume()
    print('publication: nodes', flush=True)
    for batch in batches(d.execute('SELECT * FROM nodes')):
        for row in batch:
            metadata = json.loads(row['metadata']); row['mangled'] = metadata.get('mangled')
            row['path'] = metadata.get('path') or metadata.get('source')
        for kind in sorted({r['kind'] for r in batch}):
            label = {'file': 'File', 'symbol': 'OriginalSymbol'}.get(kind, kind)
            if not re.fullmatch('[A-Za-z_][A-Za-z_0-9]*', label): raise ValueError(label)
            tx.run('UNWIND $rows AS row MERGE(n:Artifact {id:row.id}) SET n:' + label +
                   ' SET n.kind=row.kind,n.label=row.label,n.metadata=row.metadata,n.mangled=row.mangled,n.path=row.path',
                   rows=[r for r in batch if r['kind'] == kind]).consume()
    for table, operation in [('old_edges', 'delete'), ('new_edges', 'merge')]:
        total = d.execute('SELECT count(*) FROM ' + table).fetchone()[0]
        done = 0
        print(f'publication: {table} 0/{total}', flush=True)
        for batch in batches(d.execute('SELECT * FROM ' + table)):
            for kind in sorted({r['kind'] for r in batch}):
                if not re.fullmatch('[A-Za-z_][A-Za-z_0-9]*', kind): raise ValueError(kind)
                if operation == 'delete':
                    query = ('UNWIND $rows AS row MATCH(s:Artifact {id:row.src})-[r:' + kind +
                             ' {evidence:row.evidence}]->(d:Artifact {id:row.dst}) DELETE r')
                else:
                    query = ('UNWIND $rows AS row MATCH(s:Artifact {id:row.src}),(d:Artifact {id:row.dst}) '
                             'MERGE(s)-[:' + kind + ' {evidence:row.evidence}]->(d)')
                selected = [r for r in batch if r['kind'] == kind]
                if operation == 'merge':
                    count = tx.run(query + ' RETURN count(*) AS n', rows=selected).single()['n']
                    if count != len(selected): raise ContextError('Missing edge endpoints: ' + kind)
                else:
                    tx.run(query, rows=selected).consume()
            done += len(batch)
            if done % 10000 == 0 or done == total:
                print(f'publication: {table} {done}/{total}', flush=True)
    for batch in batches(d.execute('SELECT * FROM orphan_nodes')):
        # Legacy proof/catalog bindings remain historical. Remove a code entity's
        # name match when its last current TU definition/reference disappeared.
        tx.run('UNWIND $rows AS row MATCH(n:Artifact {id:row.id}) '
               'OPTIONAL MATCH(n)-[r:ENCODED_NAME_MATCH]->() DELETE r', rows=batch).consume()
        tx.run('UNWIND $rows AS row MATCH(n:Artifact {id:row.id}) WHERE NOT (n)--() DELETE n', rows=batch).consume()


def main(out):
    plan = json.loads((out / 'plan.json').read_text())
    if plan.get('identity_version') != VERSION:
        raise ContextError('Legacy sealed delta requires explicit identity migration; publication blocked')
    c = connect(BASE / 'state/refresh-index.sqlite')
    c.execute('CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT)'); c.commit()
    pending = c.execute('SELECT value FROM meta WHERE key="pending"').fetchone()
    if pending and pending[0] != str(out): raise ContextError('Another refresh is pending')
    actual = {path: sha(ROOT / path) for path in plan.get('producer_sha256', {})}
    actual['dependency-graph/memgraph_endpoint.py']=sha(BASE/'memgraph_endpoint.py')
    if actual != plan.get('producer_sha256', {}):
        raise ContextError('Publication producer changed; explicit reviewed supersession required')
    if pending:
        (out / ('resume-producers-' + str(time.time_ns()) + '.json')).write_text(json.dumps(actual, indent=2) + '\n')
    else:
        if actual != plan.get('producer_sha256', {}): raise ContextError('Refresh producer changed before staging')
        stage(c, out)
    d = sqlite3.connect(out / 'delta.sqlite'); d.row_factory = sqlite3.Row
    driver = GraphDatabase.driver(memgraph_uri(ROOT), auth=None)
    try:
        with driver.session() as session:
            session.run('MATCH(g:ContextGeneration {id:"active"}) SET g.state="refreshing"').consume()
            publication = publish(session, d, out / 'delta.sqlite', out / 'batch-commits.jsonl')
            print('publication: delta committed; checking and registering', flush=True)
            if plan.get('migration'):
                from migrate_source_identity import verify
                verify(session, out)
            nodes = {r['kind']: r['n'] for r in session.run('MATCH(n:Artifact) RETURN n.kind AS kind,count(n) AS n')}
            edges = {r['kind']: r['n'] for r in session.run('MATCH(:Artifact)-[r]->(:Artifact) RETURN type(r) AS kind,count(r) AS n')}
            report_path = out / 'refresh-report.json'; report = json.loads(report_path.read_text())
            report.update(node_kinds=nodes, edge_kinds=edges)
            report_path.write_text(json.dumps(report, indent=2) + '\n')
            changed = [path for path, digest in report['input_sha256'].items()
                       if not pathlib.Path(path).is_file() or sha(path) != digest]
            if changed:
                # The journal's snapshot was published atomically, but sources
                # have moved since it was staged. Keep the graph unavailable;
                # next prepare reconciles current TUs against this exact index.
                c.execute('INSERT OR REPLACE INTO meta VALUES(?,?)', ('unregistered_baseline', str(out)))
                c.execute('DELETE FROM meta WHERE key="pending"'); c.commit()
                (out / 'superseded.json').write_text(json.dumps({'changed': changed}, indent=2) + '\n')
                return
            register(session, out, reports=[report_path])
            session.run('MATCH(p:PublicationCheckpoint {id:$id}),(g:ContextGeneration {id:"active"}) '
                        'SET p.state="published",p.generation=g.digest',id=publication['checkpoint']).consume()
        c.execute('DELETE FROM meta WHERE key="pending"'); c.commit()
        c.execute('DELETE FROM meta WHERE key="unregistered_baseline"'); c.commit()
        (out / 'publication.json').write_text(json.dumps({'published': True, 'node_kinds': nodes, 'edge_kinds': edges, **publication}, indent=2) + '\n')
    finally:
        d.close(); c.close(); driver.close()


if __name__ == '__main__': main(pathlib.Path(sys.argv[1]))
