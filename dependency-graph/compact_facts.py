"""Compact, transaction-owned per-owner facts for the derived code index.

No operational database is opened implicitly. Callers own commit/rollback and
publication. Compatibility views are read-only; all updates use replace_owner.
Unreferenced interned rows remain until explicit touched-only pruning.
"""
from dataclasses import dataclass, field
from collections import OrderedDict
import itertools
import sys
import hashlib
import json
import sqlite3


SCHEMA = '''
CREATE TABLE IF NOT EXISTS compact_owners(owner_id INTEGER PRIMARY KEY, value TEXT NOT NULL UNIQUE);
CREATE TABLE IF NOT EXISTS compact_node_keys(node_id INTEGER PRIMARY KEY, value TEXT NOT NULL UNIQUE);
CREATE TABLE IF NOT EXISTS compact_kinds(kind_id INTEGER PRIMARY KEY, value TEXT NOT NULL UNIQUE);
CREATE TABLE IF NOT EXISTS compact_atoms(atom_id INTEGER PRIMARY KEY, value TEXT NOT NULL UNIQUE);
CREATE TABLE IF NOT EXISTS compact_node_values(
 value_id INTEGER PRIMARY KEY, kind_id INTEGER NOT NULL REFERENCES compact_kinds,
 label TEXT NOT NULL, metadata TEXT NOT NULL, fingerprint BLOB NOT NULL);
CREATE INDEX IF NOT EXISTS compact_value_fingerprints ON compact_node_values(fingerprint);
CREATE INDEX IF NOT EXISTS compact_value_kinds ON compact_node_values(kind_id);
CREATE TABLE IF NOT EXISTS compact_node_memberships(
 owner_id INTEGER NOT NULL REFERENCES compact_owners,
 node_id INTEGER NOT NULL REFERENCES compact_node_keys,
 value_id INTEGER NOT NULL REFERENCES compact_node_values,
 PRIMARY KEY(owner_id,node_id)) WITHOUT ROWID;
CREATE INDEX IF NOT EXISTS compact_node_support ON compact_node_memberships(node_id,owner_id);
CREATE INDEX IF NOT EXISTS compact_node_value_support ON compact_node_memberships(value_id);
CREATE TABLE IF NOT EXISTS compact_logical_edges(
 edge_id INTEGER PRIMARY KEY,
 src_id INTEGER NOT NULL REFERENCES compact_node_keys,
 dst_id INTEGER NOT NULL REFERENCES compact_node_keys,
 kind_id INTEGER NOT NULL REFERENCES compact_kinds,
 UNIQUE(src_id,dst_id,kind_id));
CREATE INDEX IF NOT EXISTS compact_edge_destinations ON compact_logical_edges(dst_id,edge_id);
CREATE INDEX IF NOT EXISTS compact_edge_kinds ON compact_logical_edges(kind_id);
CREATE TABLE IF NOT EXISTS compact_provenance(
 provenance_id INTEGER PRIMARY KEY, fingerprint BLOB NOT NULL,
 raw_evidence TEXT NOT NULL,
 path_id INTEGER REFERENCES compact_atoms, line INTEGER, column_number INTEGER,
 tu_id INTEGER REFERENCES compact_atoms, context_id INTEGER REFERENCES compact_atoms,
 source_id INTEGER REFERENCES compact_atoms);
CREATE INDEX IF NOT EXISTS compact_provenance_fingerprints ON compact_provenance(fingerprint);
CREATE INDEX IF NOT EXISTS compact_provenance_paths ON compact_provenance(path_id);
CREATE INDEX IF NOT EXISTS compact_provenance_tus ON compact_provenance(tu_id);
CREATE INDEX IF NOT EXISTS compact_provenance_contexts ON compact_provenance(context_id);
CREATE INDEX IF NOT EXISTS compact_provenance_sources ON compact_provenance(source_id);
CREATE TABLE IF NOT EXISTS compact_edge_observations(
 observation_id INTEGER PRIMARY KEY,
 edge_id INTEGER NOT NULL REFERENCES compact_logical_edges,
 provenance_id INTEGER NOT NULL REFERENCES compact_provenance,
 UNIQUE(edge_id,provenance_id));
CREATE INDEX IF NOT EXISTS compact_observation_provenance ON compact_edge_observations(provenance_id,observation_id);
CREATE TABLE IF NOT EXISTS compact_edge_memberships(
 owner_id INTEGER NOT NULL REFERENCES compact_owners,
 observation_id INTEGER NOT NULL REFERENCES compact_edge_observations,
 PRIMARY KEY(owner_id,observation_id)) WITHOUT ROWID;
CREATE INDEX IF NOT EXISTS compact_edge_support ON compact_edge_memberships(observation_id,owner_id);
CREATE VIEW IF NOT EXISTS node_facts AS
 SELECT o.value AS owner,n.value AS id,k.value AS kind,v.label,v.metadata
 FROM compact_node_memberships m
 JOIN compact_owners o USING(owner_id) JOIN compact_node_keys n USING(node_id)
 JOIN compact_node_values v USING(value_id) JOIN compact_kinds k USING(kind_id);
CREATE VIEW IF NOT EXISTS edge_facts AS
 SELECT o.value AS owner,s.value AS src,d.value AS dst,k.value AS kind,p.raw_evidence AS evidence
 FROM compact_edge_memberships m JOIN compact_owners o USING(owner_id)
 JOIN compact_edge_observations b USING(observation_id)
 JOIN compact_logical_edges e USING(edge_id)
 JOIN compact_node_keys s ON s.node_id=e.src_id JOIN compact_node_keys d ON d.node_id=e.dst_id
 JOIN compact_kinds k USING(kind_id) JOIN compact_provenance p USING(provenance_id);
'''


def create_schema(db):
    """Create only compact fact tables/views; preserve the caller's transaction."""
    legacy = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('node_facts','edge_facts')").fetchall()
    if legacy:
        raise ValueError('Legacy backing tables require an explicit staging migration')
    for statement in SCHEMA.split(';'):
        if statement.strip():
            db.execute(statement)


def connect(path):
    """Create/open an explicitly selected compact store (never a legacy store)."""
    db = sqlite3.connect(path)
    try:
        db.execute('PRAGMA foreign_keys=ON')
        create_schema(db)
        return db
    except BaseException:
        db.close()
        raise


@dataclass(frozen=True)
class NodeSupportChange:
    node_id: int
    before: tuple
    after: tuple


@dataclass(frozen=True)
class EdgeSupportChange:
    edge_id: int
    src: str
    dst: str
    kind: str
    evidence: str
    before_owners: tuple
    after_owners: tuple


@dataclass(frozen=True)
class ChangeSet:
    changed_nodes: dict
    changed_edges: dict


@dataclass
class PruneCandidates:
    owners: set = field(default_factory=set)
    values: set = field(default_factory=set)
    nodes: set = field(default_factory=set)
    observations: set = field(default_factory=set)

    def add(self, other):
        for name in ('owners', 'values', 'nodes', 'observations'):
            getattr(self, name).update(getattr(other, name))


@dataclass(frozen=True)
class MergedNodeChange:
    node_id: int
    before: object
    after: object


@dataclass(frozen=True)
class MergedEdgeChange:
    edge_id: int
    src: str
    dst: str
    kind: str
    evidence: str
    before_exists: bool
    after_exists: bool


@dataclass(frozen=True)
class MergedChangeSet:
    changed_nodes: dict
    changed_edges: dict
    prune: PruneCandidates


class _ImportCache:
    """Per-call interning acceleration, bounded in entries and retained bytes."""
    def __init__(self, max_entries=4096, max_bytes=4 * 1024 * 1024):
        self.entries = OrderedDict()
        self.bytes = 0
        self.max_entries, self.max_bytes = max_entries, max_bytes

    @staticmethod
    def weight(value):
        return sys.getsizeof(value) + (sum(_ImportCache.weight(item) for item in value)
                                      if isinstance(value, tuple) else 0)

    def get(self, key):
        entry = self.entries.get(key)
        if entry is not None:
            self.entries.move_to_end(key)
            return entry[0]
        return None

    def put(self, key, value):
        weight = self.weight(key) + self.weight(value) + 128
        if weight > self.max_bytes:
            return
        previous = self.entries.pop(key, None)
        if previous:
            self.bytes -= previous[1]
        while self.entries and (len(self.entries) >= self.max_entries or self.bytes + weight > self.max_bytes):
            _, (_, removed) = self.entries.popitem(last=False)
            self.bytes -= removed
        self.entries[key] = (value, weight)
        self.bytes += weight


class CompactFacts:
    """Update memberships by differences; no commit and no provider/publication I/O.

    changed_nodes maps external keys to NodeSupportChange. Each before/after
    tuple contains (owner,kind,label,metadata_text) tuples, sorted by
    external owner. changed_edges maps integer observation IDs to changes with
    logical edge, exact raw evidence and before/after sorted owner tuples.
    Only changed memberships appear; shared values and provenance stay interned.
    """
    def __init__(self, connection):
        self.db = connection
        self._import_cache = None

    def _text(self, table, column, value):
        if not isinstance(value, str):
            raise ValueError('Fact identities, kinds, labels and evidence must be strings')
        cache_key = ('text', table, value)
        cached = self._import_cache.get(cache_key) if self._import_cache else None
        if cached is not None:
            return cached
        found = self.db.execute(f'SELECT {column} FROM {table} WHERE value=?', (value,)).fetchone()
        identity = found[0] if found else self.db.execute(f'INSERT INTO {table}(value) VALUES(?)', (value,)).lastrowid
        if self._import_cache is not None:
            self._import_cache.put(cache_key, identity)
        return identity

    def _owner(self, value):
        return self._text('compact_owners', 'owner_id', value)

    def _node_key(self, value):
        return self._text('compact_node_keys', 'node_id', value)

    def _kind(self, value):
        return self._text('compact_kinds', 'kind_id', value)

    def _atom(self, value):
        return self._text('compact_atoms', 'atom_id', value) if isinstance(value, str) else None

    def _value(self, node):
        kind = self._kind(node['kind'])
        label, metadata = node['label'], node['metadata']
        if not isinstance(label, str) or not isinstance(metadata, dict):
            raise ValueError('Node label must be a string and metadata an object')
        text = json.dumps(metadata, sort_keys=True)
        cache_key = ('value', kind, label, text)
        cached = self._import_cache.get(cache_key) if self._import_cache else None
        if cached is not None:
            return cached, kind
        fingerprint = hashlib.sha256(json.dumps([kind, label, text]).encode()).digest()
        for value_id, other_kind, other_label, other_text in self.db.execute(
                'SELECT value_id,kind_id,label,metadata FROM compact_node_values WHERE fingerprint=?', (fingerprint,)):
            if (other_kind, other_label, other_text) == (kind, label, text):
                if self._import_cache is not None:
                    self._import_cache.put(cache_key, value_id)
                return value_id, kind
        value_id = self.db.execute('INSERT INTO compact_node_values(kind_id,label,metadata,fingerprint) VALUES(?,?,?,?)',
                                   (kind, label, text, fingerprint)).lastrowid
        if self._import_cache is not None:
            self._import_cache.put(cache_key, value_id)
        return value_id, kind

    def _provenance(self, evidence):
        if not isinstance(evidence, str):
            raise ValueError('Evidence must be an exact raw string')
        cache_key = ('provenance', evidence)
        cached = self._import_cache.get(cache_key) if self._import_cache else None
        if cached is not None:
            return cached
        fingerprint = hashlib.sha256(evidence.encode()).digest()
        for identity, raw in self.db.execute(
                'SELECT provenance_id,raw_evidence FROM compact_provenance WHERE fingerprint=?', (fingerprint,)):
            if raw == evidence:
                if self._import_cache is not None:
                    self._import_cache.put(cache_key, identity)
                return identity
        try:
            parsed = json.loads(evidence)
        except ValueError:
            parsed = {}
        fields = parsed if isinstance(parsed, dict) else {}
        location = fields.get('location', {})
        if not isinstance(location, dict):
            location = {}
        path = fields.get('path', location.get('path', location.get('file')))
        line = fields.get('line', location.get('line'))
        column = fields.get('column', location.get('column'))
        # Unknown/non-scalar structured fields remain losslessly in raw_evidence.
        line = line if type(line) is int else None
        column = column if type(column) is int else None
        identity = self.db.execute('''INSERT INTO compact_provenance
            (fingerprint,raw_evidence,path_id,line,column_number,tu_id,context_id,source_id)
            VALUES(?,?,?,?,?,?,?,?)''',
            (fingerprint, evidence, self._atom(path), line, column, self._atom(fields.get('tu')),
             self._atom(fields.get('context')), self._atom(fields.get('source')))).lastrowid
        if self._import_cache is not None:
            self._import_cache.put(cache_key, identity)
        return identity

    def _observation(self, edge):
        src, dst, kind, evidence = edge
        src_id, dst_id, kind_id = self._node_key(src), self._node_key(dst), self._kind(kind)
        found = self.db.execute('SELECT edge_id FROM compact_logical_edges WHERE src_id=? AND dst_id=? AND kind_id=?',
                                (src_id, dst_id, kind_id)).fetchone()
        edge_id = found[0] if found else self.db.execute(
            'INSERT INTO compact_logical_edges(src_id,dst_id,kind_id) VALUES(?,?,?)',
            (src_id, dst_id, kind_id)).lastrowid
        provenance_id = self._provenance(evidence)
        found = self.db.execute('SELECT observation_id FROM compact_edge_observations WHERE edge_id=? AND provenance_id=?',
                                (edge_id, provenance_id)).fetchone()
        return found[0] if found else self.db.execute(
            'INSERT INTO compact_edge_observations(edge_id,provenance_id) VALUES(?,?)',
            (edge_id, provenance_id)).lastrowid

    def _node_support(self, node_id):
        rows = self.db.execute('''SELECT o.value,v.value_id,k.value,v.label,v.metadata
            FROM compact_node_memberships m JOIN compact_owners o USING(owner_id)
            JOIN compact_node_values v USING(value_id) JOIN compact_kinds k USING(kind_id)
            WHERE m.node_id=? ORDER BY o.value''', (node_id,))
        return tuple((owner, kind, label, metadata)
                     for owner, value_id, kind, label, metadata in rows)

    def _merged_node_support(self, node_id, external):
        from incremental_delta import merged_support_ordered
        # Repeated equal interned values are idempotent under the merge rules.
        # Keep their last external-owner position: ordinary fields use last
        # non-None assignment and definition flags use boolean OR. Aggregate
        # only IDs/owner names BEFORE joining wide metadata, so SQLite never
        # sorts hundreds of duplicate metadata blobs for a shared node.
        rows = self.db.execute("""SELECT support.last_owner,support.first_owner,k.value,v.label,v.metadata
            FROM (SELECT m.value_id,MIN(o.value) AS first_owner,MAX(o.value) AS last_owner
                  FROM compact_node_memberships m JOIN compact_owners o USING(owner_id)
                  WHERE m.node_id=? GROUP BY m.value_id) AS support
            JOIN compact_node_values v USING(value_id) JOIN compact_kinds k USING(kind_id)
            ORDER BY support.last_owner""", (node_id,))
        first_truthy = {}

        def contributions():
            for last_owner, first_owner, kind, label, metadata in rows:
                for flag, value in json.loads(metadata).items():
                    if flag in ('source_definition', 'compiler_definition') and value:
                        if flag not in first_truthy or first_owner < first_truthy[flag][0]:
                            first_truthy[flag] = (first_owner, value)
                yield last_owner, kind, label, metadata

        result = merged_support_ordered(external, contributions())
        if result is not None and first_truthy:
            # Python OR preserves the first truthy operand, including its JSON
            # type. Keep that exact legacy behavior even for non-boolean input.
            metadata = json.loads(result['metadata'])
            metadata.update((flag, value) for flag, (_, value) in first_truthy.items())
            result['metadata'] = json.dumps(metadata, sort_keys=True)
        return result

    def _edge_exists(self, observation_id):
        return self.db.execute('SELECT 1 FROM compact_edge_memberships WHERE observation_id=? LIMIT 1',
                               (observation_id,)).fetchone() is not None

    def _edge_support(self, observation_id):
        return tuple(row[0] for row in self.db.execute('''SELECT o.value
            FROM compact_edge_memberships m JOIN compact_owners o USING(owner_id)
            WHERE observation_id=? ORDER BY o.value''', (observation_id,)))

    def _edge_change(self, observation_id, before, after):
        edge_id, src, dst, kind, evidence = self.db.execute('''SELECT e.edge_id,s.value,d.value,k.value,p.raw_evidence
            FROM compact_edge_observations b JOIN compact_logical_edges e USING(edge_id)
            JOIN compact_node_keys s ON s.node_id=e.src_id JOIN compact_node_keys d ON d.node_id=e.dst_id
            JOIN compact_kinds k USING(kind_id) JOIN compact_provenance p USING(provenance_id)
            WHERE b.observation_id=?''', (observation_id,)).fetchone()
        return EdgeSupportChange(edge_id, src, dst, kind, evidence, before, after)

    def import_owner(self, owner, nodes, edges, batch_size=256):
        '''Stream facts into an EMPTY owner without support materialization.

        nodes is a mapping or an iterable of (key,{kind,label,metadata}) pairs;
        edges streams (src,dst,kind,raw_evidence). Returns inserted row counts.
        Every node checks one indexed kind representative. Induction from an
        empty store, with all API writes preserving homogeneous kinds, makes
        this a global check without scanning accumulated shared owners.
        Per-call bounded interning caches are discarded on success or rollback.
        This never commits; errors roll back this complete owner import.
        '''
        if not isinstance(owner, str) or type(batch_size) is not int or not 1 <= batch_size <= 4096:
            raise ValueError('Import needs a string owner and batch_size in 1..4096')
        if self._import_cache is not None:
            raise ValueError('Reentrant owner import is forbidden')
        if not self.db.in_transaction:
            self.db.execute('BEGIN')
        self.db.execute('SAVEPOINT compact_import_owner')
        self._import_cache = _ImportCache()
        try:
            owner_id = self._owner(owner)
            if self.db.execute('SELECT 1 FROM compact_node_memberships WHERE owner_id=? LIMIT 1', (owner_id,)).fetchone() or self.db.execute(
                    'SELECT 1 FROM compact_edge_memberships WHERE owner_id=? LIMIT 1', (owner_id,)).fetchone():
                raise ValueError('Import destination owner is not empty: ' + owner)

            def node_memberships():
                for key, value in nodes.items() if hasattr(nodes, 'items') else nodes:
                    node_id = self._node_key(key)
                    value_id, kind_id = self._value(value)
                    representative = self.db.execute('''SELECT v.kind_id FROM compact_node_memberships m
                        JOIN compact_node_values v USING(value_id) WHERE m.node_id=? LIMIT 1''', (node_id,)).fetchone()
                    if representative is not None and representative[0] != kind_id:
                        raise ValueError('Conflicting node kinds for ' + key)
                    yield owner_id, node_id, value_id

            def insert_batches(query, rows):
                count = 0
                rows = iter(rows)
                while True:
                    batch = list(itertools.islice(rows, batch_size))
                    if not batch:
                        return count
                    count += self.db.executemany(query, batch).rowcount

            node_count = insert_batches('INSERT INTO compact_node_memberships VALUES(?,?,?)', node_memberships())
            edge_count = insert_batches('INSERT OR IGNORE INTO compact_edge_memberships VALUES(?,?)',
                                        ((owner_id, self._observation(edge)) for edge in edges))
            self.db.execute('RELEASE compact_import_owner')
            return {'nodes': node_count, 'edges': edge_count}
        except BaseException:
            self._rollback_savepoint('compact_import_owner')
            raise
        finally:
            self._import_cache = None

    def _rollback_savepoint(self, name):
        # SQLITE_INTERRUPT / IO errors can automatically roll back the entire
        # transaction. Cleanup must never replace the original failure.
        if self.db.in_transaction:
            try:
                self.db.execute('ROLLBACK TO ' + name)
                self.db.execute('RELEASE ' + name)
            except sqlite3.Error:
                pass

    def plan_owner_rows(self, owner, nodes, edges, changed_nodes, changed_edges):
        """Read-only exact insert/update/delete row plan under caller's write lock.

        Equality uses the same full values and collision checks as interning.
        This caches only this owner's lookups; no hypothetical SQL is executed.
        Membership differences are supplied by the already checked preview.
        """
        counts = {}
        payload_bytes = 0
        caches = {}

        def insert(table, size):
            nonlocal payload_bytes
            counts[table] = counts.get(table, 0) + 1
            payload_bytes += size

        def text(table, column, value):
            if not isinstance(value, str):
                raise ValueError('Fact identities, kinds, labels and evidence must be strings')
            cache = caches.setdefault(table, {})
            if value not in cache:
                row = self.db.execute(f'SELECT {column} FROM {table} WHERE value=?', (value,)).fetchone()
                if row:
                    cache[value] = row[0]
                else:
                    insert(table, 8 + len(value.encode('utf-8')))
                    cache[value] = ('new', table, value)
            return cache[value]

        def existing(identity):
            return isinstance(identity, int)

        if nodes or edges:
            text('compact_owners', 'owner_id', owner)
        values, logical, provenance, observations = {}, {}, {}, set()
        for key, node in nodes.items():
            label, metadata = node['label'], node['metadata']
            if any(not isinstance(value, str) for value in (key, node['kind'], label)) or not isinstance(metadata, dict):
                raise ValueError('Node identity/kind/label must be strings and metadata an object')
            # Preview already compared exact old/new values under the caller's
            # transaction. Unchanged memberships prove these interned rows exist.
            if key not in changed_nodes:
                continue
            text('compact_node_keys', 'node_id', key)
            kind = text('compact_kinds', 'kind_id', node['kind'])
            raw = json.dumps(metadata, sort_keys=True)
            value_key = (kind, label, raw)
            if value_key not in values:
                found = None
                if existing(kind):
                    fingerprint = hashlib.sha256(json.dumps([kind, label, raw]).encode()).digest()
                    found = next((r[0] for r in self.db.execute(
                        'SELECT value_id,kind_id,label,metadata FROM compact_node_values WHERE fingerprint=?',
                        (fingerprint,)) if tuple(r)[1:] == (kind, label, raw)), None)
                if found is None:
                    insert('compact_node_values', 48 + len(label.encode('utf-8')) + len(raw.encode('utf-8')))
                values[value_key] = found
        for src, dst, kind_name, evidence in edges:
            if any(not isinstance(value, str) for value in (src, dst, kind_name, evidence)):
                raise ValueError('Edge identities, kind and evidence must be strings')
            if (src, dst, kind_name, evidence) not in changed_edges:
                continue
            src_id = text('compact_node_keys', 'node_id', src)
            dst_id = text('compact_node_keys', 'node_id', dst)
            kind_id = text('compact_kinds', 'kind_id', kind_name)
            edge_key = (src_id, dst_id, kind_id)
            if edge_key not in logical:
                row = self.db.execute(
                    'SELECT edge_id FROM compact_logical_edges WHERE src_id=? AND dst_id=? AND kind_id=?',
                    edge_key).fetchone() if all(map(existing, edge_key)) else None
                if row:
                    logical[edge_key] = row[0]
                else:
                    insert('compact_logical_edges', 32)
                    logical[edge_key] = ('new-edge', edge_key)
            if not isinstance(evidence, str):
                raise ValueError('Evidence must be an exact raw string')
            if evidence not in provenance:
                fingerprint = hashlib.sha256(evidence.encode()).digest()
                identity = next((r[0] for r in self.db.execute(
                    'SELECT provenance_id,raw_evidence FROM compact_provenance WHERE fingerprint=?',
                    (fingerprint,)) if r[1] == evidence), None)
                if identity is None:
                    insert('compact_provenance', 88 + len(evidence.encode('utf-8')))
                    identity = ('new-provenance', evidence)
                    try:
                        fields = json.loads(evidence)
                    except ValueError:
                        fields = {}
                    fields = fields if isinstance(fields, dict) else {}
                    location = fields.get('location', {})
                    location = location if isinstance(location, dict) else {}
                    atoms = (fields.get('path', location.get('path', location.get('file'))),
                             fields.get('tu'), fields.get('context'), fields.get('source'))
                    for atom in atoms:
                        if isinstance(atom, str):
                            text('compact_atoms', 'atom_id', atom)
                provenance[evidence] = identity
            observation = (logical[edge_key], provenance[evidence])
            if observation not in observations:
                row = self.db.execute(
                    'SELECT observation_id FROM compact_edge_observations WHERE edge_id=? AND provenance_id=?',
                    observation).fetchone() if all(map(existing, observation)) else None
                if row is None:
                    insert('compact_edge_observations', 24)
                observations.add(observation)
        counts['compact_node_memberships'] = len(changed_nodes)
        counts['compact_edge_memberships'] = len(changed_edges)
        payload_bytes += 24 * len(changed_nodes) + 16 * len(changed_edges)
        return dict(rows=sum(counts.values()), tables=counts, payload_bytes=payload_bytes)

    def replace_owner(self, owner, nodes, edges, *, merged=False, savepoint=True):
        """Atomically replace one owner; outer transaction remains caller-owned.

        Nodes follow facts(): key -> {kind,label,metadata}. Edges are an iterable
        of (src,dst,kind,raw_evidence). A kind conflict with another current owner
        fails closed and rolls back this call, including newly interned values.
        merged=True is an opt-in staging contract returning merged before/after
        values and touched prune IDs instead of complete owner populations.
        """
        if type(savepoint) is not bool:
            raise ValueError('savepoint must be a boolean')
        if not savepoint:
            # Guarded staging cannot recover a partial owner and always aborts
            # the complete publication. Avoid a redundant disk subjournal for
            # each owner; this opt-out never starts or commits a transaction.
            if not self.db.in_transaction:
                raise ValueError('savepoint=False requires an active outer transaction')
            try:
                if not isinstance(owner, str):
                    raise ValueError('Owner must be a string')
                return self._replace_owner(owner, nodes, edges, merged=merged)
            except BaseException:
                if self.db.in_transaction:
                    self.db.rollback()
                raise
        if not isinstance(owner, str):
            raise ValueError('Owner must be a string')
        # BEGIN avoids the outermost SAVEPOINT RELEASE committing the operation.
        if not self.db.in_transaction:
            self.db.execute('BEGIN')
        self.db.execute('SAVEPOINT compact_replace_owner')
        try:
            result = self._replace_owner(owner, nodes, edges, merged=merged)
            self.db.execute('RELEASE compact_replace_owner')
            return result
        except BaseException:
            self._rollback_savepoint('compact_replace_owner')
            raise

    def _replace_owner(self, owner, nodes, edges, *, merged=False):
        edges = list(edges)
        found = self.db.execute('SELECT owner_id FROM compact_owners WHERE value=?', (owner,)).fetchone()
        if not found and not nodes and not edges:
            if merged == 'touched':
                return PruneCandidates()
            return MergedChangeSet({}, {}, PruneCandidates()) if merged else ChangeSet({}, {})
        owner_id = found[0] if found else self._owner(owner)
        old_nodes = dict(self.db.execute('SELECT node_id,value_id FROM compact_node_memberships WHERE owner_id=?', (owner_id,)))
        new_nodes, keys = {}, {}
        for key, node in nodes.items():
            node_id = self._node_key(key)
            value_id, kind_id = self._value(node)
            # API writes preserve homogeneous kinds. An identical membership
            # was already checked; changed values need one indexed other owner.
            if old_nodes.get(node_id) != value_id:
                representative = self.db.execute('''SELECT v.kind_id FROM compact_node_memberships m
                    JOIN compact_node_values v USING(value_id)
                    WHERE m.node_id=? AND m.owner_id!=? LIMIT 1''',
                    (node_id, owner_id)).fetchone()
                if representative is not None and representative[0] != kind_id:
                    raise ValueError('Conflicting node kinds for ' + key)
            new_nodes[node_id], keys[node_id] = value_id, key
        old_edges = {row[0] for row in self.db.execute(
            'SELECT observation_id FROM compact_edge_memberships WHERE owner_id=?', (owner_id,))}
        new_edges = {self._observation(edge) for edge in edges}
        changed_nodes = {key for key in old_nodes.keys() | new_nodes.keys() if old_nodes.get(key) != new_nodes.get(key)}
        changed_edges = old_edges ^ new_edges
        if merged is True:
            for key in changed_nodes:
                if key not in keys:
                    keys[key] = self.db.execute('SELECT value FROM compact_node_keys WHERE node_id=?', (key,)).fetchone()[0]
            before_nodes = {key: self._merged_node_support(key, keys[key]) for key in changed_nodes}
            before_edges = {key: self._edge_exists(key) for key in changed_edges}
        elif not merged:
            before_nodes = {key: self._node_support(key) for key in changed_nodes}
            before_edges = {key: self._edge_support(key) for key in changed_edges}
        for key in sorted(changed_nodes):
            if key in new_nodes:
                self.db.execute('''INSERT INTO compact_node_memberships VALUES(?,?,?)
                    ON CONFLICT(owner_id,node_id) DO UPDATE SET value_id=excluded.value_id''',
                    (owner_id, key, new_nodes[key]))
            else:
                self.db.execute('DELETE FROM compact_node_memberships WHERE owner_id=? AND node_id=?', (owner_id, key))
        self.db.executemany('DELETE FROM compact_edge_memberships WHERE owner_id=? AND observation_id=?',
                            ((owner_id, key) for key in sorted(old_edges - new_edges)))
        self.db.executemany('INSERT INTO compact_edge_memberships VALUES(?,?)',
                            ((owner_id, key) for key in sorted(new_edges - old_edges)))
        if merged:
            touched = PruneCandidates(owners={owner}, nodes=set(changed_nodes),
                                      observations=set(changed_edges))
            for key in changed_nodes:
                if key in old_nodes:
                    touched.values.add(old_nodes[key])
                if key in new_nodes:
                    touched.values.add(new_nodes[key])
            if merged == 'touched':
                return touched
            node_changes = {keys[key]: MergedNodeChange(
                key, before_nodes[key], self._merged_node_support(key, keys[key]))
                for key in changed_nodes}
            edge_changes = {}
            for key in changed_edges:
                edge = self._edge_change(key, (), ())
                edge_changes[key] = MergedEdgeChange(edge.edge_id, edge.src, edge.dst, edge.kind,
                                                     edge.evidence, before_edges[key], self._edge_exists(key))
            return MergedChangeSet(node_changes, edge_changes, touched)
        node_changes = {}
        for key in sorted(changed_nodes):
            external = keys.get(key)
            if external is None:
                external = self.db.execute('SELECT value FROM compact_node_keys WHERE node_id=?', (key,)).fetchone()[0]
            node_changes[external] = NodeSupportChange(key, before_nodes[key], self._node_support(key))
        return ChangeSet(node_changes, {key: self._edge_change(key, before_edges[key], self._edge_support(key))
                                        for key in sorted(changed_edges)})

    def prune_unreferenced(self, changes, before_mutation=None, *, max_batch=None):
        """Prune only entities touched by supplied ChangeSets after delta use.

        This never commits. Consume change snapshots first: a deleted internal
        ID may subsequently be reused by SQLite. Foreign references are checked
        on every deletion; unrelated interned history is never globally swept.
        Pass all per-owner changes for a staged transaction as one iterable.
        """
        if not self.db.in_transaction:
            self.db.execute('BEGIN')
        if isinstance(changes, (ChangeSet, MergedChangeSet, PruneCandidates)):
            changes = [changes]
        numeric_names = ('values', 'nodes', 'observations', 'edges', 'provenance', 'kinds', 'atoms')
        if max_batch:
            from compact_identity_bitmap import IdentityBitmap
            candidates = {name: IdentityBitmap() for name in numeric_names}
        else:
            candidates = {name: set() for name in numeric_names}
        candidates['owners'] = set()
        for change in changes:
            touched = change.prune if isinstance(change, MergedChangeSet) else change
            if isinstance(touched, PruneCandidates):
                for name in ('owners', 'values', 'nodes', 'observations'):
                    candidates[name].update(getattr(touched, name))
                continue
            candidates['observations'].update(change.changed_edges)
            for node in change.changed_nodes.values():
                candidates['nodes'].add(node.node_id)
                for owner, kind, label, metadata in node.before + node.after:
                    candidates['owners'].add(owner)
                    found = self.db.execute('SELECT kind_id FROM compact_kinds WHERE value=?', (kind,)).fetchone()
                    if not found:
                        continue
                    kind_id = found[0]
                    fingerprint = hashlib.sha256(json.dumps([kind_id, label, metadata]).encode()).digest()
                    candidates['values'].update(row[0] for row in self.db.execute(
                        'SELECT value_id FROM compact_node_values WHERE fingerprint=? AND kind_id=? AND label=? AND metadata=?',
                        (fingerprint, kind_id, label, metadata)))
            for edge in change.changed_edges.values():
                candidates['owners'].update(edge.before_owners + edge.after_owners)
        for identity in candidates['observations']:
            row = self.db.execute('SELECT edge_id,provenance_id FROM compact_edge_observations WHERE observation_id=?', (identity,)).fetchone()
            if row:
                candidates['edges'].add(row[0])
                candidates['provenance'].add(row[1])
        for identity in candidates['edges']:
            row = self.db.execute('SELECT src_id,dst_id,kind_id FROM compact_logical_edges WHERE edge_id=?', (identity,)).fetchone()
            if row:
                candidates['nodes'].update(row[:2])
                candidates['kinds'].add(row[2])
        for identity in candidates['values']:
            row = self.db.execute('SELECT kind_id FROM compact_node_values WHERE value_id=?', (identity,)).fetchone()
            if row:
                candidates['kinds'].add(row[0])
        for identity in candidates['provenance']:
            row = self.db.execute('SELECT path_id,tu_id,context_id,source_id FROM compact_provenance WHERE provenance_id=?', (identity,)).fetchone()
            if row:
                candidates['atoms'].update(value for value in row if value is not None)
        counts = {}
        def remove(table, column, values, guard):
            # Previous table removals affect this table's referential guard.
            # Plan eligible IDs now, charge them, then perform those exact rows.
            source = iter(values if max_batch else set(values))
            batches = iter(lambda: list(itertools.islice(source, max_batch)), []) if max_batch else [source]
            counts[table] = 0
            for batch in batches:
                planned = [value for value in batch if self.db.execute(
                    f'SELECT 1 FROM {table} WHERE {column}=? AND {guard}', (value,)).fetchone()]
                if before_mutation is not None and planned:
                    # As in normal staging, charge actual eligible payload and
                    # require exact planned/deleted row balance for each batch.
                    payload = sum(sum(len(value.encode('utf-8')) if isinstance(value, str)
                                      else len(value) if isinstance(value, bytes)
                                      else 8 if value is not None else 0
                                      for value in self.db.execute(
                                          f'SELECT * FROM {table} WHERE {column}=?', (identity,)).fetchone())
                                  for identity in planned)
                    before_mutation(table, len(planned), payload)
                removed = sum(self.db.execute(
                    f'DELETE FROM {table} WHERE {column}=? AND {guard}', (value,)).rowcount
                    for value in planned)
                if removed != len(planned):
                    raise ValueError('Prune row plan changed for ' + table)
                counts[table] += removed
        remove('compact_edge_observations', 'observation_id', candidates['observations'],
               'NOT EXISTS(SELECT 1 FROM compact_edge_memberships m WHERE m.observation_id=compact_edge_observations.observation_id)')
        remove('compact_logical_edges', 'edge_id', candidates['edges'],
               'NOT EXISTS(SELECT 1 FROM compact_edge_observations b WHERE b.edge_id=compact_logical_edges.edge_id)')
        remove('compact_provenance', 'provenance_id', candidates['provenance'],
               'NOT EXISTS(SELECT 1 FROM compact_edge_observations b WHERE b.provenance_id=compact_provenance.provenance_id)')
        remove('compact_node_values', 'value_id', candidates['values'],
               'NOT EXISTS(SELECT 1 FROM compact_node_memberships m WHERE m.value_id=compact_node_values.value_id)')
        remove('compact_node_keys', 'node_id', candidates['nodes'],
               'NOT EXISTS(SELECT 1 FROM compact_node_memberships m WHERE m.node_id=compact_node_keys.node_id) '
               'AND NOT EXISTS(SELECT 1 FROM compact_logical_edges e WHERE e.src_id=compact_node_keys.node_id OR e.dst_id=compact_node_keys.node_id)')
        owner_ids = [row[0] for owner in candidates['owners'] for row in self.db.execute(
            'SELECT owner_id FROM compact_owners WHERE value=?', (owner,))]
        remove('compact_owners', 'owner_id', owner_ids,
               'NOT EXISTS(SELECT 1 FROM compact_node_memberships m WHERE m.owner_id=compact_owners.owner_id) '
               'AND NOT EXISTS(SELECT 1 FROM compact_edge_memberships m WHERE m.owner_id=compact_owners.owner_id)')
        remove('compact_kinds', 'kind_id', candidates['kinds'],
               'NOT EXISTS(SELECT 1 FROM compact_node_values v WHERE v.kind_id=compact_kinds.kind_id) '
               'AND NOT EXISTS(SELECT 1 FROM compact_logical_edges e WHERE e.kind_id=compact_kinds.kind_id)')
        remove('compact_atoms', 'atom_id', candidates['atoms'],
               'NOT EXISTS(SELECT 1 FROM compact_provenance p WHERE p.path_id=compact_atoms.atom_id '
               'OR p.tu_id=compact_atoms.atom_id OR p.context_id=compact_atoms.atom_id OR p.source_id=compact_atoms.atom_id)')
        return counts
