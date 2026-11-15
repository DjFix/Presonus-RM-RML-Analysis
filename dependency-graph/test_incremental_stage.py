"""Bounded in-memory staging tests; never open the operational index."""
import sqlite3
import unittest
from unittest.mock import patch
from compact_facts import create_schema, CompactFacts
from incremental_stage import IncrementalStage
from publication_budget import PublicationBudget, BudgetLimits, BudgetExceeded


def node(label='same'):
    return {'kind': 'Function', 'label': label, 'metadata': {}}


class StageTests(unittest.TestCase):
    def setUp(self):
        self.c = sqlite3.connect(':memory:')
        self.c.row_factory = sqlite3.Row
        create_schema(self.c)
        self.c.execute('CREATE TABLE unit_observations(owner TEXT PRIMARY KEY,observation_id TEXT,payload TEXT)')
        self.c.commit()
        self.c.execute('BEGIN')
        self.delta = sqlite3.connect(':memory:')
        self.delta.execute('BEGIN')
        self.store = CompactFacts(self.c)

    def tearDown(self):
        self.c.close()
        self.delta.close()

    def stage(self, **limits):
        return IncrementalStage(self.c, PublicationBudget(BudgetLimits(**limits), io_reader=lambda: 0))

    def test_noop_has_no_fact_cost_or_delta(self):
        self.store.replace_owner('a', {'n': node()}, [('n', 'n', 'CALLS', 'raw')])
        stage = self.stage()
        before = self.c.total_changes
        stage.replace_facts('a', {'n': node()}, [('n', 'n', 'CALLS', 'raw')])
        self.assertEqual(self.c.total_changes, before)
        self.assertEqual(stage.receipt()['totals']['rows'], 0)
        counts = stage.finish(self.delta)
        self.assertEqual(set(counts.values()), {0})
        self.assertTrue(self.c.in_transaction)
        self.assertTrue(self.delta.in_transaction)

    def test_shared_edge_last_owner_and_touched_pruning(self):
        edge = ('n', 'n', 'CALLS', 'raw')
        for owner in ('a', 'b'):
            self.store.replace_owner(owner, {'n': node()}, [edge])
        stage = self.stage()
        stage.remove_owner('a')
        self.assertEqual(stage.net.edges[edge], (True, True))
        stage.remove_owner('b')
        self.assertEqual(stage.net.edges[edge], (True, False))
        counts = stage.finish(self.delta)
        self.assertEqual(counts['old_edges'], 1)
        self.assertEqual(counts['orphan_nodes'], 1)
        self.assertEqual(self.c.execute('SELECT count(*) FROM compact_edge_observations').fetchone()[0], 0)

    def test_budget_overflow_precedes_owner_mutation(self):
        self.store.replace_owner('a', {'n': node()}, [])
        before = self.c.total_changes
        stage = self.stage(rows=1)
        with self.assertRaises(BudgetExceeded):
            stage.replace_facts('a', {'n': node('changed')}, [])
        self.assertEqual(self.c.total_changes, before)
        self.assertEqual(self.c.execute('SELECT label FROM node_facts').fetchone()[0], 'same')

    def test_caller_rolls_back_earlier_owner_on_later_failure(self):
        self.store.replace_owner('a', {'n': node()}, [])
        self.c.commit()
        self.c.execute('BEGIN')
        stage = self.stage(rows=4)
        stage.replace_facts('a', {'n': node('changed')}, [])
        with self.assertRaises(BudgetExceeded):
            stage.replace_facts('b', {'m': node()}, [])
        self.c.rollback()
        self.assertEqual(self.c.execute('SELECT label FROM node_facts').fetchone()[0], 'same')
        self.assertEqual(self.c.execute('SELECT count(*) FROM node_facts').fetchone()[0], 1)

    def test_small_change_does_not_charge_unchanged_population(self):
        nodes = {str(i): node() for i in range(500)}
        self.store.replace_owner('a', nodes, [])
        nodes['1'] = node('changed')
        stage = self.stage(rows=40, journal_bytes=100_000, sqlite_write_bytes=200_000)
        stage.replace_facts('a', nodes, [])
        self.assertEqual(stage.receipt()['totals']['changed_nodes'], 1)
        self.assertEqual(stage.finish(self.delta)['nodes'], 1)

    def test_unit_payload_only_update_and_removed_owner(self):
        stage = self.stage()
        with patch('incremental_stage.sha', return_value='hash'):
            stage.replace_unit('a', {}, {}, [], {}, 'ast', 'gcc')
            stage.replace_unit('a', {}, {}, [], {}, 'ast', 'gcc')
            stage.replace_unit('a', {'changed': True}, {}, [], {}, 'ast', 'gcc')
        self.assertEqual(stage.receipt()['totals']['observation_updates'], 2)
        self.assertEqual(stage.costs[1]['rows'], 0)
        stage.remove_owner('a')
        self.assertEqual(self.c.execute('SELECT count(*) FROM unit_observations').fetchone()[0], 0)
        self.assertEqual(stage.receipt()['totals']['observation_updates'], 3)

    def test_observation_overflow_precedes_any_fact_write(self):
        stage = self.stage(sqlite_write_bytes=1)
        before = self.c.total_changes
        with patch('incremental_stage.sha', return_value='hash'):
            with self.assertRaises(BudgetExceeded):
                stage.replace_unit('a', {}, {}, [], {}, 'ast', 'gcc')
        self.assertEqual(self.c.total_changes, before)

    def test_special_owners_and_caller_transaction_requirement(self):
        stage = self.stage()
        stage.replace_facts('@catalog', {'catalog': node()}, [])
        stage.replace_facts('@build', {'build': node()}, [])
        self.assertEqual(stage.finish(self.delta)['nodes'], 2)
        with self.assertRaises(RuntimeError):
            stage.remove_owner('@build')
        self.c.rollback()
        with self.assertRaisesRegex(RuntimeError, 'BEGIN'):
            self.stage().replace_facts('a', {}, [])


if __name__ == '__main__':
    unittest.main()
