"""Shared-owner cost accounting charges only changed storage and merged output."""
import json
import sqlite3
import unittest

from incremental_delta import merged_support
from publication_budget import BudgetExceeded
from test_incremental_stage import StageTests, node


class OwnerCostTests(StageTests):
    def test_many_wide_owners_do_not_multiply_one_owner_change(self):
        wide = {'kind': 'Function', 'label': 'same',
                'metadata': {'wide': 'x' * 4096, 'source_definition': False}}
        for i in range(80):
            self.store.replace_owner('owner-%03d' % i, {'shared': wide}, [])
        changed = dict(wide, metadata=dict(wide['metadata'], source_definition=True))
        stage = self.stage(rows=40, journal_bytes=200_000, sqlite_write_bytes=500_000)
        before_rows = self.c.total_changes
        stage.replace_facts('owner-000', {'shared': changed}, [])
        self.assertEqual(self.c.total_changes - before_rows, 2)
        self.assertLess(stage.receipt()['totals']['encoded_changed_bytes'], 20_000)
        self.assertTrue(json.loads(stage.net.nodes['shared'][1]['metadata'])['source_definition'])
        self.assertEqual(stage.finish(self.delta)['nodes'], 1)
        self.assertEqual(self.c.execute('SELECT count(*) FROM node_facts').fetchone()[0], 80)
        self.assertEqual(self.c.execute('SELECT count(*) FROM compact_node_values').fetchone()[0], 2)

    def test_shadowed_fields_and_boolean_union_match_real_delta_merge(self):
        def value(label, **metadata):
            return dict(kind='Function', label=label, metadata=metadata)
        self.store.replace_owner('a', {'n': value('first', choice='first', nullable=4,
                                               source_definition=True)}, [])
        self.store.replace_owner('z', {'n': value('last', choice='last', nullable=None,
                                               compiler_definition=True)}, [])
        before = [tuple(r) for r in self.c.execute(
            'SELECT owner,kind,label,metadata FROM node_facts WHERE id=? ORDER BY owner', ('n',))]
        changed = value('shadowed', choice='changed', nullable=5, source_definition=False)
        stage = self.stage()
        stage.replace_facts('a', {'n': changed}, [])
        after = [tuple(r) for r in self.c.execute(
            'SELECT owner,kind,label,metadata FROM node_facts WHERE id=? ORDER BY owner', ('n',))]
        self.assertEqual(stage.net.nodes['n'], (merged_support('n', before), merged_support('n', after)))
        actual = stage.net.nodes['n'][1]
        self.assertEqual(actual['label'], 'last')
        self.assertEqual(json.loads(actual['metadata']), dict(choice='last', nullable=5,
                                                            source_definition=False, compiler_definition=True))
        self.assertEqual(stage.finish(self.delta)['nodes'], 1)
        self.assertEqual(self.delta.execute('SELECT metadata FROM nodes').fetchone()[0], actual['metadata'])

    def test_completely_shadowed_change_has_storage_cost_but_no_graph_update(self):
        self.store.replace_owner('a', {'n': node('first')}, [])
        self.store.replace_owner('z', {'n': node('winner')}, [])
        stage = self.stage()
        stage.replace_facts('a', {'n': node('still-shadowed')}, [])
        self.assertEqual(stage.receipt()['totals']['changed_nodes'], 1)
        self.assertGreater(stage.receipt()['totals']['encoded_changed_bytes'], 0)
        self.assertEqual(stage.finish(self.delta)['nodes'], 0)

    def test_kind_conflict_still_precedes_mutation(self):
        self.store.replace_owner('a', {'n': node()}, [])
        self.store.replace_owner('b', {'n': node()}, [])
        before = self.c.total_changes
        stage = self.stage()
        with self.assertRaisesRegex(ValueError, 'Conflicting node kinds'):
            stage.replace_facts('a', {'n': dict(node(), kind='Other')}, [])
        self.assertEqual(self.c.total_changes, before)
        self.assertEqual(stage.receipt()['totals']['rows'], 0)

    def test_rejected_owner_receipt_includes_projected_cost_before_write(self):
        stage = self.stage(journal_bytes=1)
        before = self.c.total_changes
        with self.assertRaises(BudgetExceeded):
            stage.replace_facts('rejected-owner', {'n': node('wide')}, [])
        receipt = stage.receipt()
        rejected = receipt['rejected_owner']
        self.assertEqual(self.c.total_changes, before)
        self.assertEqual(rejected['owner'], 'rejected-owner')
        self.assertFalse(rejected['mutation_started'])
        self.assertEqual(rejected['previous_totals']['rows'], 0)
        self.assertEqual(rejected['projected_totals']['rows'], 5)
        self.assertGreater(rejected['preflight']['journal_estimate_bytes'], 1)
        self.assertIn('rejected-owner', stage.budget.receipt()['failure'])
        self.assertEqual(receipt['owners'], [])

    def test_actual_unique_edge_rows_are_bounded_and_fully_counted(self):
        edges = [('src%d' % i, 'dst%d' % i, 'CALL%d' % i,
                  json.dumps(dict(path='p%d' % i, tu='t%d' % i,
                                  context='c%d' % i, source='s%d' % i)))
                 for i in range(100)]
        stage = self.stage()
        start_storage, start_delta = self.c.total_changes, self.delta.total_changes
        stage.replace_facts('a', {}, edges)
        self.assertEqual(stage.finish(self.delta)['new_edges'], 100)
        receipt = stage.receipt()
        actual = receipt['actual_mutation_rows']
        self.assertEqual(actual['storage'] + actual['prune'], self.c.total_changes - start_storage)
        self.assertEqual(actual['delta'], self.delta.total_changes - start_delta)
        self.assertEqual(actual['storage'], 1101)
        self.assertEqual(actual['delta'], 501)
        self.assertGreaterEqual(receipt['totals']['rows'], sum(actual.values()))
        # Removing the same unique edge population also accounts touched pruning.
        second = self.stage()
        delta2 = sqlite3.connect(':memory:')
        self.addCleanup(delta2.close)
        delta2.execute('BEGIN')
        second.remove_owner('a')
        second.finish(delta2)
        self.assertGreater(second.receipt()['actual_mutation_rows']['prune'], 0)
        self.assertGreaterEqual(second.receipt()['totals']['rows'],
                                sum(second.receipt()['actual_mutation_rows'].values()))


if __name__ == '__main__':
    unittest.main()
