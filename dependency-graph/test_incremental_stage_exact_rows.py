"""Exact mutation plans must precede writes and match real SQLite row changes."""
import json
import sqlite3
import unittest
from unittest.mock import patch

from publication_budget import BudgetExceeded
from test_incremental_stage import StageTests, node


class ExactRowTests(StageTests):
    def test_new_owner_reuses_wide_values_and_existing_provenance(self):
        nodes = {str(i): dict(kind='Function', label='same', metadata={'wide': 'x' * 4096})
                 for i in range(100)}
        edges = [(str(i), str(i), 'CALLS', '{"path":"shared","tu":"shared"}') for i in range(100)]
        self.store.replace_owner('first', nodes, edges)
        before = self.c.total_changes
        stage = self.stage()
        stage.replace_facts('second', nodes, edges)
        cost = stage.costs[0]
        self.assertEqual(cost['rows'], 201)  # owner plus 200 memberships
        self.assertEqual(cost['rows'], self.c.total_changes - before)
        self.assertNotIn('compact_node_values', cost['storage_row_plan']['tables'])
        self.assertNotIn('compact_provenance', cost['storage_row_plan']['tables'])
        self.assertLess(cost['encoded_changed_bytes'], 5000)
        counts = stage.finish(self.delta)
        self.assertEqual(counts['nodes'], 0)
        self.assertEqual(counts['new_edges'], 0)
        receipt = stage.receipt()
        self.assertEqual(receipt['totals']['rows'], sum(receipt['actual_mutation_rows'].values()))

    def test_new_interning_plan_is_readonly_and_deduplicates_payloads(self):
        nodes = {'a': node(), 'b': node()}
        edges = [('a', 'b', 'CALLS', json.dumps({'location': {'file': 'same'}, 'tu': 'same'})),
                 ('b', 'a', 'CALLS', json.dumps({'location': {'file': 'same'}, 'tu': 'same'}))]
        before = self.c.total_changes
        plan = self.store.plan_owner_rows('new', nodes, edges, nodes, edges)
        self.assertEqual(self.c.total_changes, before)
        self.assertEqual(plan['tables']['compact_node_values'], 1)
        self.assertEqual(plan['tables']['compact_provenance'], 1)
        self.assertEqual(plan['tables']['compact_atoms'], 1)
        self.store.replace_owner('new', nodes, edges)
        self.assertEqual(plan['rows'], self.c.total_changes - before)

    def test_exact_plan_matches_replacements_removals_and_raw_evidence(self):
        stage = self.stage()
        for i in range(24):
            owner = 'owner%d' % (i % 4)
            nodes = {str(j): dict(kind='Function', label='l%d' % (i % 3),
                                 metadata={'v': j % 2, 'source_definition': bool(i % 2)})
                     for j in range(i % 5)}
            evidence = ['not-json', '[]', '{"path":3}', '{"location":{"file":"p"},"source":"s"}'][i % 4]
            edges = [(str(j), str(j + 1), 'CALLS', evidence) for j in range(i % 3)]
            before = self.c.total_changes
            stage.replace_facts(owner, nodes, edges)
            self.assertEqual(stage.costs[-1]['rows'], self.c.total_changes - before)
        stage.finish(self.delta)
        receipt = stage.receipt()
        self.assertEqual(receipt['totals']['rows'], sum(receipt['actual_mutation_rows'].values()))

    def test_unexpected_trigger_rows_abort_the_transaction(self):
        self.c.commit()
        self.c.executescript('CREATE TABLE audit(x); CREATE TRIGGER unexpected AFTER INSERT ON compact_node_memberships BEGIN INSERT INTO audit VALUES(1); END;')
        self.c.execute('BEGIN')
        stage = self.stage()
        with self.assertRaisesRegex(ValueError, 'Storage row plan changed'):
            stage.replace_facts('a', {'n': node()}, [])
        self.assertFalse(self.c.in_transaction)
        self.assertEqual(self.c.execute('SELECT count(*) FROM node_facts').fetchone()[0], 0)
        self.assertEqual(self.c.execute('SELECT count(*) FROM audit').fetchone()[0], 0)

    def test_delta_limit_precedes_ddl_and_delta_rows(self):
        stage = self.stage(rows=7)
        stage.replace_facts('a', {'n': node()}, [])  # five exact rows
        with self.assertRaises(BudgetExceeded):
            stage.finish(self.delta)  # touched node, published node, setting
        self.assertEqual(self.delta.execute("SELECT count(*) FROM sqlite_master WHERE name='nodes'").fetchone()[0], 0)
        self.assertEqual(stage.receipt()['rejected_owner']['owner'], '@delta-schema')

    def test_prune_limit_is_checked_before_deletion_and_rolls_back_both(self):
        self.store.replace_owner('a', {'n': node()}, [])
        self.c.commit()
        self.c.execute('BEGIN')
        stage = self.stage(rows=5)
        stage.replace_facts('a', {'n': node('changed')}, [])  # value + membership
        with self.assertRaises(BudgetExceeded):
            stage.finish(self.delta)  # delta three rows, old value deletion is sixth
        self.assertEqual(self.c.execute('SELECT label FROM node_facts').fetchone()[0], 'same')
        self.assertFalse(self.c.in_transaction)
        self.assertFalse(self.delta.in_transaction)
        self.assertEqual(self.delta.execute("SELECT count(*) FROM sqlite_master WHERE name='nodes'").fetchone()[0], 0)
        self.assertEqual(stage.receipt()['rejected_owner']['owner'], '@prune:compact_node_values')


if __name__ == '__main__':
    unittest.main()
