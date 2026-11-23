"""Bounded staging must preserve external effects and resume its own journal."""
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest

from batch_publication import publish
from bounded_net_changes import BoundedNetChanges
from compact_facts import CompactFacts, PruneCandidates, create_schema
from context_runtime import ContextError, sha
from incremental_delta import NetChanges
from publication_budget import PublicationBudget
from publication_events import require_verified

ROWS = {
    'changed_nodes': ('id',),
    'nodes': ('id', 'kind', 'label', 'metadata'),
    'old_edges': ('src', 'dst', 'kind', 'evidence'),
    'new_edges': ('src', 'dst', 'kind', 'evidence'),
    'orphan_nodes': ('id',),
}


def rows(db):
    return {name: list(db.execute(f'SELECT rowid,{",".join(columns)} FROM {name} ORDER BY rowid'))
            for name, columns in ROWS.items()}


def node(label, **metadata):
    return dict(kind='Function', label=label, metadata=metadata)


def build_journal(path, bounded, seed, updates):
    """Use the maintained compact stores and persisted SQLite delta layout."""
    with closing(sqlite3.connect(path.with_name(path.stem + '-facts.sqlite'))) as source, \
            closing(sqlite3.connect(path)) as delta:
        source.execute('PRAGMA journal_mode=WAL')
        create_schema(source)
        store = CompactFacts(source)
        for owner, nodes, edges in seed:
            store.replace_owner(owner, nodes, edges)
        source.commit()
        source.execute('BEGIN IMMEDIATE')
        delta.execute('BEGIN')
        touched = PruneCandidates()
        net = BoundedNetChanges(source, touched) if bounded else NetChanges()
        try:
            for owner, nodes, edges in updates:
                change = store.replace_owner(owner, nodes, edges,
                                             merged='touched' if bounded else True,
                                             savepoint=False)
                (touched.add if bounded else net.add_merged)(change)
            plan = net.plan()
            counts = net.write(delta)
            observed = rows(delta)
            delta.execute('INSERT INTO settings VALUES(?,?)', ('replace_legacy_build', 0))
        finally:
            if bounded:
                net.close()
        source.commit()
        delta.commit()
    return plan, counts, observed


class Result(list):
    def single(self):
        return self[0] if self else None

    def consume(self):
        pass


class EdgeBackend:
    """Offline transactional relationship store for the publisher contract."""
    def __init__(self, edges):
        self.edges = set(edges)
        self.checkpoint = None
        self.cursor = None
        self.mutations = []

    def run(self, query, **params):
        selected = params.get('rows', [])
        if 'p.digest AS digest' in query:
            return Result([self.cursor] if params['id'] == self.checkpoint else [])
        if 'properties(p) AS p' in query:
            return Result([dict(checkpoint=self.checkpoint, p=self.cursor)])
        if 'SET g.state="refreshing"' in query:
            self.checkpoint = params['id']
            return Result([{'n': 1}])
        if 'CREATE(p:PublicationCheckpoint' in query:
            self.cursor = dict(digest=params['digest'], batch_size=params['size'],
                               contract_version=1, phase=0, last_row=0, commits=0,
                               verified_commits=0, event_phase=None, event_start=0, event_end=0)
            return Result()
        if 'g.publication_checkpoint AS checkpoint' in query:
            return Result([dict(checkpoint=self.checkpoint)])
        if 'p.contract_version AS version' in query:
            fields = dict(version='contract_version', commits='commits', verified='verified_commits',
                          phase='event_phase', start='event_start', end='event_end')
            return Result([{key: self.cursor[value] for key, value in fields.items()}])
        if 'p.phase AS phase' in query:
            return Result([self.cursor])
        if 'SET p.verified_commits=$commit' in query:
            assert self.cursor['commits'] == params['commit']
            assert self.cursor['verified_commits'] == params['previous']
            self.cursor['verified_commits'] = params['commit']
            return Result([{'n': 1}])
        if 'SET p.phase=$next_phase' in query:
            assert (self.cursor['phase'], self.cursor['last_row']) == (params['phase'], params['last'])
            assert self.cursor['verified_commits'] == self.cursor['commits']
            self.cursor.update(phase=params['next_phase'], last_row=params['next_row'],
                               commits=self.cursor['commits'] + 1, event_phase=params['event_phase'],
                               event_start=params['last'], event_end=params['event_end'])
            return Result([{'n': 1}])
        if 'count(r) AS n' in query:
            return Result([dict(journal_row=row['journal_row'], n=int(self.edge(row) in self.edges))
                           for row in selected])
        if 'DELETE r' in query or 'MERGE(s)-[:' in query:
            remove = 'DELETE r' in query
            for row in selected:
                edge = self.edge(row)
                (self.edges.remove if remove else self.edges.add)(edge)
                self.mutations.append(('old_edges' if remove else 'new_edges', row['journal_row']))
            return Result([{'n': len(selected)}])
        raise AssertionError(query)

    @staticmethod
    def edge(row):
        return tuple(row[name] for name in ROWS['new_edges'])

    def begin_transaction(self):
        return self

    def __enter__(self):
        self.before = (self.edges.copy(), self.checkpoint,
                       None if self.cursor is None else self.cursor.copy(), len(self.mutations))
        return self

    def __exit__(self, *_error):
        if self.before is not None:
            self.edges, self.checkpoint, self.cursor, count = self.before
            del self.mutations[count:]

    def commit(self):
        self.before = None


class BoundedNetTests(unittest.TestCase):
    def setUp(self):
        scratch = Path.cwd() / 'temp' / 'test-work'
        scratch.mkdir(parents=True, exist_ok=True)
        self.directory = Path(self.enterContext(tempfile.TemporaryDirectory(dir=scratch)))

    def test_shared_support_and_or_merge_match_legacy_after_reordering(self):
        original = ('z', 'shared', 'CALLS', 'old')
        replaced = ('z', 'shared', 'CALLS', 'new')
        transfer = ('a', 'shared', 'CALLS', 'transfer')
        retained = ('shared', 'z', 'CALLS', 'retained')
        seed = [
            ('z', {'z': node('remove'), 'shared': node('winning', val='z', compiler_definition=False)},
             [original, retained]),
            ('a', {'shared': node('peer', val='a', source_definition=True)},
             [transfer, retained]),
        ]
        updates = [
            ('z', {'shared': node('new winner', val=None, compiler_definition=False)},
             [replaced, retained, transfer]),
            ('a', {'shared': node('update', val='a', source_definition=False, compiler_definition=True)}, []),
        ]
        normalize = lambda items: {tab: sorted(row[1:] for row in vals) for tab, vals in items.items()}
        for order, changes in enumerate((updates, list(reversed(updates)))):
            with self.subTest(order=order):
                old_plan, old_count, old = build_journal(self.directory / f'old-{order}.sqlite', False, seed, changes)
                new_plan, new_count, new = build_journal(self.directory / f'new-{order}.sqlite', True, seed, changes)
                self.assertEqual(normalize(new), normalize(old))
                self.assertEqual(new_count, old_count)
                for field in ('rows', 'payload_bytes', 'graph_rows'):
                    self.assertEqual(new_plan[field], old_plan[field])
                outcome = normalize(new)
                self.assertEqual(outcome['old_edges'], [original])
                self.assertEqual(outcome['new_edges'], [replaced])
                self.assertEqual(outcome['orphan_nodes'], [('z',)])
                self.assertEqual(outcome['nodes'], [
                    ('shared', 'Function', 'new winner',
                     '{"compiler_definition": true, "source_definition": false, "val": "a"}'),
                ])

    def test_generated_journal_resumes_its_exact_cursor_and_rejects_another_digest(self):
        removed = ('z', 'a', 'CALLS', 'old')
        added = ('a', 'z', 'CALLS', 'new')
        seed = [('owner', {}, [removed])]
        updates = [('owner', {}, [added])]
        journal, other = (self.directory / file for file in ('bounded.sqlite', 'legacy.sqlite'))
        _, _, events = build_journal(journal, True, seed, updates)
        build_journal(other, False, seed, updates)
        digest = sha(journal)
        self.assertNotEqual(digest, sha(other))
        server = EdgeBackend([removed])
        with closing(sqlite3.connect(journal.as_uri() + '?mode=ro', uri=True)) as db, \
                closing(sqlite3.connect(other.as_uri() + '?mode=ro', uri=True)) as wrong:
            db.row_factory = wrong.row_factory = sqlite3.Row
            log = self.directory / 'publication.jsonl'
            budget = lambda: PublicationBudget(io_reader=lambda: 0)
            with self.assertRaisesRegex(ContextError, 'Injected interruption'):
                publish(server, db, journal, log, batch_size=1, stop_after=2, budget=budget())
            cursor = server.cursor.copy()
            proposed = dict(checkpoint='source-delta:' + digest, delta_sha256=digest, batch_size=1,
                            verification_contract=1, verification_state='verified')
            with self.assertRaisesRegex(ContextError, 'Unverified publication'):
                require_verified(server, proposed, journal)
            with self.assertRaisesRegex(ContextError, 'Different journal cannot supersede'):
                publish(server, wrong, other, log, batch_size=1, budget=budget())
            self.assertEqual(server.cursor, cursor)
            receipt = publish(server, db, journal, log, batch_size=1, budget=budget())
            require_verified(server, receipt, journal)
        self.assertEqual(receipt, proposed)
        self.assertEqual(sha(journal), digest)
        self.assertEqual(server.edges, {added})
        self.assertEqual(server.mutations, [(phase, row[0]) for phase in ('old_edges', 'new_edges')
                                            for row in events[phase]])


if __name__ == '__main__':
    unittest.main()
