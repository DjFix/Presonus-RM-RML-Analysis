import json
import sqlite3
import unittest

from compact_facts import CompactFacts, create_schema
from incremental_delta import NetChanges


class IncrementalDeltaTests(unittest.TestCase):
    def setUp(self):
        self.source = sqlite3.connect(':memory:')
        create_schema(self.source)
        self.store = CompactFacts(self.source)
        self.nodes = {'f': dict(kind='Function', label='f', metadata={'source_definition': True})}
        self.edge = ('f', 'g', 'CALLS', '{"path":"shared.hpp","line":7}')
        self.delta = sqlite3.connect(':memory:')

    def tearDown(self):
        self.source.close()
        self.delta.close()

    def test_unchanged_owner_has_no_effects_or_fact_writes(self):
        self.store.replace_owner('a', self.nodes, [self.edge])
        before = self.source.total_changes
        net = NetChanges()
        net.add(self.store.replace_owner('a', self.nodes, [self.edge]))
        self.assertEqual(self.source.total_changes, before)
        self.assertEqual(set(net.write(self.delta).values()), {0})

    def test_shared_owner_removal_keeps_edge_until_last_support_disappears(self):
        self.store.replace_owner('a', self.nodes, [self.edge])
        self.store.replace_owner('b', self.nodes, [self.edge])
        net = NetChanges()
        net.add(self.store.replace_owner('a', {}, []))
        self.assertEqual(net.write(self.delta)['old_edges'], 0)
        second = sqlite3.connect(':memory:')
        try:
            net = NetChanges()
            net.add(self.store.replace_owner('b', {}, []))
            self.assertEqual(net.write(second)['old_edges'], 1)
            self.assertEqual(second.execute('SELECT src,dst,kind,evidence FROM old_edges').fetchone(), self.edge)
        finally:
            second.close()

    def test_owner_transfer_does_not_retract_and_reinsert_unchanged_edge(self):
        self.store.replace_owner('a', self.nodes, [self.edge])
        net = NetChanges()
        net.add(self.store.replace_owner('a', {}, []))
        net.add(self.store.replace_owner('b', self.nodes, [self.edge]))
        self.assertEqual(set(net.write(self.delta).values()), {0})

    def test_evidence_change_emits_only_one_removal_and_addition_with_cursors(self):
        self.store.replace_owner('a', self.nodes, [self.edge])
        changed = (*self.edge[:3], '{"path":"shared.hpp","line":8}')
        net = NetChanges()
        net.add(self.store.replace_owner('a', self.nodes, [changed]))
        counts = net.write(self.delta)
        self.assertEqual(counts, dict(nodes=0, old_edges=1, new_edges=1, orphan_nodes=0))
        self.delta.row_factory = sqlite3.Row
        for phase in ('old_edges', 'new_edges'):
            row = self.delta.execute('SELECT rowid AS journal_row,* FROM ' + phase +
                                     ' WHERE rowid>? ORDER BY rowid LIMIT 1', (0,)).fetchone()
            self.assertGreater(row['journal_row'], 0)
            self.assertIsNone(self.delta.execute('SELECT rowid FROM ' + phase + ' WHERE rowid>?',
                                                (row['journal_row'],)).fetchone())
        self.assertEqual(self.delta.execute('SELECT count(*) FROM prior_edges').fetchone()[0], 0)
        self.assertEqual(self.delta.execute("SELECT type FROM sqlite_master WHERE name='prior_edges'").fetchone()[0], 'view')
        self.assertEqual(self.delta.execute('SELECT count(*) FROM delta_edges').fetchone()[0], 2)

    def test_last_definition_demotion_preserves_other_owner_metadata(self):
        self.store.replace_owner('a', self.nodes, [])
        weak = {'f': dict(kind='Function', label='last owner', metadata={'source_definition': False, 'value': 42})}
        self.store.replace_owner('z', weak, [])
        net = NetChanges()
        net.add(self.store.replace_owner('a', {}, []))
        self.assertEqual(net.write(self.delta)['nodes'], 1)
        row = self.delta.execute('SELECT label,metadata FROM nodes').fetchone()
        self.assertEqual(row[0], 'last owner')
        self.assertEqual(json.loads(row[1]), {'source_definition': False, 'value': 42})


if __name__ == '__main__':
    unittest.main()
