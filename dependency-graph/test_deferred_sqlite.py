import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'dependency-graph'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from publication_budget import BudgetExceeded, BudgetLimits, PublicationBudget, read_proc_write_bytes
from deferred_sqlite import commit_and_close, deferred_reserve


class DeferredWrites(unittest.TestCase):
    def fixture(self, directory):
        paths = [Path(directory) / 'main.sqlite', Path(directory) / 'delta.sqlite']
        main, delta = [sqlite3.connect(p) for p in paths]
        main.execute('PRAGMA journal_mode=WAL')
        main.execute('PRAGMA synchronous=FULL')
        main.execute('PRAGMA wal_autocheckpoint=0')
        main.execute('PRAGMA cache_size=-1024')
        delta.execute('PRAGMA cache_size=-512')
        for c in [main, delta]:
            c.execute('CREATE TABLE data(value BLOB)')
            c.execute('CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT)')
            c.commit()
        return main, delta, paths

    def budget(self, limit=32 * 1024**2, reader=read_proc_write_bytes):
        b = PublicationBudget(BudgetLimits(sqlite_write_bytes=limit), io_reader=reader)
        b.preflight(journal_estimate_bytes=0, sqlite_write_estimate_bytes=0, rows=0, transfer_bytes=0)
        b.completed_stage_estimate = dict(complete=True, estimates=dict(b.estimates))
        return b

    def test_real_wal_commit_checkpoint_close_accounted(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'temp') as d:
            main, delta, paths = self.fixture(d)
            b = self.budget()
            for c in [main, delta]:
                c.execute('INSERT INTO data VALUES(zeroblob(262144))')
            result = commit_and_close(main, delta, b, paths, pending_value='capture')
            self.assertEqual(result['state'], 'committed_pending')
            self.assertTrue(result['closed'])
            self.assertGreater(b.write_bytes, 0)
            self.assertEqual(b.write_bytes, read_proc_write_bytes() - b.baseline)
            self.assertEqual(result['checkpoints'][0]['result'][0], 0)
            with sqlite3.connect(paths[0]) as c:
                self.assertEqual(c.execute('SELECT value FROM meta WHERE key="pending"').fetchone()[0], 'capture')

    def test_reserve_rejects_before_either_commit(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'temp') as d:
            main, delta, paths = self.fixture(d)
            b = self.budget(6 * 1024**2)
            for c in [main, delta]:
                c.execute('INSERT INTO data VALUES(zeroblob(65536))')
            self.assertGreater(deferred_reserve((main, delta), paths, b)['bytes'], b.limits.sqlite_write_bytes)
            with self.assertRaises(BudgetExceeded):
                commit_and_close(main, delta, b, paths, pending_value='capture')
            self.assertEqual(b.deferred_sqlite['state'], 'rolled_back')
            self.assertTrue(b.deferred_sqlite['closed'])
            for path in paths:
                with sqlite3.connect(path) as c:
                    self.assertEqual(c.execute('SELECT count(*) FROM data').fetchone()[0], 0)
                    self.assertEqual(c.execute('SELECT count(*) FROM meta').fetchone()[0], 0)

    def test_late_failure_keeps_real_pending_commit(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'temp') as d:
            main, delta, paths = self.fixture(d)
            # Real SQLite writes; only accounting failure injected after main commit.
            b = self.budget()
            original = b.observe
            def observe(*args, **kwargs):
                original(*args, **kwargs)
                if not main.in_transaction:
                    raise BudgetExceeded('injected postcommit accounting failure')
            b.observe = observe
            for c in [main, delta]:
                c.execute('INSERT INTO data VALUES(zeroblob(65536))')
            with self.assertRaises(BudgetExceeded):
                commit_and_close(main, delta, b, paths, pending_value='capture')
            self.assertEqual(b.deferred_sqlite['state'], 'committed_pending')
            self.assertTrue(b.deferred_sqlite['closed'])
            with sqlite3.connect(paths[0]) as c:
                self.assertEqual(c.execute('SELECT value FROM meta WHERE key="pending"').fetchone()[0], 'capture')

    def test_actual_proposed_stage_default_routine_and_reopen(self):
        self.run_proposed_stage(False)

    def test_actual_proposed_stage_precommit_rejects(self):
        self.run_proposed_stage(True)

    def run_proposed_stage(self, reject):
        import ast
        import pathlib
        from context_runtime import ContextError
        from deferred_sqlite import staging_cache_kib
        self.assertEqual(staging_cache_kib(256 * 1024**2), 87381)
        self.assertEqual(staging_cache_kib(768 * 1024**2), 262144)
        source = Path(__file__).with_name('refresh_publish.py')
        tree = ast.parse(source.read_text())
        functions = [x for x in tree.body if isinstance(x, ast.FunctionDef) and x.name in ('stage', 'publication_budget')]
        scope = dict(json=json, pathlib=pathlib, sqlite3=sqlite3, ContextError=ContextError)
        counter = [0]
        with tempfile.TemporaryDirectory(dir=ROOT / 'temp') as directory:
            out = Path(directory)
            main_path = out / 'main.sqlite'
            main = sqlite3.connect(main_path)
            main.execute('PRAGMA journal_mode=WAL')
            main.execute('CREATE TABLE data(value BLOB)')
            main.execute('CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT)')
            main.commit()
            (out / 'plan.json').write_text('{}')
            (out / 'units.json').write_text('[]')
            def body(c, output, delta, plan, selected, budget):
                c.execute('INSERT INTO data VALUES(zeroblob(87381))')
                delta.execute('CREATE TABLE payload(value BLOB)')
                delta.execute('INSERT INTO payload VALUES(zeroblob(87381))')
                budget.completed_stage_estimate = dict(complete=True, estimates=dict(budget.estimates))
                if reject:
                    counter[0] = 250 * 1024**2
            scope['_stage_compact'] = body
            exec(compile(ast.Module(body=functions, type_ignores=[]), str(source), 'exec'), scope)
            budget = self.budget(reader=(lambda: counter[0]) if reject else read_proc_write_bytes)
            # Actual routine256MiB limits, not the small helper-fixture allowance.
            budget = PublicationBudget(io_reader=(lambda: counter[0]) if reject else read_proc_write_bytes)
            if reject:
                with self.assertRaises(BudgetExceeded):
                    scope['stage'](main, out, budget=budget)
            else:
                scope['stage'](main, out, budget=budget)
            with self.assertRaises(sqlite3.ProgrammingError):
                main.execute('SELECT 1')
            receipt = json.loads((out / 'stage-budget.json').read_text())
            self.assertEqual(receipt['staging_cache_kib'], 87381)
            self.assertTrue(receipt['deferred_sqlite']['closed'])
            # Same ownership transition used by proposed main caller.
            with sqlite3.connect(main_path) as reopened:
                pending = reopened.execute('SELECT value FROM meta WHERE key="pending"').fetchone()
                self.assertEqual(pending, None if reject else (str(out),))
                self.assertEqual(reopened.execute('SELECT count(*) FROM data').fetchone()[0], 0 if reject else 1)

    def test_real_failed_budget_rollback_close_final_sample(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'temp') as d:
            main, delta, paths = self.fixture(d)
            main.execute('PRAGMA cache_size=-64')
            b = self.budget(limit=65536)
            main.executemany('INSERT INTO data VALUES(zeroblob(3000))', [() for _ in range(512)])
            with self.assertRaises(BudgetExceeded):
                b.observe([paths[1]], sqlite_paths=paths)
            original = b.failure
            main.rollback(); delta.rollback(); main.close(); delta.close()
            b.observe_final_io()
            self.assertEqual(b.failure, original)
            self.assertEqual(b.write_bytes, read_proc_write_bytes() - b.baseline)
            self.assertGreater(b.write_bytes, b.limits.sqlite_write_bytes)

    def test_final_raw_sample_preserves_failure_and_records_cleanup(self):
        counter = [0]
        b = self.budget(reader=lambda: counter[0])
        b.failure = 'original staging failure'
        counter[0] = 40 * 1024**2
        self.assertEqual(b.observe_final_io(), counter[0])
        self.assertEqual(b.failure, 'original staging failure')
        self.assertGreater(b.write_bytes, b.limits.sqlite_write_bytes)

    def test_estimate_less_than_observed_keeps_floor_and_cache_diagnostics(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'temp') as d:
            main, delta, paths = self.fixture(d)
            b = self.budget()
            b.write_bytes = 1024
            reserve = deferred_reserve((main, delta), paths, b)
            self.assertEqual(reserve['residual_estimate_bytes'], 0)
            self.assertGreaterEqual(reserve['bytes'], 20 * 1024**2)
            self.assertEqual(reserve['configurations'][0]['cache_size'], -1024)
            main.close(); delta.close()

    def test_missing_invalid_or_changed_final_estimate_rejected(self):
        from publication_budget import AccountingUnavailable
        for value in [None, -1, float('inf'), float('nan'), True]:
            with self.subTest(value=value), tempfile.TemporaryDirectory(dir=ROOT / 'temp') as d:
                main, delta, paths = self.fixture(d)
                b = self.budget()
                if value is None:
                    del b.completed_stage_estimate
                else:
                    b.estimates['sqlite_write_bytes'] = value
                    b.completed_stage_estimate = dict(complete=True, estimates=dict(b.estimates))
                with self.assertRaises(AccountingUnavailable):
                    commit_and_close(main, delta, b, paths, pending_value='capture')
                self.assertEqual(b.deferred_sqlite['state'], 'rolled_back')

    def test_final_estimate_exceeds_cap_before_commits(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'temp') as d:
            main, delta, paths = self.fixture(d)
            b = self.budget()
            b.estimates['sqlite_write_bytes'] = b.limits.sqlite_write_bytes + 1
            b.completed_stage_estimate = dict(complete=True, estimates=dict(b.estimates))
            with self.assertRaises(BudgetExceeded):
                commit_and_close(main, delta, b, paths, pending_value='capture')
            self.assertEqual(b.deferred_sqlite['state'], 'rolled_back')

    def test_actual_counter_exceed_after_commit_keeps_pending(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'temp') as d:
            main, delta, paths = self.fixture(d)
            counter = [0]
            b = self.budget(reader=lambda: counter[0])
            main.execute('INSERT INTO data VALUES(zeroblob(1000))')
            delta.execute('INSERT INTO data VALUES(zeroblob(1000))')
            original = b.observe
            def observe(*args, **kwargs):
                if not main.in_transaction:
                    counter[0] = b.limits.sqlite_write_bytes + 4096
                return original(*args, **kwargs)
            b.observe = observe
            with self.assertRaises(BudgetExceeded):
                commit_and_close(main, delta, b, paths, pending_value='capture')
            self.assertEqual(b.deferred_sqlite['state'], 'committed_pending')
            self.assertGreater(b.write_bytes, b.limits.sqlite_write_bytes)
            with sqlite3.connect(paths[0]) as c:
                self.assertEqual(c.execute('SELECT value FROM meta WHERE key="pending"').fetchone(), ('capture',))

    def test_real_finish_marks_complete_only_after_delta_and_prune(self):
        from compact_facts import create_schema
        from incremental_stage import IncrementalStage
        c = sqlite3.connect(':memory:'); delta = sqlite3.connect(':memory:')
        create_schema(c); c.commit(); c.execute('BEGIN'); delta.execute('BEGIN')
        b = self.budget(); del b.completed_stage_estimate
        stage = IncrementalStage(c, b)
        self.assertFalse(hasattr(b, 'completed_stage_estimate'))
        stage.finish(delta)
        self.assertTrue(stage.finished)
        self.assertEqual(b.completed_stage_estimate, dict(complete=True, estimates=b.estimates))
        self.assertGreater(b.estimates['sqlite_write_bytes'], 0)
        c.rollback(); delta.rollback(); c.close(); delta.close()

    def test_prior_overrun_reserve_rejects(self):
        # Historical exact precommit counter was not retained. Test a finite
        # near-cap observation plus the nonzero16MiB deferred estimate floor.
        with tempfile.TemporaryDirectory(dir=ROOT / 'temp') as d:
            main, delta, paths = self.fixture(d)
            main.execute('PRAGMA cache_size=-262144')
            delta.execute('PRAGMA cache_size=-2000')
            counter = [0]
            b = self.budget(768 * 1024**2, lambda: counter[0])
            counter[0] = 760 * 1024**2
            main.execute('BEGIN'); delta.execute('BEGIN')
            with self.assertRaises(BudgetExceeded):
                commit_and_close(main, delta, b, paths, pending_value='capture')
            self.assertEqual(b.deferred_sqlite['state'], 'rolled_back')


if __name__ == '__main__':
    unittest.main()
