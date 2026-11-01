"""Build a new complete observation generation; never write production registry."""
import argparse
import csv
import hashlib
import json
import pathlib
import re
import shlex
import sqlite3
import time

from gcc_source_graph import parse_dump

ROOT = pathlib.Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.file_digest(path.open('rb'), 'sha256').hexdigest()


def ro(path):
    return sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run', required=True)
    p.add_argument('--gcc', required=True)
    p.add_argument('--extend-database')
    p.add_argument('--ast-subdir', default='ast2')
    a = p.parse_args()
    run = pathlib.Path(a.run).resolve()
    baseline = ROOT / 'dependency-graph/runs/baseline-01'
    ast = run / a.ast_subdir
    gccdir = pathlib.Path(a.gcc).resolve()
    assert json.loads((ast / 'report.json').read_text())['all_passed']
    assert json.loads((gccdir / 'report.json').read_text())['all_passed']
    extending = bool(a.extend_database)
    path = pathlib.Path(a.extend_database).resolve() if extending else run / 'graph.sqlite'
    assert path.exists() if extending else not path.exists()
    start = time.perf_counter()
    c = sqlite3.connect(path)
    if not extending:
        base = ro(baseline / 'graph.sqlite')
        base.backup(c)
        base.close()
    delta_nodes = 'core_delta_nodes' if extending else 'delta_nodes'
    delta_edges = 'core_delta_edges' if extending else 'delta_edges'
    c.executescript('CREATE TABLE ' + delta_nodes + '(id TEXT PRIMARY KEY); CREATE TABLE ' +
                   delta_edges + '(src TEXT,dst TEXT,kind TEXT,evidence TEXT, PRIMARY KEY(src,dst,kind,evidence));')
    metadata = {}
    inputs = {}
    changed = set()

    def node(key, kind, label, meta):
        if key not in metadata:
            old = c.execute('SELECT metadata FROM nodes WHERE id=?', (key,)).fetchone()
            metadata[key] = json.loads(old[0]) if old else {}
        merged = metadata[key]
        # Preserve evidence of definitions already seen in another TU.
        for field, value in meta.items():
            if field in ('source_definition', 'compiler_definition'):
                merged[field] = merged.get(field, False) or value
            elif value is not None:
                merged[field] = value
        c.execute('INSERT INTO nodes VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET '
                  'metadata=excluded.metadata,kind=excluded.kind,label=excluded.label',
                  (key, kind, label, json.dumps(merged, sort_keys=True)))
        c.execute('INSERT OR IGNORE INTO ' + delta_nodes + ' VALUES(?)', (key,))
        changed.add(key)
        return key

    def edge(src, dst, kind, evidence):
        values = (src, dst, kind, evidence)
        c.execute('INSERT OR IGNORE INTO edges VALUES(?,?,?,?)', values)
        c.execute('INSERT OR IGNORE INTO ' + delta_edges + ' VALUES(?,?,?,?)', values)

    # The full original catalog retains separate anchors for duplicate names/ranges.
    registry = ro(baseline / 'registry-snapshot.sqlite')
    registry.row_factory = sqlite3.Row
    catalogs = {}
    for row in registry.execute('SELECT * FROM catalog_symbols ORDER BY anchor'):
        row = dict(row)
        key = 'catalog:' + row['anchor']
        if not extending:
            node(key, 'CatalogSymbol', row['demangled'], row)
        catalogs.setdefault(row['mangled'], []).append(key)
        rid = 'symbol:' + row['elf'] + ':' + row['mangled']
        if not extending and c.execute('SELECT 1 FROM nodes WHERE id=?', (rid,)).fetchone():
            edge(rid, key, 'CATALOG_CANDIDATE', 'original catalog anchor; duplicate ranges preserved')
    for row in registry.execute('SELECT elf,mangled,metadata FROM records'):
        if extending:
            break
        entry = json.loads(row['metadata'])
        rid = 'symbol:' + row['elf'] + ':' + row['mangled']
        for field in ('validation', 'behavior_validation'):
            if entry.get(field):
                file = ROOT / 'uc-library' / entry[field]
                label = str(file.relative_to(ROOT))
                target = node('file:' + label, 'Proof', label, {
                    'recorded_sha256': entry.get(field + '_sha256'), 'provenance_field': field})
                edge(rid, target, 'VALIDATED_BY', json.dumps({'field': field,
                     'sha256': entry.get(field + '_sha256')}, sort_keys=True))
    owner = ro(baseline / 'ownership.sqlite')
    for obj, original in owner.execute('''SELECT d.object_id,s.id FROM definitions d
      JOIN original_symbols s ON s.mangled=d.mangled'''):
        if extending:
            break
        edge(obj, original, 'DEFINES', '')
    commands = json.loads((run / 'compile_commands.json').read_text())
    tests = [] if extending else json.loads((run / 'ctest-inventory.json').read_text())['tests']
    test_execs = {}
    for test in tests:
        tid = node('test:' + test['name'], 'Test', test['name'], test)
        argv = test.get('command', [])
        if not argv:
            continue
        executable = pathlib.Path(argv[0])
        if executable.is_relative_to(ROOT):
            label = str(executable.relative_to(ROOT))
            eid = node('file:' + label, 'file', label, {})
            edge(tid, eid, 'RUNS', 'CTest inventory')
            test_execs[eid] = tid
        for arg in argv[1:]:
            candidate = pathlib.Path(arg)
            if candidate.is_absolute() and candidate.is_relative_to(ROOT) and candidate.is_file():
                label = str(candidate.relative_to(ROOT))
                fid = node('file:' + label, 'Fixture', label, {'sha256': sha(candidate)})
                edge(tid, fid, 'USES_FIXTURE', 'explicit existing file argument in CTest command')
    clean = recovery = 0
    unresolved = 0
    for index, command in enumerate(commands):
        source = pathlib.Path(command['file'])
        source_label = str(source.relative_to(ROOT))
        ast_path = ast / f'{index:04d}.json'
        data = json.loads(ast_path.read_text())
        assert data['passed']
        clean += bool(data['parse_clean'])
        recovery += not data['parse_clean']
        inputs[str(ast_path)] = sha(ast_path)
        for ipath, digest in data['input_sha256'].items():
            if ipath in inputs and inputs[ipath] != digest:
                raise ValueError('Mixed source generations: ' + ipath)
            inputs[ipath] = digest
        ast_names = {}
        for key, value in data['nodes'].items():
            node(key, value['kind'], value['label'], value['metadata'])
            name = value['metadata'].get('mangled')
            if name and value['kind'] == 'Function':
                ast_names.setdefault(name, []).append(key)
            if value['kind'] == 'TranslationUnit':
                argv = command.get('arguments') or shlex.split(command['command'])
                obj = pathlib.Path(command['directory']) / argv[argv.index('-o') + 1]
                object_key = 'file:' + str(obj.relative_to(ROOT))
                if extending:
                    node(object_key, 'file', str(obj.relative_to(ROOT)), {})
                    depfile = pathlib.Path(str(obj) + '.d')
                    inputs[str(depfile)] = sha(depfile)
                    for token in shlex.split(depfile.read_text().replace('\\\n', '').partition(': ')[2]):
                        dependency = (pathlib.Path(command['directory']) / token).resolve()
                        label = str(dependency.relative_to(ROOT)) if dependency.is_relative_to(ROOT) else str(dependency)
                        node('file:' + label, 'file', label, {})
                        edge(object_key, 'file:' + label, 'compiler_input', str(depfile))
                    source_key = node('file:' + source_label, 'file', source_label, {})
                    edge(object_key, source_key, 'compiles', str(run / 'compile_commands.json'))
                edge(key, object_key, 'COMPILED_AS', 'compile_commands.json')
                for executable, in c.execute("SELECT src FROM edges WHERE dst=? AND kind='link_input'", (object_key,)).fetchall():
                    if executable in test_execs:
                        edge(test_execs[executable], key, 'HAS_TEST_TU', 'explicit CMake link operand + CTest command')
        for values in data['edges']:
            edge(*values)
        unresolved += len(data['unresolved'])
        compiler_path = gccdir / f'{index:04d}.json'
        compiler = json.loads(compiler_path.read_text())
        assert compiler['returncode'] == 0 and compiler['source_sha256'] == sha(source)
        dump = pathlib.Path(compiler['dump'])
        assert sha(dump) == compiler['dump_sha256']
        # New parser execution over preserved compiler output, not a relabelled old proof.
        records = parse_dump(dump.read_text())
        inputs[str(compiler_path)] = sha(compiler_path)
        ids = {}
        observed_names = {}
        for record in records.values():
            for name, number in record['calls'] + record['references']:
                if re.fullmatch(r'[A-Za-z_$][\w.$]*', name):
                    observed_names[number] = name
        for number, record in records.items():
            name = record['name']
            if not re.fullmatch(r'[A-Za-z_$][\w.$]*', name):
                name = observed_names.get(number)
            kind = 'Function' if 'function' in record.get('type', '') else 'Data'
            candidates = ast_names.get(name, []) if kind == 'Function' else []
            if len(candidates) == 1:
                key = candidates[0]
            elif name:
                local = name == 'main' or name.startswith('_ZL') or '_GLOBAL__N_' in name
                key = kind.lower() + ':' + (source_label + ':' if local else '') + name
            else:
                key = f'compiler:{"core-source-01:" if extending else ""}{index}:{number}'
            ids[number] = node(key, kind, record['demangled'], {
                'mangled': name, 'compiler_printed_name': record['name'],
                'compiler_definition': record['definition'], 'compiler_type': record.get('type'),
                'source_port_declaration': True})
        evidence = json.dumps({'gcc_input': str(compiler_path.relative_to(ROOT)),
                               'dump_sha256': compiler['dump_sha256'], 'source': source_label}, sort_keys=True)
        for number, record in records.items():
            for name, target in record['calls']:
                if target not in ids:
                    ids[target] = node('function:' + name, 'Function', name, {'mangled': name})
                edge(ids[number], ids[target], 'GCC_CALLS', evidence)
            for name, target in record['references']:
                if target not in ids:
                    ids[target] = node('data:' + name, 'Data', name, {'mangled': name})
                edge(ids[number], ids[target], 'ALIAS_OF' if 'alias' in record.get('type', '')
                     else 'GCC_REFERENCES', evidence)
            for n, description in enumerate(record['indirect']):
                key = node(f'unresolved:gcc:{"core-source-01:" if extending else ""}{index}:{number}:{n}', 'UnresolvedCall', description,
                           {'source': source_label, 'compiler_input': str(compiler_path.relative_to(ROOT))})
                edge(ids[number], key, 'GCC_UNRESOLVED', evidence)
        if index % 25 == 0:
            c.commit()
    if extending:
        for directory in {pathlib.Path(row['directory']) for row in commands}:
            for recipe in directory.glob('CMakeFiles/*/link.txt'):
                argv = shlex.split(recipe.read_text())
                inputs[str(recipe)] = sha(recipe)
                if not argv or pathlib.Path(argv[0]).name not in ('ar', 'gcc-ar', 'llvm-ar'):
                    continue
                output = next((v for v in argv[1:] if v.endswith('.a')), None)
                if not output:
                    continue
                archive = (directory / output).resolve()
                label = str(archive.relative_to(ROOT))
                node('file:' + label, 'file', label, {})
                for token in argv:
                    if token.endswith('.o'):
                        obj = (directory / token).resolve()
                        object_label = str(obj.relative_to(ROOT))
                        node('file:' + object_label, 'file', object_label, {})
                        edge('file:' + label, 'file:' + object_label, 'link_input', str(recipe))
    # Name matches remain explicit interface evidence, never ABI/behavior claims.
    for key, meta in metadata.items():
        name = meta.get('mangled')
        if key.startswith('function:') and name in catalogs:
            for target in catalogs[name]:
                edge(key, target, 'ENCODED_NAME_MATCH', 'source/compiler mangling only; not ABI proof')
    for ipath, digest in inputs.items():
        if sha(pathlib.Path(ipath)) != digest:
            raise ValueError('Input changed before publication: ' + ipath)
    c.commit()
    for table in ('nodes', 'edges'):
        query = ('SELECT n.* FROM nodes n JOIN ' + delta_nodes + ' d ON d.id=n.id ORDER BY n.id'
                 if table == 'nodes' else 'SELECT * FROM ' + delta_edges + ' ORDER BY kind,src,dst,evidence')
        with (run / ('delta-' + table + '.csv')).open('x') as stream:
            writer = csv.writer(stream)
            cursor = c.execute(query)
            writer.writerow([d[0] for d in cursor.description])
            writer.writerows(cursor)
    report = {'compile_commands': len(commands), 'gcc_native_passed': len(commands),
              'clang_clean': clean, 'clang_recovery_gcc_validated': recovery,
              'catalog_anchors': registry.execute('SELECT count(*) FROM catalog_symbols').fetchone()[0],
              'node_kinds': dict(c.execute('SELECT kind,count(*) FROM nodes GROUP BY kind')),
              'edge_kinds': dict(c.execute('SELECT kind,count(*) FROM edges GROUP BY kind')),
              'delta_nodes': c.execute('SELECT count(*) FROM ' + delta_nodes).fetchone()[0],
              'delta_edges': c.execute('SELECT count(*) FROM ' + delta_edges).fetchone()[0],
              'ast_unresolved_observations': unresolved,
              'input_sha256': inputs, 'merger_sha256': sha(pathlib.Path(__file__)),
              'compiler_dump_parser_sha256': sha(pathlib.Path(__file__).with_name('gcc_source_graph.py')),
              'seconds': time.perf_counter() - start,
              'scope': 'All selected compile commands and catalog anchors; static observations, unresolved dispatch explicit',
              'runtime_or_original_firmware_callgraph_complete': False}
    (run / 'full-graph.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ('clang_clean', 'clang_recovery_gcc_validated',
                                             'catalog_anchors', 'delta_nodes', 'delta_edges', 'seconds')}))
    c.close()


if __name__ == '__main__':
    main()
