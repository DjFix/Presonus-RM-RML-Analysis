"""Offline budget enforcement, including SQLite's real opcode interrupt path."""
import sqlite3
import unittest
from publication_budget import (AccountingUnavailable, BudgetExceeded, BudgetLimits,
                                PublicationBudget)


class Counter:
    value = 0
    def __call__(self):
        return self.value


class BudgetTests(unittest.TestCase):
    def budget(self, **kwargs):
        counter = Counter()
        return PublicationBudget(io_reader=counter, **kwargs), counter

    def preflight(self, budget):
        budget.preflight(journal_estimate_bytes=0, sqlite_write_estimate_bytes=0,
                         rows=0, transfer_bytes=0)

    def test_routine_profile_accepts_measured_199_owner_update_and_stays_bounded(self):
        budget, _ = self.budget()
        budget.preflight(journal_estimate_bytes=1101382727,
                         sqlite_write_estimate_bytes=2010271744,
                         rows=4361506, transfer_bytes=301800000)
        with self.assertRaises(BudgetExceeded):
            budget.preflight(journal_estimate_bytes=3 * 1024**3 + 1,
                             sqlite_write_estimate_bytes=0, rows=0, transfer_bytes=0)

    def test_budget_rejects_before_any_write(self):
        budget, _ = self.budget(limits=BudgetLimits(rows=2))
        with self.assertRaises(BudgetExceeded):
            budget.preflight(journal_estimate_bytes=0, sqlite_write_estimate_bytes=0,
                             rows=3, transfer_bytes=0)
        self.assertEqual(budget.rows, 0)
        with self.assertRaises(BudgetExceeded):
            budget.charge_rows(1)

    def test_cumulative_rows_and_actual_utf8_transfer(self):
        budget, _ = self.budget(limits=BudgetLimits(rows=2, transfer_bytes=4))
        self.preflight(budget)
        budget.charge_rows(1)
        budget.charge_rows(1)
        self.assertEqual(budget.charge_transfer('é'), b'\xc3\xa9')
        self.assertEqual(budget.charge_transfer('ab'), b'ab')
        with self.assertRaises(BudgetExceeded):
            budget.charge_rows(1)
        self.assertEqual(budget.rows, 2)
        other, _ = self.budget(limits=BudgetLimits(transfer_bytes=1))
        self.preflight(other)
        with self.assertRaises(BudgetExceeded):
            other.charge_transfer('é')
        self.assertEqual(other.transfer_bytes, 0)

    def test_rebuild_is_explicit_and_finite(self):
        with self.assertRaises(ValueError):
            PublicationBudget(mode='full_rebuild', io_reader=lambda: 0)
        with self.assertRaises(ValueError):
            PublicationBudget(rebuild_limits=BudgetLimits(), io_reader=lambda: 0)
        with self.assertRaises(ValueError):
            BudgetLimits(rows=float('inf'))
        budget = PublicationBudget(mode='full_rebuild', rebuild_authorization='user:task-12',
                                   rebuild_limits=BudgetLimits(rows=200_000), io_reader=lambda: 0)
        budget.preflight(journal_estimate_bytes=1, sqlite_write_estimate_bytes=1,
                         rows=150_000, transfer_bytes=1)
        self.assertEqual(budget.receipt()['rebuild_authorization'], 'user:task-12')

    def test_absent_proc_is_honest_and_fails_closed(self):
        def absent():
            raise FileNotFoundError('/proc/self/io')
        with self.assertRaises(AccountingUnavailable):
            PublicationBudget(io_reader=absent)
        budget, _ = self.budget()
        self.preflight(budget)
        budget.io_reader = absent
        with self.assertRaises(AccountingUnavailable):
            budget.observe()
        self.assertIsNotNone(budget.receipt()['failure'])
        with self.assertRaises(BudgetExceeded):
            budget.charge_rows(1)

    def test_real_sqlite_progress_interrupt_rolls_back(self):
        budget, counter = self.budget(limits=BudgetLimits(sqlite_write_bytes=5))
        self.preflight(budget)
        connection = sqlite3.connect(':memory:')
        connection.execute('CREATE TABLE work(value)')
        with self.assertRaises(sqlite3.OperationalError):
            with budget.sqlite_progress_guard(connection, opcode_interval=1):
                connection.execute('INSERT INTO work VALUES(1)')
                counter.value = 6
                connection.execute('INSERT INTO work VALUES(2)')
        self.assertEqual(connection.execute('SELECT count(*) FROM work').fetchone()[0], 0)
        self.assertIn('sqlite_write_bytes budget exceeded', budget.receipt()['failure'])
        self.assertGreater(budget.progress_samples, 0)
        connection.close()

    def test_precommit_check_catches_io_between_opcodes(self):
        budget, counter = self.budget(limits=BudgetLimits(sqlite_write_bytes=5))
        self.preflight(budget)
        connection = sqlite3.connect(':memory:')
        connection.execute('CREATE TABLE work(value)')
        with self.assertRaises(BudgetExceeded):
            with budget.sqlite_progress_guard(connection, opcode_interval=1_000_000):
                connection.execute('INSERT INTO work VALUES(1)')
                counter.value = 6
        self.assertEqual(connection.execute('SELECT count(*) FROM work').fetchone()[0], 0)
        connection.close()

    def test_guard_does_not_commit_and_receipt_is_bounded(self):
        budget, _ = self.budget()
        self.preflight(budget)
        connection = sqlite3.connect(':memory:')
        connection.execute('CREATE TABLE work(value)')
        with budget.sqlite_progress_guard(connection):
            budget.charge_rows(1)
            connection.execute('INSERT INTO work VALUES(1)')
        self.assertTrue(connection.in_transaction)
        self.assertEqual(budget.precommit_checks, 1)
        connection.commit()
        budget.observe()
        receipt = budget.receipt()
        self.assertEqual(receipt['observed']['rows_charged'], 1)
        self.assertTrue(receipt['uncertainty'])
        self.assertEqual(receipt['limits'], dict(journal_bytes=3 * 1024**3,
                                                sqlite_write_bytes=12 * 1024**3,
                                                rows=30_000_000, transfer_bytes=3 * 1024**3))
        connection.close()

    def test_journal_actual_size_and_missing_file(self):
        from unittest.mock import patch, Mock
        budget, _ = self.budget(limits=BudgetLimits(journal_bytes=3))
        self.preflight(budget)
        with patch('publication_budget.Path.stat', return_value=Mock(st_size=4)):
            with self.assertRaises(BudgetExceeded):
                budget.observe(['journal.sqlite'])
        self.assertEqual(budget.receipt()['observed']['journal_high_water_logical_bytes'], 4)
        other, _ = self.budget()
        self.preflight(other)
        with patch('publication_budget.Path.stat', side_effect=FileNotFoundError):
            with self.assertRaises(AccountingUnavailable):
                other.observe(['missing.sqlite'])

    def test_io_counter_regression_is_not_zero_writes(self):
        budget, counter = self.budget()
        self.preflight(budget)
        counter.value = 10
        budget.observe()
        counter.value = 5
        with self.assertRaises(AccountingUnavailable):
            budget.observe()


if __name__ == '__main__':
    unittest.main()
