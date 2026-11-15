"""Explicit SQLite sidecar lifecycle; missing ordinary paths stay fail-closed."""
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from publication_budget import AccountingUnavailable, BudgetExceeded, BudgetLimits, PublicationBudget


class SQLiteSidecarTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[1] / 'temp/test-work'
        root.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix='sidecar-budget-', dir=root)
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.database = self.root / 'main.sqlite'
        self.database.write_bytes(b'db')

    def budget(self, **limits):
        budget = PublicationBudget(limits=BudgetLimits(**limits), io_reader=lambda: 0)
        budget.preflight(journal_estimate_bytes=0, sqlite_write_estimate_bytes=0, rows=0, transfer_bytes=0)
        return budget

    def test_absent_then_appearing_then_deleted_journal_keeps_highwater(self):
        budget = self.budget()
        journal = Path(str(self.database) + '-journal')
        wal = Path(str(self.database) + '-wal')
        budget.observe(sqlite_paths=[self.database])
        self.assertEqual(budget.receipt()['observed']['journal_high_water_logical_bytes'], 0)
        journal.write_bytes(b'x' * 31)
        wal.write_bytes(b'y' * 47)
        budget.observe(sqlite_paths=[self.database])
        self.assertEqual(budget.receipt()['observed']['journal_high_water_logical_bytes'], 78)
        journal.unlink()
        wal.unlink()
        budget.observe(sqlite_paths=[self.database])
        self.assertEqual(budget.receipt()['observed']['journal_high_water_logical_bytes'], 78)
        self.assertEqual(budget.receipt()['sqlite_sidecar_databases'], [str(self.database)])
        journal.write_bytes(b'x' * 4)
        budget.observe(sqlite_paths=[self.database])
        self.assertEqual(budget.receipt()['observed']['journal_high_water_logical_bytes'], 78)

    def test_preexisting_sidecars_and_delta_database_sum_before_work(self):
        delta = self.root / 'delta.sqlite'
        delta.write_bytes(b'd' * 11)
        Path(str(self.database) + '-journal').write_bytes(b'j' * 13)
        Path(str(delta) + '-wal').write_bytes(b'w' * 17)
        budget = self.budget(journal_bytes=40)
        with self.assertRaises(BudgetExceeded):
            budget.observe([delta], sqlite_paths=[self.database, delta])
        self.assertEqual(budget.receipt()['observed']['journal_high_water_logical_bytes'], 41)

    def test_only_explicit_sidecars_allow_absence(self):
        budget = self.budget()
        with self.assertRaises(AccountingUnavailable):
            budget.observe([Path(str(self.database) + '-journal')])
        other = self.budget()
        self.database.unlink()
        with self.assertRaisesRegex(AccountingUnavailable, 'SQLite database accounting unavailable'):
            other.observe(sqlite_paths=[self.database])

    def test_sidecar_permission_error_is_not_zero_bytes(self):
        budget = self.budget()
        original = Path.stat
        def fail(path, *args, **kwargs):
            if str(path).endswith('-wal'):
                raise PermissionError('fixture denied')
            return original(path, *args, **kwargs)
        with patch.object(Path, 'stat', fail):
            with self.assertRaisesRegex(AccountingUnavailable, 'Journal accounting unavailable'):
                budget.observe(sqlite_paths=[self.database])
        self.assertIsNotNone(budget.receipt()['failure'])

    def test_delta_progress_uses_same_global_guard_and_rolls_back_both(self):
        main, delta = sqlite3.connect(':memory:'), sqlite3.connect(':memory:')
        self.addCleanup(main.close)
        self.addCleanup(delta.close)
        for connection in (main, delta):
            connection.execute('CREATE TABLE values_(n)')
        counter = [0]
        budget = PublicationBudget(limits=BudgetLimits(sqlite_write_bytes=5), io_reader=lambda: counter[0])
        budget.preflight(journal_estimate_bytes=0, sqlite_write_estimate_bytes=0, rows=0, transfer_bytes=0)
        with self.assertRaises(sqlite3.OperationalError):
            with budget.sqlite_progress_guard(main, opcode_interval=1, other_connections=(delta,)):
                main.execute('INSERT INTO values_ VALUES(1)')
                delta.execute('INSERT INTO values_ VALUES(1)')
                counter[0] = 6
                delta.execute('INSERT INTO values_ VALUES(2)')
        self.assertEqual(main.execute('SELECT count(*) FROM values_').fetchone()[0], 0)
        self.assertEqual(delta.execute('SELECT count(*) FROM values_').fetchone()[0], 0)
        self.assertIn('sqlite_write_bytes budget exceeded', budget.receipt()['failure'])

    def test_actual_sqlite_journal_growth_interrupts_before_commit(self):
        self.database.unlink()
        connection = sqlite3.connect(self.database)
        self.addCleanup(connection.close)
        connection.execute('CREATE TABLE values_(n TEXT)')
        connection.executemany('INSERT INTO values_ VALUES(?)', [('x' * 4000,)] * 20)
        connection.commit()
        budget = self.budget(journal_bytes=1024)
        with self.assertRaises(sqlite3.OperationalError):
            with budget.sqlite_progress_guard(connection, opcode_interval=1, sqlite_paths=[self.database]):
                connection.execute("UPDATE values_ SET n=replace(n,'x','y')")
        self.assertEqual(connection.execute('SELECT substr(n,1,1) FROM values_ LIMIT 1').fetchone()[0], 'x')
        self.assertGreater(budget.receipt()['observed']['journal_high_water_logical_bytes'], 1024)
        self.assertIn('journal_bytes budget exceeded', budget.receipt()['failure'])

    def test_actual_wal_growth_is_guarded_before_commit(self):
        self.database.unlink()
        connection = sqlite3.connect(self.database)
        self.addCleanup(connection.close)
        connection.execute('PRAGMA journal_mode=WAL')
        connection.execute('PRAGMA cache_size=1')
        connection.execute('CREATE TABLE values_(n TEXT)')
        connection.executemany('INSERT INTO values_ VALUES(?)', [('x' * 4000,)] * 20)
        connection.commit()
        connection.execute('PRAGMA wal_checkpoint(TRUNCATE)')
        budget = self.budget(journal_bytes=1024)
        with self.assertRaises(sqlite3.OperationalError):
            with budget.sqlite_progress_guard(connection, opcode_interval=1, sqlite_paths=[self.database]):
                connection.execute("UPDATE values_ SET n=replace(n,'x','y')")
        self.assertEqual(connection.execute('SELECT substr(n,1,1) FROM values_ LIMIT 1').fetchone()[0], 'x')
        wal = str(self.database) + '-wal'
        self.assertGreater(budget.receipt()['journal_files'][wal], 1024)
        self.assertIn('journal_bytes budget exceeded', budget.receipt()['failure'])


if __name__ == '__main__':
    unittest.main()
