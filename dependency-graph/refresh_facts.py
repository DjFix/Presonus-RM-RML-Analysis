"""Per-TU facts and dependency-aware replacement for the derived code index."""
import json
import pathlib
import re
import shlex
import sqlite3
import functools
import hashlib

from context_runtime import sha
from code_identity import VERSION, context_id, digest
from compact_facts import CompactFacts, create_schema
from stage_normalization import normalize_ast


def connect(path):
    c = sqlite3.connect(path)
    try:
        if c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='node_facts'").fetchone():
            raise ValueError('Explicit compact source-index migration required; legacy index left unchanged')
        c.execute('PRAGMA journal_mode=WAL')
        c.execute('PRAGMA synchronous=FULL')
        c.execute('PRAGMA foreign_keys=ON')
        c.execute('PRAGMA cache_size=-65536')
        create_schema(c)
        for statement in '''
          CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT);
          CREATE TABLE IF NOT EXISTS unit_observations(owner TEXT PRIMARY KEY,
            observation_id TEXT NOT NULL UNIQUE,payload TEXT NOT NULL);
          CREATE VIEW IF NOT EXISTS units AS SELECT owner,payload FROM unit_observations;
          CREATE VIEW IF NOT EXISTS observations AS
            SELECT observation_id AS id,owner,payload FROM unit_observations;
          CREATE VIEW IF NOT EXISTS current_observations AS
            SELECT owner,observation_id FROM unit_observations;
        '''.split(';'):
            if statement.strip():
                c.execute(statement)
        return c
    except BaseException:
        c.close()
        raise


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


def facts(root, owner, row, ast_path, gcc_path, catalog_lookup=None):
    ast, _ = normalize_ast(root, row, json.loads(ast_path.read_text()))
    gcc_bytes = gcc_path.read_bytes()
    gcc = json.loads(gcc_bytes)
    context = context_id(root, row)
    # GCC serials are capture-local and may change kind after a source edit.
    # Bind serial-based nodes (including indirect sites) to the exact capture.
    gcc_scope = context + ':' + hashlib.sha256(gcc_bytes).hexdigest()
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
            key = 'compiler:' + gcc_scope + ':' + number
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
                    named = re.fullmatch(r'[A-Za-z_$][\w.$]*', name)
                    key = category.lower() + ':' + name if named else 'compiler:' + gcc_scope + ':' + target
                    ids[target] = node(key, category, name, {'mangled': name if named else None})
                relation = 'ALIAS_OF' if field == 'references' and 'alias' in record.get('type', '') else kind
                edges.add((ids[number], ids[target], relation, evidence))
        for n, description in enumerate(record['indirect']):
            key = node('unresolved:gcc:' + gcc_scope + ':' + number + ':' + str(n),
                       'UnresolvedCall', description, {'source': source, 'context': context})
            edges.add((ids[number], key, 'GCC_UNRESOLVED', evidence))
    for key, value in nodes.items():
        name = value['metadata'].get('mangled')
        if key.startswith('function:') and name:
            lookup = catalogs(root) if catalog_lookup is None else catalog_lookup
            for target in lookup.get(name, []):
                edges.add((key, target, 'ENCODED_NAME_MATCH', 'source/compiler mangling only; not ABI proof'))
    return nodes, edges


def replace(c, owner, row, nodes, edges, inputs, ast, gcc, external_inputs=None):
    if not c.in_transaction:
        c.execute('BEGIN')
    changes = CompactFacts(c).replace_owner(owner, nodes, edges)
    payload = {'command': row, 'inputs': inputs, 'ast': str(ast), 'gcc': str(gcc),
               'ast_sha256': sha(ast), 'gcc_sha256': sha(gcc)}
    if external_inputs is not None: payload['external_inputs'] = external_inputs
    observation = dict(payload, owner=owner, identity_version=VERSION)
    observation_id = digest(observation)
    c.execute('''INSERT INTO unit_observations(owner,observation_id,payload) VALUES(?,?,?)
      ON CONFLICT(owner) DO UPDATE SET observation_id=excluded.observation_id,payload=excluded.payload
      WHERE unit_observations.observation_id<>excluded.observation_id''',
      (owner, observation_id, json.dumps(payload, sort_keys=True)))
    return changes


def merged_node(c, key):
    metadata = {}; kind = label = None
    merged_kind = None
    for kind, label, text in c.execute('SELECT kind,label,metadata FROM node_facts WHERE id=? ORDER BY owner', (key,)):
        if merged_kind is not None and kind != merged_kind:
            raise ValueError('Conflicting node kinds for ' + key + ': ' + merged_kind + ' vs ' + kind)
        merged_kind = kind
        for field, value in json.loads(text).items():
            if field in ('source_definition', 'compiler_definition'):
                metadata[field] = metadata.get(field, False) or value
            elif value is not None: metadata[field] = value
    return None if kind is None else {'id': key, 'kind': kind, 'label': label,
                                     'metadata': json.dumps(metadata, sort_keys=True)}
