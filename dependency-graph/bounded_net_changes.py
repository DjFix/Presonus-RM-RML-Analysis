"""Exact baseline-to-current effects using compact numeric observations and streamed payloads."""
from array import array
import json
from pathlib import Path
import sqlite3

from compact_facts import CompactFacts
from compact_identity_bitmap import IdentityBitmap
from incremental_delta import create_delta_schema


CHUNK = 1024
MAX_IDENTITIES = IdentityBitmap.MAX_IDENTITY
MAX_BASELINE_PAGE_CACHE_KIB = 32768
EDGE_ROWS = '''
SELECT b.observation_id,e.src_id,e.dst_id,e.kind_id,b.provenance_id
FROM compact_edge_observations b JOIN compact_logical_edges e USING(edge_id)
WHERE b.observation_id IN ({})
AND EXISTS(SELECT 1 FROM compact_edge_memberships m WHERE m.observation_id=b.observation_id)
'''
VALUE_TABLES = (
    ('compact_node_keys', 'node_id', 'value'),
    ('compact_kinds', 'kind_id', 'value'),
    ('compact_provenance', 'provenance_id', 'raw_evidence'),
)


def size(text):
    return len(text.encode('utf-8'))


def values(db, table, identity, column, keys):
    for first in range(0, len(keys), CHUNK):
        batch = keys[first:first + CHUNK]
        markers = ','.join('?' for _ in batch)
        yield from db.execute(
            f'SELECT {identity},{column} FROM {table} WHERE {identity} IN ({markers}) ORDER BY {identity}', batch,
        )


def sparse_map(keys):
    # Internal IDs remain intact until pruning, which the caller performs only
    # after publishing the exact delta journal. Zero marks an inactive mapping.
    last = keys[-1] if keys else 0
    if last > MAX_IDENTITIES:
        raise ValueError(f'Compact integer identity space exceeds bounded map: {last}')
    return array('I', [0]) * (last + 1)


class BoundedNetChanges:
    def __init__(self, writer, touched):
        self.writer = writer
        self.touched = touched
        self.current_store = CompactFacts(writer)
        filename, = (x[2] for x in writer.execute('PRAGMA database_list') if x[1] == 'main')
        self.reader = sqlite3.connect(Path(filename).resolve().as_uri() + '?mode=ro', uri=True)
        try:
            self.reader.execute(f'PRAGMA cache_size=-{MAX_BASELINE_PAGE_CACHE_KIB}')
            self.reader.execute('BEGIN')
            # Establish the WAL snapshot before the writer mutates ownership.
            self.reader.execute('SELECT owner_id FROM compact_owners ORDER BY owner_id LIMIT 1').fetchone()
            self.previous_store = CompactFacts(self.reader)
        except BaseException:
            self.reader.close()
            raise
        self.dictionary = None
        self.edges = None
        self.node_keys = None

    def close(self):
        if self.reader is not None:
            self.reader.close()
            self.reader = None

    def _node_rows(self):
        for identity, external in values(self.writer, *VALUE_TABLES[0], self.node_keys):
            before = self.previous_store._merged_node_support(identity, external)
            after = self.current_store._merged_node_support(identity, external)
            yield external, before, after

    def _scan_edges(self):
        touched = array('I', self.touched.observations)
        if len(touched) > MAX_IDENTITIES:
            raise ValueError('Compact observation population exceeds bounded stage')
        nodes, kinds, provenances = IdentityBitmap(), IdentityBitmap(), IdentityBitmap()
        operations, identities = array('b'), array('I')
        for first in range(0, len(touched), CHUNK):
            keys = touched[first:first + CHUNK]
            sql = EDGE_ROWS.format(','.join('?' for _ in keys))
            old = {r[0]: r[1:] for r in self.reader.execute(sql, keys)}
            current = {r[0]: r[1:] for r in self.writer.execute(sql, keys)}
            for identity in sorted(old.keys() ^ current.keys()):
                row = current.get(identity) or old[identity]
                src, dst, kind, evidence = row
                nodes.update((src, dst))
                kinds.add(kind)
                provenances.add(evidence)
                identities.append(identity)
                operations.append(1 if identity in current else -1)
        self.edges = identities, operations
        self.dictionary = tuple(array('I', keys) for keys in (nodes, kinds, provenances))

    def _strings(self):
        # Compact domains individually intern strings exactly. Cross-domain
        # matches still use exact text equality via the existing UNIQUE keys.
        mappings = tuple(sparse_map(keys) for keys in self.dictionary)
        assigned = 0
        for group, (schema, keys) in enumerate(zip(VALUE_TABLES, self.dictionary, strict=True)):
            for identity, text in values(self.writer, *schema, keys):
                prior = 0
                for category in range(min(group, 2)):
                    table, key, column = VALUE_TABLES[category]
                    row = self.writer.execute(
                        f'SELECT {key} FROM {table} WHERE {column}=?', (text,),
                    ).fetchone()
                    if row and row[0] < len(mappings[category]):
                        prior = mappings[category][row[0]]
                    if prior:
                        break
                if not prior:
                    assigned += 1
                    prior = assigned
                    yield mappings, (assigned, text)
                mappings[group][identity] = prior

    def plan(self):
        self.node_keys = array('I', self.touched.nodes)
        if len(self.node_keys) > MAX_IDENTITIES:
            raise ValueError('Compact node population exceeds bounded stage')
        self._scan_edges()
        affected = node_payload = node_transfer = key_payload = 0
        for external, before, after in self._node_rows():
            key_payload += size(external)
            if before != after:
                affected += 1
                node_payload += sum(map(size, after.values())) if after else size(external)
                node_transfer += size(json.dumps(after or {'id': external}, sort_keys=True))
        strings = string_payload = 0
        for _, (_, text) in self._strings():
            strings += 1
            string_payload += 8 + size(text)
        edge_count = len(self.edges[0])
        # Existing forecast replaces this estimate with exact serialized request
        # bytes before any publication or commit, as in normal staging.
        return dict(rows=len(self.node_keys) + affected + strings + edge_count + 1,
                    payload_bytes=key_payload + node_payload + string_payload + 48 * edge_count
                    + len('delta_storage_version') + 8,
                    graph_rows=affected + edge_count,
                    graph_payload_bytes=node_transfer + string_payload + 48 * edge_count)

    @property
    def nodes(self):
        return (text for _, text in values(self.writer, *VALUE_TABLES[0], self.node_keys))

    def write(self, db):
        create_delta_schema(db)
        for external, before, after in self._node_rows():
            db.execute('INSERT INTO changed_nodes VALUES(?)', (external,))
            if before == after:
                continue
            if after is None:
                db.execute('INSERT INTO orphan_nodes VALUES(?)', (external,))
            else:
                db.execute('INSERT INTO nodes VALUES(:id,:kind,:label,:metadata)', after)
        mappings = None
        for mappings, row in self._strings():
            db.execute('INSERT INTO delta_strings(id,value) VALUES(?,?)', row)
        ids, operations = self.edges
        assert not ids or mappings is not None
        for first in range(0, len(ids), CHUNK):
            batch = ids[first:first + CHUNK]
            markers = ','.join('?' for _ in batch)
            view = dict((row[0], row[1:]) for row in self.writer.execute('''
SELECT b.observation_id,e.src_id,e.dst_id,e.kind_id,b.provenance_id
FROM compact_edge_observations b JOIN compact_logical_edges e USING(edge_id)
WHERE b.observation_id IN (''' + markers + ')', batch))
            for index, identity in enumerate(batch, first):
                src, dst, kind, evidence = view[identity]
                db.execute('INSERT INTO delta_edges(operation,src,dst,kind,evidence) VALUES(?,?,?,?,?)',
                           (operations[index], mappings[0][src], mappings[0][dst],
                            mappings[1][kind], mappings[2][evidence]))
        db.execute('INSERT INTO settings VALUES(?,?)', ('delta_storage_version', 2))
        return {name: db.execute('SELECT count(*) FROM ' + name).fetchone()[0]
                for name in ('nodes', 'old_edges', 'new_edges', 'orphan_nodes')}
