"""Staging opts out of redundant owner subjournals, retaining outer rollback."""
import sqlite3
import unittest

from compact_facts import CompactFacts, create_schema
from test_incremental_stage import StageTests, node


class StageOwnerSavepointTests(StageTests):
    def test_staging_has_no_owner_savepoints_and_exact_rows(self):
        statements = []
        self.c.set_trace_callback(statements.append)
        stage = self.stage()
        stage.replace_facts('a', {'n': node()}, [('n', 'n', 'CALLS', 'raw')])
        stage.replace_facts('b', {'n': node()}, [('n', 'n', 'CALLS', 'raw')])
        stage.finish(self.delta)
        self.assertFalse(any('SAVEPOINT' in query.upper() for query in statements))
        receipt = stage.receipt()
        self.assertEqual(receipt['totals']['rows'], sum(receipt['actual_mutation_rows'].values()))
        self.assertTrue(self.c.in_transaction)
        self.assertTrue(self.delta.in_transaction)

    def test_optout_requires_existing_outer_transaction(self):
        self.c.rollback()
        before = self.c.total_changes
        with self.assertRaisesRegex(ValueError, 'requires an active outer'):
            self.store.replace_owner('a', {'n': node()}, [], savepoint=False)
        self.assertFalse(self.c.in_transaction)
        self.assertEqual(self.c.total_changes, before)

    def test_optout_error_rolls_back_prior_owner_and_partial_interns(self):
        self.store.replace_owner('baseline', {'n': node()}, [])
        self.c.commit()
        original = tuple(self.c.iterdump())
        self.c.execute('BEGIN')
        self.store.replace_owner('earlier', {'other': node()}, [], savepoint=False)
        with self.assertRaisesRegex(ValueError, 'Conflicting node kinds'):
            self.store.replace_owner('broken', {'n': dict(node(), kind='Wrong')}, [], savepoint=False)
        self.assertFalse(self.c.in_transaction)
        self.assertEqual(tuple(self.c.iterdump()), original)

    def test_default_keeps_owner_atomicity_and_prior_transaction_work(self):
        self.store.replace_owner('baseline', {'n': node()}, [])
        self.store.replace_owner('earlier', {'other': node()}, [])
        with self.assertRaisesRegex(ValueError, 'Conflicting node kinds'):
            self.store.replace_owner('broken', {'n': dict(node(), kind='Wrong')}, [])
        self.assertTrue(self.c.in_transaction)
        self.assertEqual(self.c.execute('SELECT count(*) FROM node_facts').fetchone()[0], 2)
        self.assertEqual(self.c.execute('SELECT count(*) FROM compact_kinds WHERE value="Wrong"').fetchone()[0], 0)


if __name__ == '__main__':
    unittest.main()
