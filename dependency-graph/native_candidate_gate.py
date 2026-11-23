"""Independent admission checks for affected current source candidate lifecycle.

This does not own historical candidate edges, repair omissions, or certify the
untouched join. The caller holds the existing writer lock through registration.
"""
import json
import pathlib
import sqlite3
from collections import defaultdict

from context_runtime import ContextError, inside, sha
from refresh_facts import merged_node
from native_candidate_ownership import unpack_guard

SETTING = 'native_candidate_guard'
BASIS = {'basis': 'encoded name only; not ABI proof'}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def digest(value):
    from native_candidate_ownership import digest as streaming_digest
    return streaming_digest(value)


def reject_native_sidecars(path):
    # Hashing only the main file cannot authenticate committed WAL contents or
    # a hot rollback journal. Never merge, checkpoint, or remove provider state.
    for suffix in ('-wal', '-journal'):
        sidecar = pathlib.Path(str(path) + suffix)
        if sidecar.is_file() and sidecar.stat().st_size:
            raise ContextError('Native candidate provider has active sidecar: ' + str(sidecar))


def open_native(root):
    pointer_path = root / 'dependency-graph/NATIVE_ACTIVE.json'
    if not pointer_path.is_file():
        raise ContextError('Native candidate pointer absent')
    pointer = json.loads(pointer_path.read_text())
    db_path = inside(root, pointer['database'])
    reject_native_sidecars(db_path)
    if sha(db_path) != pointer['sha256'] or sha(inside(root, pointer['report'])) != pointer['report_sha256']:
        raise ContextError('Native candidate provider hash mismatch')
    db = sqlite3.connect(db_path.as_uri() + '?mode=ro&immutable=1', uri=True)
    db.row_factory = sqlite3.Row
    try:
        for row in db.execute('SELECT path,sha256 FROM inputs'):
            if sha(inside(root, row['path'])) != row['sha256']:
                raise ContextError('Native candidate input changed: ' + row['path'])
    except BaseException:
        db.close()
        raise
    return db, pointer


def native_snapshot(db, row):
    meta = json.loads(row['metadata'])
    resolution = db.execute('SELECT * FROM symbol_resolution WHERE symbol_id=?', (row['id'],)).fetchone()
    return {'id': row['id'], 'kind': row['kind'], 'label': row['label'], 'elf': row['elf'],
            'metadata': meta, 'mangled': meta.get('mangled'), 'firmware': meta.get('firmware'),
            'resolution': dict(resolution) if resolution else None}


def matching_native_nodes(db, names):
    """Stream the immutable provider once; retain only matched snapshots.

    Preserve SQLite parameter coercion and the old 400-name chunk visitation
    order, including rejection when SQL-equivalent names span two chunks.
    Canonical JSON equality remains the final typed-name filter.
    """
    def sql_key(value):
        if value is None:
            return None  # SQL NULL never satisfies IN.
        return ('text' if isinstance(value, str) else 'number', value)

    chunks_by_value = defaultdict(set)
    values = list(names.values())
    for offset in range(0, len(values), 400):
        part = values[offset:offset + 400]
        # Bind through SQLite as before: unsupported types/overflow still fail,
        # and booleans/NaN retain SQLite's parameter conversion semantics.
        bound = db.execute('SELECT ' + ','.join('?' for _ in part), part).fetchone()
        for value in bound:
            key = sql_key(value)
            if key is not None:
                chunks_by_value[key].add(offset // 400)
    matched = []
    if values:
        query = "SELECT *, json_extract(metadata,'$.mangled') AS guard_mangled FROM nodes ORDER BY id"
        for row in db.execute(query):
            chunks = chunks_by_value.get(sql_key(row['guard_mangled']), ())
            if not chunks or canonical(json.loads(row['metadata']).get('mangled')) not in names:
                continue
            snapshot = native_snapshot(db, row)
            for chunk in chunks:
                matched.append((chunk, row['id'], snapshot))
    native = {}
    for _, identity, snapshot in sorted(matched, key=lambda entry: (entry[0], entry[1])):
        if identity in native:
            raise ContextError('Duplicate native provider identity: ' + identity)
        native[identity] = snapshot
    return native


def seal_guard(root, source_db, delta_db, *, bounded=False):
    """Return a seal; caller stores its exact JSON in delta settings and report."""
    root = pathlib.Path(root).resolve()
    db, pointer = open_native(root)  # Missing pointer and stale inputs fail closed.
    try:
        inputs = [dict(row) for row in db.execute('SELECT path,sha256 FROM inputs ORDER BY path')]
        affected = sorted(row[0] for row in delta_db.execute('SELECT id FROM changed_nodes'))
        sources = []
        owner_lists = {} if bounded else None
        for key in affected:
            node = merged_node(source_db, key)
            if node is None or node['kind'] != 'Function':
                continue
            owners = [row[0] for row in source_db.execute(
                'SELECT owner FROM node_facts WHERE id=? ORDER BY owner', (key,))]
            if not owners or not any(owner != '@build' for owner in owners):
                raise ContextError('Candidate gate current source ownership absent: ' + key)
            node['metadata'] = json.loads(node['metadata'])
            node['mangled'] = node['metadata'].get('mangled')
            node['path'] = node['metadata'].get('path') or node['metadata'].get('source')
            if owner_lists is not None:
                # A sealed owner list stays read-only throughout graph verification.
                owners = owner_lists.setdefault(tuple(owners), owners)
            sources.append({'properties': node, 'owners': owners})
        names = {canonical(node['properties']['mangled']): node['properties']['mangled']
                 for node in sources if node['properties']['mangled'] is not None}
        native = matching_native_nodes(db, names)
        native_by_name = defaultdict(list)
        for node in native.values():
            native_by_name[canonical(node['mangled'])].append(node)
        expected = [{'src': n['id'], 'dst': s['properties']['id'], 'properties': BASIS}
                    for s in sources if s['properties']['mangled'] is not None
                    for n in native_by_name[canonical(s['properties']['mangled'])]]
        seal = {'version': 1, 'scope': 'affected_current_function_candidate_completeness',
                'affected_ids': affected, 'sources': sources, 'native_nodes': native,
                'expected': sorted(expected, key=lambda e: (e['src'], e['dst'])),
                'native': {k: pointer[k] for k in ('database', 'sha256', 'report', 'report_sha256')},
                'native_inputs': inputs}
        seal['seal_sha256'] = digest(seal)
        check_native_files(root, seal)
        return seal
    finally:
        db.close()


def decoded_properties(props):
    result = dict(props)
    for field in ('metadata', 'resolution'):
        if isinstance(result.get(field), str):
            try:
                result[field] = json.loads(result[field])
            except ValueError as error:
                raise ContextError('Invalid candidate endpoint serialized property') from error
    return result


def endpoint(session, wanted, required_labels):
    rows = list(session.run('MATCH(n {id:$id}) RETURN properties(n) AS props,labels(n) AS labels', id=wanted['id']))
    if len(rows) != 1:
        raise ContextError('Missing/duplicate candidate endpoint: ' + wanted['id'])
    actual = decoded_properties(rows[0]['props'])
    if not set(required_labels) <= set(rows[0]['labels']) or any(canonical(actual.get(k)) != canonical(v) for k, v in wanted.items()):
        raise ContextError('Candidate endpoint differs from sealed provider: ' + wanted['id'])


BATCH_SIZE = 512


def endpoint_inventory(session, ids):
    """One global identity pass preserves duplicates outside required labels.

    Property lookups below use existing label/id indexes. An unlabeled id
    UNWIND would instead risk a whole graph scan for every requested id.
    """
    wanted = set(ids)
    counts = {}
    if wanted:
        # Keep cross-label duplicate detection, but filter on the server instead
        # of transferring every unrelated graph identity for a local update.
        for row in session.run('MATCH(n) WHERE n.id IN $ids RETURN n.id AS identity',
                               ids=sorted(wanted)):
            identity = row['identity']
            if identity in wanted:
                counts[identity] = counts.get(identity, 0) + 1
    return counts


def endpoint_batch(session, wanted_nodes, required_labels, inventory=None):
    """Bounded label-indexed property lookups plus global physical uniqueness."""
    wanted_nodes = list(wanted_nodes)
    if inventory is None:
        inventory = endpoint_inventory(session, (node['id'] for node in wanted_nodes))
    label = required_labels[0]
    if label not in ('Artifact', 'NativeArtifact'):
        raise ContextError('Unsupported candidate endpoint lookup label')
    for offset in range(0, len(wanted_nodes), BATCH_SIZE):
        part = wanted_nodes[offset:offset + BATCH_SIZE]
        for wanted in part:
            if inventory.get(wanted['id'], 0) != 1:
                raise ContextError('Missing/duplicate candidate endpoint: ' + wanted['id'])
        observed = defaultdict(list)
        for row in session.run('UNWIND $ids AS key MATCH(n:' + label + ' {id:key}) '
                'RETURN n.id AS identity,properties(n) AS props,labels(n) AS labels',
                ids=[node['id'] for node in part]):
            observed[row['identity']].append(row)
        for wanted in part:
            rows = observed[wanted['id']]
            if len(rows) != 1:
                raise ContextError('Missing/duplicate candidate endpoint: ' + wanted['id'])
            actual = decoded_properties(rows[0]['props'])
            if not set(required_labels) <= set(rows[0]['labels']) or any(
                    canonical(actual.get(k)) != canonical(v) for k, v in wanted.items()):
                raise ContextError('Candidate endpoint differs from sealed provider: ' + wanted['id'])


def incoming_edges(session, ids):
    # One complete typed relationship stream, rather than an unindexed lookup
    # for each affected destination. Filter only after reading every occurrence;
    # unknown labels and duplicate physical endpoints/relationships are retained.
    wanted = set(ids)
    if wanted:
        for row in session.run('MATCH(n)-[r:NATIVE_SOURCE_CANDIDATE]->(f) '
                'RETURN n.id AS src,f.id AS dst,properties(r) AS props,labels(n) AS src_labels,labels(f) AS dst_labels'):
            if row['dst'] in wanted:
                yield row


def check_native_files(root, seal):
    provider = seal['native']
    pointer_path = root / 'dependency-graph/NATIVE_ACTIVE.json'
    if not pointer_path.is_file():
        raise ContextError('Pinned native pointer absent')
    pointer = json.loads(pointer_path.read_text())
    if any(pointer.get(k) != v for k, v in provider.items()):
        raise ContextError('Native candidate pointer moved from sealed provider')
    reject_native_sidecars(inside(root, provider['database']))
    for path, expected in [(provider['database'], provider['sha256']),
                           (provider['report'], provider['report_sha256']),
                           *((row['path'], row['sha256']) for row in seal['native_inputs'])]:
        if sha(inside(root, path)) != expected:
            raise ContextError('Pinned native candidate provider changed: ' + path)


def reject_delta_sidecars(delta_path):
    for suffix in ('-wal', '-journal'):
        sidecar = pathlib.Path(str(delta_path) + suffix)
        if sidecar.is_file() and sidecar.stat().st_size:
            raise ContextError('Sealed candidate delta has active sidecar: ' + str(sidecar))


def verify_guard_inputs(session, root, delta_path, seal):
    """Bound provider/source preconditions without requiring candidate edges.

    Lifecycle reconciliation may use this before creating missing candidates.
    Caller retains the writer lock; this helper never writes graph or SQLite.
    """
    seal = unpack_guard(seal)
    root = pathlib.Path(root).resolve()
    if not isinstance(seal, dict):
        raise ContextError('Missing native candidate guard')
    body = dict(seal)
    bound = body.pop('seal_sha256', None)
    if body.get('version') != 1 or bound != digest(body) or not {'scope', 'affected_ids', 'sources', 'native_nodes', 'expected', 'native', 'native_inputs'} <= body.keys():
        raise ContextError('Invalid native candidate seal')
    reject_delta_sidecars(delta_path)
    with sqlite3.connect(pathlib.Path(delta_path).resolve().as_uri() + '?mode=ro&immutable=1', uri=True) as delta:
        row = delta.execute('SELECT value FROM settings WHERE key=?', (SETTING,)).fetchone()
        if not row or unpack_guard(json.loads(row[0])) != seal:
            raise ContextError('Native candidate seal is not bound to immutable delta')
    provider = seal['native']
    check_native_files(root, seal)
    marker = list(session.run('MATCH(g:NativeGeneration {id:"active"}) RETURN g.state AS state,g.digest AS digest'))
    if len(marker) != 1 or marker[0]['state'] != 'ready' or marker[0]['digest'] != provider['sha256']:
        raise ContextError('Native candidate generation is not pinned ready generation')
    ids = {source['properties']['id'] for source in seal['sources']}
    ids.update(seal['native_nodes'])
    inventory = endpoint_inventory(session, ids)
    endpoint_batch(session, (source['properties'] for source in seal['sources']), ('Artifact', 'Function'), inventory)
    endpoint_batch(session, seal['native_nodes'].values(), ('NativeArtifact',), inventory)
    check_native_files(root, seal)
    final_marker = list(session.run('MATCH(g:NativeGeneration {id:"active"}) RETURN g.state AS state,g.digest AS digest'))
    if final_marker != marker:
        raise ContextError('Native candidate generation changed during verification')
    reject_delta_sidecars(delta_path)


def verify_guard(session, root, delta_path, seal):
    """Check current completeness and absence of certified stale owned tuples.

    Legacy basis-only tuples are acceptable current evidence. Unknown historical
    extras remain untouched and unresolved; they never certify exact cleanup.
    """
    from native_candidate_ownership import validate_owned_edge, OwnershipVerification
    seal = unpack_guard(seal)

    root = pathlib.Path(root).resolve()
    verify_guard_inputs(session, root, delta_path, seal)
    provider = seal['native']
    expected = {(edge['src'], edge['dst']) for edge in seal['expected']}
    if len(expected) != len(seal['expected']):
        raise ContextError('Duplicate sealed expected native candidate')
    legacy_current = owned_current = unresolved = 0
    incoming_expected = {}
    verification = OwnershipVerification(session)
    for row in incoming_edges(session, seal['affected_ids']):
        pair = (row['src'], row['dst'])
        props = row['props']
        marked = any(str(key).startswith('candidate_') for key in props)
        if marked:
            validate_owned_edge(session, pair[0], pair[1], props, provider['sha256'], verification=verification)
            if pair not in expected:
                raise ContextError('Stale owned native candidate remains: ' + pair[1])
        if pair in expected:
            if 'NativeArtifact' not in row['src_labels'] or 'Artifact' not in row['dst_labels']:
                raise ContextError('Missing/duplicate native candidate relationship endpoint labels')
            incoming_expected[pair] = incoming_expected.get(pair, 0) + 1
            if canonical(props) == canonical(BASIS):
                legacy_current += 1
            elif marked:
                owned_current += 1
            else:
                raise ContextError('Foreign native candidate ownership properties')
        else:
            unresolved += 1
    if any(incoming_expected.get(pair, 0) != 1 for pair in expected):
        raise ContextError('Affected native candidate relationship inventory differs from exact current pairs')
    verify_guard_inputs(session, root, delta_path, seal)
    return {'version': 1, 'verified': True, 'scope': seal['scope'], 'seal_sha256': seal['seal_sha256'],
            'delta_sha256': sha(delta_path), 'native_generation': provider['sha256'],
            'affected_ids': len(seal['affected_ids']), 'current_functions': len(seal['sources']),
            'expected_candidates': len(seal['expected']), 'legacy_current_candidates': legacy_current,
            'certified_owned_current_candidates': owned_current,
            'stale_owned_candidates': 0, 'affected_unresolved_extra_occurrences': unresolved,
            'historical_extras': 'preserved; ownership unresolved',
            'untouched_join_verified': False, 'complete_cleanup': False, 'writes': 0}
