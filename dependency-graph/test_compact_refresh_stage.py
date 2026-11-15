"""Real compact refresh stage transactions on tiny project-local fixtures.

Only extractor output and the native-provider seal are substituted. Compact SQL,
unit observations, build inventory, net delta and budget enforcement execute.
No server, firmware provider or operational SQLite file is opened.
"""
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import refresh_publish
from context_runtime import ContextError, sha
from publication_budget import BudgetExceeded
from refresh_facts import connect


class ClosingConnection:
    """Observe writes/transaction state before stage owns the actual close."""
    def __init__(self, connection):
        self.connection = connection
        self.closed = False

    def __getattr__(self, name):
        return getattr(self.connection, name)

    def close(self):
        if not self.closed:
            self.total_changes_at_close = self.connection.total_changes
            self.in_transaction_at_close = self.connection.in_transaction
            self.connection.close()
            self.closed = True


class CompactRefreshStageTests(unittest.TestCase):
    def setUp(self):
        scratch = Path(__file__).resolve().parents[1] / 'temp/test-work'
        scratch.mkdir(parents=True, exist_ok=True)
        temporary = tempfile.TemporaryDirectory(prefix='compact-refresh-stage-', dir=scratch)
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        environment = patch.dict(os.environ, TMPDIR=str(self.root), SQLITE_TMPDIR=str(self.root))
        environment.start()
        self.addCleanup(environment.stop)
        self.build = self.root / 'build'
        for name in ('uc-library/CMakeLists.txt', 'uc-library/cmake/Inputs.cmake',
                     'build/compile_commands.json', 'build/CMakeCache.txt',
                     'build/upstream-core/build/compile_commands.json',
                     'build/upstream-core/build/CMakeCache.txt'):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('[]' if name.endswith('.json') else '# fixture\n')
        self.rows = {}
        for owner in ('a', 'b'):
            source = self.root / ('uc-library/src/' + owner + '.cpp')
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_text('int ' + owner + '() { return 1; }\n')
            self.rows[owner] = dict(file=str(source), directory=str(self.build),
                                    arguments=['c++', '-c', str(source), '-o', owner + '.o'])
        self.edges = {owner: {('shared', 'external', 'CALLS', 'same captured evidence')}
                      for owner in self.rows}
        self.fail_source = False
        self.database = self.root / 'source.sqlite'
        self.c = connect(self.database)
        self.addCleanup(lambda: self.c.close())
        self.c.commit()
        for name, value in [('ROOT', self.root), ('BUILD', self.build)]:
            replacement = patch.object(refresh_publish, name, value)
            replacement.start()
            self.addCleanup(replacement.stop)
        replacement = patch.object(refresh_publish, 'facts', side_effect=self.extractor_facts)
        replacement.start()
        self.addCleanup(replacement.stop)
        replacement = patch('native_candidate_gate.seal_guard', return_value={'version': 1, 'sources': [], 'fixture': True})
        self.seal = replacement.start()
        self.addCleanup(replacement.stop)
        self.counter = 0
        self.attempt()  # Real initial stage populates compact facts + observations.
        self.clear_pending()

    def extractor_facts(self, root, owner, row, ast, gcc):
        self.assertEqual(root, self.root)
        self.assertEqual(row, self.rows[owner])
        captured = json.loads(ast.read_text())
        self.assertEqual(set(captured['input_sha256']), {row['file']})
        if self.fail_source:
            Path(row['file']).write_text('int ' + owner + '() { return 2; }\n')
        nodes = {
            'tu:' + owner: dict(kind='TranslationUnit', label=owner, metadata={}),
            'shared': dict(kind='Function', label='shared', metadata={}),
            'external': dict(kind='Function', label='external', metadata={}),
        }
        return nodes, self.edges[owner]

    def output(self, limits=None):
        self.counter += 1
        out = self.root / ('attempt-' + str(self.counter))
        out.mkdir()
        plan = {'removed_units': []}
        if limits is not None:
            plan['publication_budget'] = {'limits': limits}
        (out / 'plan.json').write_text(json.dumps(plan))
        (out / 'units.json').write_text(json.dumps(list(self.rows.items())))
        (out / 'ctest-inventory.log').write_text(json.dumps({'tests': []}))
        for owner, row in self.rows.items():
            dest = out / 'observations' / owner
            dest.mkdir(parents=True)
            (dest / 'ast.json').write_text(json.dumps({
                'input_sha256': {row['file']: sha(Path(row['file']))},
                'external_inputs': [],
            }))
            (dest / '0000.json').write_text('{}')
        return out

    def attempt(self, limits=None):
        out = self.output(limits)
        self.stage(out)
        return out

    def stage(self, out):
        observed = ClosingConnection(self.c)
        self.last_stage_connection = observed
        try:
            refresh_publish.stage(observed, out)
        finally:
            self.assertTrue(observed.closed, 'stage owns closing its source connection')
            self.c = connect(self.database)

    def clear_pending(self):
        self.c.execute("DELETE FROM meta WHERE key='pending'")
        self.c.commit()

    def snapshot(self):
        return tuple(self.c.iterdump())

    def test_unchanged_facts_emit_zero_net_edges_through_actual_stage(self):
        self.seal.reset_mock()
        out = self.attempt()
        with sqlite3.connect(out / 'delta.sqlite') as delta:
            for table in ('old_edges', 'new_edges', 'nodes', 'orphan_nodes'):
                self.assertEqual(delta.execute('SELECT count(*) FROM ' + table).fetchone()[0], 0)
            self.assertEqual(delta.execute(
                "SELECT value FROM settings WHERE key='delta_storage_version'").fetchone()[0], 2)
        self.assertEqual(self.c.execute("SELECT value FROM meta WHERE key='pending'").fetchone()[0], str(out))
        self.assertEqual(self.c.execute('SELECT count(*) FROM unit_observations').fetchone()[0], 2)
        self.assertEqual(json.loads((out / 'stage-changes.json').read_text())['counts']['new_edges'], 0)
        self.assertTrue(json.loads((out / 'refresh-report.json').read_text())['source_graph_refresh'])
        self.seal.assert_called_once()
        timing = json.loads((out / 'stage-timings.json').read_text())
        self.assertTrue({'capture_equivalence','generate_facts','replace_unit','build_facts',
                         'replace_build_facts','finish_delta','input_hash_checks','verify_retained',
                         'candidate_seal'} <= timing['phases'].keys())
        self.assertEqual(timing['phases']['replace_unit']['calls'], 2)
        self.assertGreaterEqual(timing['other_seconds'], 0)

    def test_one_owner_change_retains_shared_edge_owned_by_other_unit(self):
        self.edges['a'] = {('shared', 'external', 'READS', 'replacement evidence')}
        out = self.attempt()
        with sqlite3.connect(out / 'delta.sqlite') as delta:
            self.assertEqual(delta.execute('SELECT src,dst,kind,evidence FROM old_edges').fetchall(), [])
            self.assertEqual(delta.execute('SELECT src,dst,kind,evidence FROM new_edges').fetchall(),
                             [('shared', 'external', 'READS', 'replacement evidence')])
        self.assertEqual(self.c.execute(
            "SELECT owner FROM edge_facts WHERE kind='CALLS' ORDER BY owner").fetchall(), [('b',)])
        self.assertEqual(self.c.execute(
            "SELECT owner FROM edge_facts WHERE kind='READS' ORDER BY owner").fetchall(), [('a',)])

    def test_late_source_hash_failure_rolls_back_all_source_changes_and_pending(self):
        before = self.snapshot()
        changes = self.c.total_changes
        self.edges['a'] = {('shared', 'external', 'READS', 'not committed')}
        self.fail_source = True
        self.seal.reset_mock()
        out = self.output()
        with self.assertRaisesRegex(ContextError, 'Inputs changed before publication'):
            self.stage(out)
        # Prove writes really ran before the late failure, then verify rollback.
        self.assertGreater(self.last_stage_connection.total_changes_at_close, changes)
        self.assertEqual(self.snapshot(), before)
        self.assertFalse(self.last_stage_connection.in_transaction_at_close)
        self.assertFalse(self.c.in_transaction)
        self.assertIsNone(self.c.execute("SELECT value FROM meta WHERE key='pending'").fetchone())
        self.assertFalse((out / 'refresh-report.json').exists())
        self.seal.assert_not_called()
        with sqlite3.connect(out / 'delta.sqlite') as delta:
            self.assertEqual(delta.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall(), [])

    def test_budget_failure_precedes_owner_writes(self):
        before = self.snapshot()
        changes = self.c.total_changes
        self.edges['a'] = {('shared', 'external', 'READS', 'must not be written')}
        out = self.output({'rows': 1})
        self.seal.reset_mock()
        with self.assertRaises(BudgetExceeded):
            self.stage(out)
        self.assertEqual(self.last_stage_connection.total_changes_at_close, changes)
        self.assertEqual(self.snapshot(), before)
        self.assertFalse(self.last_stage_connection.in_transaction_at_close)
        self.assertFalse(self.c.in_transaction)
        self.assertIsNone(self.c.execute("SELECT value FROM meta WHERE key='pending'").fetchone())
        self.assertFalse((out / 'refresh-report.json').exists())
        receipt = json.loads((out / 'stage-budget.json').read_text())
        self.assertIsNotNone(receipt['failure'])
        self.seal.assert_not_called()


if __name__ == '__main__':
    unittest.main()
