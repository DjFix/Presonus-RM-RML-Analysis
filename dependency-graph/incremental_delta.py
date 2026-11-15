"""Accumulate net effects, not copies of the old/current edge populations."""
import json


def merged_support(key, rows):
    return merged_support_ordered(key, sorted(rows))


def merged_support_ordered(key, rows):
    """Merge a cursor already ordered by external owner, retaining one value."""
    metadata = {}
    kind = label = None
    for owner, next_kind, next_label, text in rows:
        if kind is not None and kind != next_kind:
            raise ValueError('Conflicting node kinds for ' + key)
        kind, label = next_kind, next_label
        for field, value in json.loads(text).items():
            if field in ('source_definition', 'compiler_definition'):
                metadata[field] = metadata.get(field, False) or value
            elif value is not None:
                metadata[field] = value
    if kind is None:
        return None
    return dict(id=key, kind=kind, label=label,
                metadata=json.dumps(metadata, sort_keys=True))


class NetChanges:
    def __init__(self):
        self.nodes = {}
        self.edges = {}

    def add(self, changes):
        for key, change in changes.changed_nodes.items():
            before = merged_support(key, change.before)
            after = merged_support(key, change.after)
            if key in self.nodes:
                before = self.nodes[key][0]
            self.nodes[key] = (before, after)
        for change in changes.changed_edges.values():
            # External identity remains exact; no digest is used as equality.
            key = (change.src, change.dst, change.kind, change.evidence)
            before, after = bool(change.before_owners), bool(change.after_owners)
            if key in self.edges:
                before = self.edges[key][0]
            self.edges[key] = (before, after)

    def add_merged(self, changes):
        """Consume opt-in summaries without retaining any owner populations."""
        for key, change in changes.changed_nodes.items():
            before = self.nodes[key][0] if key in self.nodes else change.before
            self.nodes[key] = (before, change.after)
        for change in changes.changed_edges.values():
            key = (change.src, change.dst, change.kind, change.evidence)
            before = self.edges[key][0] if key in self.edges else change.before_exists
            self.edges[key] = (before, change.after_exists)

    def plan(self):
        """Exact delta row count and logical payload, before DDL or inserts."""
        def size(value):
            return len(value.encode('utf-8'))
        changed_edges = [edge for edge, (before, after) in self.edges.items() if before != after]
        strings = {value for edge in changed_edges for value in edge}
        effective = [(key, after) for key, (before, after) in self.nodes.items() if before != after]
        rows = len(self.nodes) + len(effective) + len(strings) + len(changed_edges) + 1
        payload = (sum(size(key) for key in self.nodes)
                   + sum(sum(size(value) for value in after.values()) if after is not None else size(key)
                         for key, after in effective)
                   + sum(8 + size(value) for value in strings)
                   + 48 * len(changed_edges) + len('delta_storage_version') + 8)
        # This is publication output only, not every intermediate owner change.
        transfer = (sum(len(json.dumps(after if after is not None else {'id': key},
                                       sort_keys=True).encode('utf-8')) for key, after in effective)
                    + sum(len(json.dumps(edge).encode('utf-8')) for edge in changed_edges))
        return dict(rows=rows, payload_bytes=payload, graph_rows=len(effective) + len(changed_edges),
                    graph_payload_bytes=transfer)

    def planned_rows(self):
        return self.plan()['rows']

    def write(self, db):
        """Emit only actual effects using integer dictionary references.

        Read-only views retain the publisher's external row contract and stable
        journal cursors. prior_edges is an empty compatibility view, not a copy.
        The caller owns transaction/commit and the publication budget.
        """
        statements = '''
        CREATE TABLE delta_strings(id INTEGER PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE delta_edges(id INTEGER PRIMARY KEY,operation INTEGER NOT NULL,
          src INTEGER NOT NULL,dst INTEGER NOT NULL,kind INTEGER NOT NULL,evidence INTEGER NOT NULL);
        CREATE INDEX delta_edge_operations ON delta_edges(operation,id);
        CREATE TABLE settings(key TEXT PRIMARY KEY,value);
        CREATE TABLE changed_nodes(id TEXT PRIMARY KEY);
        CREATE TABLE nodes(id TEXT,kind TEXT,label TEXT,metadata TEXT);
        CREATE TABLE orphan_nodes(id TEXT);
        CREATE VIEW old_edges AS SELECT e.id AS rowid,s.value AS src,d.value AS dst,
          k.value AS kind,p.value AS evidence FROM delta_edges e
          JOIN delta_strings s ON s.id=e.src JOIN delta_strings d ON d.id=e.dst
          JOIN delta_strings k ON k.id=e.kind JOIN delta_strings p ON p.id=e.evidence
          WHERE e.operation=-1;
        CREATE VIEW new_edges AS SELECT e.id AS rowid,s.value AS src,d.value AS dst,
          k.value AS kind,p.value AS evidence FROM delta_edges e
          JOIN delta_strings s ON s.id=e.src JOIN delta_strings d ON d.id=e.dst
          JOIN delta_strings k ON k.id=e.kind JOIN delta_strings p ON p.id=e.evidence
          WHERE e.operation=1;
        CREATE VIEW prior_edges AS SELECT src,dst,kind,evidence FROM old_edges WHERE 0;
        '''
        for statement in statements.split(';'):
            if statement.strip():
                db.execute(statement)
        # Ownership changes remain visible to native-candidate validation even
        # when the merged graph property itself is unchanged.
        db.executemany('INSERT INTO changed_nodes VALUES(?)', ((key,) for key in sorted(self.nodes)))
        for key, (before, after) in sorted(self.nodes.items()):
            if before == after:
                continue
            if after is None:
                db.execute('INSERT INTO orphan_nodes VALUES(?)', (key,))
            else:
                db.execute('INSERT INTO nodes VALUES(:id,:kind,:label,:metadata)', after)
        cache = {}

        def intern(value):
            if value not in cache:
                cursor = db.execute('INSERT INTO delta_strings(value) VALUES(?)', (value,))
                cache[value] = cursor.lastrowid
            return cache[value]

        for edge, (before, after) in sorted(self.edges.items()):
            if before != after:
                db.execute('INSERT INTO delta_edges(operation,src,dst,kind,evidence) VALUES(?,?,?,?,?)',
                           (1 if after else -1, *(intern(value) for value in edge)))
        db.execute('INSERT INTO settings VALUES(?,?)', ('delta_storage_version', 2))
        return {name: db.execute('SELECT count(*) FROM ' + name).fetchone()[0]
                for name in ('nodes', 'old_edges', 'new_edges', 'orphan_nodes')}
