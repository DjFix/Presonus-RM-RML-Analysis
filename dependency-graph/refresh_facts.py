"""Per-TU facts and dependency-aware replacement for the derived code index."""
import json
import pathlib
import re
import shlex
import sqlite3
import functools

from context_runtime import sha
from code_identity import VERSION, context_id, normalize_ast, digest


def connect(path):
    c = sqlite3.connect(path)
    c.executescript('''PRAGMA journal_mode=WAL; PRAGMA synchronous=FULL;
      CREATE TABLE IF NOT EXISTS units(owner TEXT PRIMARY KEY, payload TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS node_facts(owner TEXT,id TEXT,kind TEXT,label TEXT,metadata TEXT,
        PRIMARY KEY(owner,id));
      CREATE INDEX IF NOT EXISTS node_fact_ids ON node_facts(id);
      CREATE TABLE IF NOT EXISTS edge_facts(owner TEXT,src TEXT,dst TEXT,kind TEXT,evidence TEXT,
        PRIMARY KEY(owner,src,dst,kind,evidence));
      CREATE INDEX IF NOT EXISTS edge_fact_keys ON edge_facts(src,dst,kind,evidence);
      CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT);
      CREATE TABLE IF NOT EXISTS observations(id TEXT PRIMARY KEY,owner TEXT NOT NULL,payload TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS current_observations(owner TEXT PRIMARY KEY,observation_id TEXT NOT NULL);
    ''')
    return c


def command_key(row):
    # The original AST unit ID includes the full captured row; retain it verbatim.
    return json.dumps(row, sort_keys=True)


@functools.lru_cache(maxsize=1)
def catalogs(root):
    path = root / 'dependency-graph/runs/baseline-01/registry-snapshot.sqlite'
    c = sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)
    result = {}
    for name, anchor in c.execute('SELECT mangled,anchor FROM catalog_symbols'):
        result.setdefault(name, []).append('catalog:' + anchor)
    c.close()
    return result


def dependencies(root, row):
    argv = row.get('arguments') or shlex.split(row['command'])
    obj = pathlib.Path(row['directory']) / argv[argv.index('-o') + 1]
    dep = pathlib.Path(str(obj) + '.d')
    paths = {str(pathlib.Path(row['file']).resolve())}
    if dep.exists():
        paths.update(str((pathlib.Path(row['directory']) / token).resolve()) for token in
                     shlex.split(dep.read_text().replace('\\\n', '').partition(': ')[2]))
    return {p: sha(p) for p in paths if pathlib.Path(p).is_relative_to(root) and pathlib.Path(p).is_file()}


def external_dependencies(root, row):
    argv = row.get('arguments') or shlex.split(row['command'])
    obj = pathlib.Path(row['directory']) / argv[argv.index('-o') + 1]
    dep = pathlib.Path(str(obj) + '.d')
    if not dep.exists(): return []
    paths = [(pathlib.Path(row['directory']) / token).resolve() for token in
             shlex.split(dep.read_text().replace('\\\n', '').partition(': ')[2])]
    return sorted(str(p) for p in paths if not p.is_relative_to(root))


def stale_units(c, rows, changed, all_units=False):
    previous = {owner: json.loads(payload) for owner, payload in c.execute('SELECT * FROM units')}
    wanted = {owner: row for owner, row in rows}
    changed = set(changed)
    dirty = {owner for owner, row in rows if all_units or owner not in previous or
             previous[owner]['command'] != row or changed.intersection(previous[owner]['inputs'])}
    return dirty, set(previous) - set(wanted)


def requires_reconfigure(changed, inventory_delta):
    # New/deleted headers can change __has_include even without a prior include
    # edge. New sources can change CMake globs. Neither is safely a leaf.
    return bool(inventory_delta) or any(str(path).endswith(
        ('.cmake', 'CMakeLists.txt', 'CMakeCache.txt', 'compile_commands.json')) for path in changed)


def facts(root, owner, row, ast_path, gcc_path):
    ast, _ = normalize_ast(root, row, json.loads(ast_path.read_text()))
    gcc = json.loads(gcc_path.read_text())
    context = context_id(root, row)
    if not ast.get('passed') or gcc.get('returncode') != 0:
        raise ValueError('Failed compiler observations: ' + owner)
    source = str(pathlib.Path(row['file']).relative_to(root))
    nodes = ast['nodes']; edges = set(map(tuple, ast['edges']))
    names = {}

    def node(key, kind, label, metadata):
        if key not in nodes:
            nodes[key] = {'kind': kind, 'label': label, 'metadata': {}}
        target = nodes[key]
        target['kind'], target['label'] = kind, label
        for field, value in metadata.items():
            if field in ('source_definition', 'compiler_definition'):
                target['metadata'][field] = target['metadata'].get(field, False) or value
            elif value is not None:
                target['metadata'][field] = value
        return key

    for key, value in list(nodes.items()):
        if value['kind'] == 'Function' and value['metadata'].get('mangled'):
            names.setdefault(value['metadata']['mangled'], []).append(key)
        if value['kind'] == 'TranslationUnit':
            argv = row.get('arguments') or shlex.split(row['command'])
            obj = pathlib.Path(row['directory']) / argv[argv.index('-o') + 1]
            object_key = 'file:' + str(obj.relative_to(root))
            node(object_key, 'file', object_key[5:], {})
            edges.add((key, object_key, 'COMPILED_AS', 'compile_commands.json'))
    records = gcc['symbols']; observed = {}; ids = {}
    for record in records.values():
        for name, number in record['calls'] + record['references']:
            if re.fullmatch(r'[A-Za-z_$][\w.$]*', name): observed[number] = name
    for number, record in records.items():
        name = record['name']
        if not re.fullmatch(r'[A-Za-z_$][\w.$]*', name): name = observed.get(number)
        kind = 'Function' if 'function' in record.get('type', '') else 'Data'
        candidates = names.get(name, []) if kind == 'Function' else []
        if len(candidates) == 1: key = candidates[0]
        elif name:
            local = name == 'main' or name.startswith('_ZL') or '_GLOBAL__N_' in name
            key = kind.lower() + ':' + (source + ':' if local else '') + name
        else:
            key = 'compiler:' + context + ':' + number
        ids[number] = node(key, kind, record['demangled'], {
            'mangled': name, 'compiler_printed_name': record['name'],
            'compiler_definition': record['definition'], 'compiler_type': record.get('type'),
            'source_port_declaration': True})
    evidence = json.dumps({'context': context, 'source': source, 'identity_version': VERSION}, sort_keys=True)
    for number, record in records.items():
        for field, kind in [('calls', 'GCC_CALLS'), ('references', 'GCC_REFERENCES')]:
            for name, target in record[field]:
                if target not in ids:
                    category = 'Function' if field == 'calls' else 'Data'
                    ids[target] = node(category.lower() + ':' + name, category, name, {'mangled': name})
                relation = 'ALIAS_OF' if field == 'references' and 'alias' in record.get('type', '') else kind
                edges.add((ids[number], ids[target], relation, evidence))
        for n, description in enumerate(record['indirect']):
            key = node('unresolved:gcc:' + context + ':' + number + ':' + str(n),
                       'UnresolvedCall', description, {'source': source, 'context': context})
            edges.add((ids[number], key, 'GCC_UNRESOLVED', evidence))
    for key, value in nodes.items():
        name = value['metadata'].get('mangled')
        if key.startswith('function:') and name:
            for target in catalogs(root).get(name, []):
                edges.add((key, target, 'ENCODED_NAME_MATCH', 'source/compiler mangling only; not ABI proof'))
    return nodes, edges


def replace(c, owner, row, nodes, edges, inputs, ast, gcc, external_inputs=None):
    c.execute('DELETE FROM node_facts WHERE owner=?', (owner,))
    c.execute('DELETE FROM edge_facts WHERE owner=?', (owner,))
    c.executemany('INSERT INTO node_facts VALUES(?,?,?,?,?)',
                  ((owner, key, v['kind'], v['label'], json.dumps(v['metadata'], sort_keys=True))
                   for key, v in nodes.items()))
    c.executemany('INSERT OR IGNORE INTO edge_facts VALUES(?,?,?,?,?)',
                  ((owner, *e) for e in edges))
    payload = {'command': row, 'inputs': inputs, 'ast': str(ast), 'gcc': str(gcc),
               'ast_sha256': sha(ast), 'gcc_sha256': sha(gcc)}
    if external_inputs is not None: payload['external_inputs'] = external_inputs
    observation = dict(payload, owner=owner, identity_version=VERSION)
    text = json.dumps(observation, sort_keys=True)
    observation_id = digest(observation)
    c.execute('INSERT OR IGNORE INTO observations VALUES(?,?,?)', (observation_id, owner, text))
    c.execute('INSERT OR REPLACE INTO current_observations VALUES(?,?)', (owner, observation_id))
    c.execute('INSERT OR REPLACE INTO units VALUES(?,?)', (owner, json.dumps(payload, sort_keys=True)))


def merged_node(c, key):
    metadata = {}; kind = label = None
    for kind, label, text in c.execute('SELECT kind,label,metadata FROM node_facts WHERE id=? ORDER BY owner', (key,)):
        for field, value in json.loads(text).items():
            if field in ('source_definition', 'compiler_definition'):
                metadata[field] = metadata.get(field, False) or value
            elif value is not None: metadata[field] = value
    return None if kind is None else {'id': key, 'kind': kind, 'label': label,
                                     'metadata': json.dumps(metadata, sort_keys=True)}
