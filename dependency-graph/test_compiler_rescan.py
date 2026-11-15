"""Explicit all-unit extraction must retain routine publisher budget guards."""
import ast
from contextlib import ExitStack
from dataclasses import asdict
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import refresh_graph
from context_runtime import ContextError, sha
from publication_budget import BudgetExceeded, BudgetLimits
# Load the actual budget factory without the publisher-only neo4j dependency.
_tree = ast.parse((Path(__file__).parent / 'refresh_publish.py').read_text())
_factory = next(node for node in _tree.body
                if isinstance(node, ast.FunctionDef) and node.name == 'publication_budget')
_scope = {'ContextError': ContextError}
exec(compile(ast.Module(body=[_factory], type_ignores=[]), 'refresh_publish.py', 'exec'), _scope)
publication_budget = _scope['publication_budget']


class CompilerRescanTests(unittest.TestCase):
    def exercise(self, **options):
        scratch = Path(__file__).resolve().parents[1] / 'temp/test-work'
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='compiler-rescan-', dir=scratch) as directory:
            root = Path(directory)
            reviewed_rows = options.pop('reviewed_rows', None)
            reviewed_bytes = options.pop('reviewed_bytes', None)
            if reviewed_rows is not None:
                forecast = root / 'forecast.json'
                forecast.write_text('{"mandatory_rows": 302128}')
                review = root / 'review.json'
                record = {'rows': reviewed_rows,
                    'reason': 'Measured compact memberships exceed routine row count',
                    'evidence': {'path': 'forecast.json', 'sha256': sha(forecast)}}
                if reviewed_bytes is not None:
                    resource = root / 'measured.json'; resource.write_text('{"write_bytes": 271912960}')
                    record.update(byte_limits=reviewed_bytes,
                                  resource_evidence={'path': 'measured.json', 'sha256': sha(resource)})
                review.write_text(json.dumps(record))
                options['row_budget_review'] = review
            base = root / 'dependency-graph'
            base.mkdir()
            state_path = base / 'current.json'
            state_path.write_text(json.dumps({'files': {}, 'source_inventory': []}))
            (base / 'ACTIVE.json').write_text(json.dumps({
                'state': 'dependency-graph/current.json', 'state_sha256': sha(state_path)}))
            c = sqlite3.connect(':memory:')
            c.execute('CREATE TABLE units(owner TEXT)')
            c.execute('INSERT INTO units VALUES("old")')
            c.execute('CREATE TABLE meta(key TEXT,value TEXT)')
            wanted = [('a', {'file': 'a.cpp'}), ('b', {'file': 'b.cpp'})]
            calls = []

            def fake_run(argv, out, label):
                self.assertEqual(label, 'ctest-inventory')
                (out / 'ctest-inventory.log').write_text('{"tests": []}')

            def fake_docker(script, out, label, analysis=False):
                plan = json.loads((out / 'plan.json').read_text())
                units = json.loads((out / 'units.json').read_text())
                calls.append((label, analysis, plan, units))

            with ExitStack() as stack:
                for name, value in dict(ROOT=root, BASE=base, GROUPS=[], PRODUCERS=()).items():
                    stack.enter_context(patch.object(refresh_graph, name, value))
                for name, values in {
                    'connect': {'return_value': c},
                    'guard': {'side_effect': ContextError('stale')},
                    'inventory': {'return_value': ['uc-library/include/new.hpp']},
                    'requires_reconfigure': {'return_value': False},
                    'rows': {'return_value': wanted},
                    'compiler_invalidation': {'return_value': (True, 'header or unknown inventory change')},
                    'stale_units': {'return_value': ({'a', 'b'}, set())},
                    'run': {'side_effect': fake_run},
                    'docker': {'side_effect': fake_docker},
                }.items():
                    stack.enter_context(patch.object(refresh_graph, name, **values))
                if not options:
                    with self.assertRaisesRegex(ContextError, 'Automatic full rebuild refused'):
                        refresh_graph.ensure_fresh()
                else:
                    result = refresh_graph.ensure_fresh(**options)
                    self.assertEqual(result['recompiled_units'], 2)
            return calls

    def test_automatic_all_unit_invalidation_stops_before_extraction_or_publication(self):
        self.assertEqual(self.exercise(), [])

    def test_rescan_extracts_all_units_and_keeps_actual_routine_publisher_limits(self):
        calls = self.exercise(compiler_rescan='new production headers')
        self.assertEqual([(x[0], x[1]) for x in calls], [('extract', True), ('publish', False)])
        plan = calls[-1][2]
        self.assertEqual(plan['compiler_rescan']['authorization'], 'new production headers')
        self.assertTrue(plan['compiler_invalidation_all'])
        self.assertEqual([x[0] for x in calls[0][3]], ['a', 'b'])
        budget = publication_budget(plan)
        self.assertEqual(budget.mode, 'routine')
        self.assertEqual(asdict(budget.limits), asdict(BudgetLimits()))
        with self.assertRaises(BudgetExceeded):
            budget.preflight(journal_estimate_bytes=0, sqlite_write_estimate_bytes=0,
                             rows=BudgetLimits().rows + 1, transfer_bytes=0)

    def test_full_rebuild_preserves_separate_larger_budgets(self):
        calls = self.exercise(full_rebuild=True, rebuild_authorization='explicit rebuild')
        plan = calls[-1][2]
        self.assertNotIn('compiler_rescan', plan)
        budget = publication_budget(plan)
        self.assertEqual(budget.mode, 'full_rebuild')
        self.assertEqual(budget.limits.rows, 10000000)

    def test_explicit_review_changes_only_global_row_ceiling(self):
        calls = self.exercise(compiler_rescan='reviewed compact update', reviewed_rows=500000)
        plan = calls[-1][2]
        budget = publication_budget(plan)
        expected = asdict(BudgetLimits()); expected['rows'] = 500000
        self.assertEqual(asdict(budget.limits), expected)
        self.assertEqual(budget.mode, 'routine')
        self.assertEqual(plan['publication_budget']['row_budget_review']['review']['rows'], 500000)
        budget.preflight(journal_estimate_bytes=0, sqlite_write_estimate_bytes=0,
                         rows=302128, transfer_bytes=0)
        with self.assertRaises(BudgetExceeded):
            budget.charge_rows(500001)

    def test_review_rejects_missing_or_changed_evidence(self):
        scratch = Path(__file__).resolve().parents[1] / 'temp/test-work'
        with tempfile.TemporaryDirectory(prefix='row-review-', dir=scratch) as directory:
            root = Path(directory); evidence = root / 'forecast.json'; evidence.write_text('{}')
            review = root / 'review.json'
            review.write_text(json.dumps({'rows': 500000, 'reason': 'Measured input',
                'evidence': {'path': 'forecast.json', 'sha256': sha(evidence)}}))
            with patch.object(refresh_graph, 'ROOT', root):
                self.assertEqual(refresh_graph.reviewed_row_allowance(review)['review']['rows'], 500000)
                evidence.write_text('{"changed": true}')
                with self.assertRaisesRegex(ContextError, 'evidence mismatch'):
                    refresh_graph.reviewed_row_allowance(review)

    def test_explicit_measured_byte_exception_remains_finite_and_transfer_unchanged(self):
        limits = {'journal_bytes': 256 * 1024**2, 'sqlite_write_bytes': 512 * 1024**2}
        plan = self.exercise(compiler_rescan='Measured accumulated update', reviewed_rows=500000,
                             reviewed_bytes=limits)[-1][2]
        budget = publication_budget(plan)
        self.assertEqual(budget.limits.journal_bytes, limits['journal_bytes'])
        self.assertEqual(budget.limits.sqlite_write_bytes, limits['sqlite_write_bytes'])
        self.assertEqual(budget.limits.transfer_bytes, BudgetLimits().transfer_bytes)
        with self.assertRaisesRegex(ContextError, 'configured ceilings'):
            self.exercise(compiler_rescan='invalid', reviewed_rows=500000,
                          reviewed_bytes={'sqlite_write_bytes': 4 * 1024**3 + 1})

    def test_measured_request_envelope_review_has_finite_1gib_ceiling(self):
        maximum = 1024**3
        plan = self.exercise(compiler_rescan='measured apply and verification envelopes',
                             reviewed_rows=2000000,
                             reviewed_bytes={'transfer_bytes': maximum})[-1][2]
        budget = publication_budget(plan)
        self.assertEqual(budget.limits.transfer_bytes, maximum)
        self.assertEqual(budget.limits.sqlite_write_bytes, BudgetLimits().sqlite_write_bytes)
        with self.assertRaises(BudgetExceeded):
            budget.preflight(journal_estimate_bytes=0, sqlite_write_estimate_bytes=0,
                             rows=0, transfer_bytes=maximum + 1)
        with self.assertRaisesRegex(ContextError, 'configured ceilings'):
            self.exercise(compiler_rescan='excessive wire allowance', reviewed_rows=2000000,
                          reviewed_bytes={'transfer_bytes': maximum + 1})

    def test_explicit_448mib_journal_review_keeps_routine_and_other_caps(self):
        limits = {'journal_bytes': 448 * 1024**2,
                  'sqlite_write_bytes': 736 * 1024**2,
                  'transfer_bytes': 416 * 1024**2}
        plan = self.exercise(compiler_rescan='Exact completed capture and measured WAL forecast',
                             reviewed_rows=1800000, reviewed_bytes=limits)[-1][2]
        budget = publication_budget(plan)
        self.assertEqual(budget.limits.journal_bytes, limits['journal_bytes'])
        self.assertEqual(budget.limits.sqlite_write_bytes, limits['sqlite_write_bytes'])
        self.assertEqual(budget.limits.transfer_bytes, limits['transfer_bytes'])
        self.assertEqual(BudgetLimits().journal_bytes, 1024**3)
        self.assertEqual(BudgetLimits().sqlite_write_bytes, 4 * 1024**3)
        self.assertEqual(BudgetLimits().transfer_bytes, 1024**3)
        with self.assertRaises(BudgetExceeded):
            budget.preflight(journal_estimate_bytes=limits['journal_bytes'] + 1,
                             sqlite_write_estimate_bytes=0, rows=0, transfer_bytes=0)
        for excessive in ({'journal_bytes': 1024**3 + 1},
                          {'sqlite_write_bytes': 4 * 1024**3 + 1},
                          {'transfer_bytes': 1024**3 + 1}):
            with self.subTest(excessive=excessive), self.assertRaisesRegex(ContextError, 'configured ceilings'):
                self.exercise(compiler_rescan='Out of reviewed bounds',
                              reviewed_rows=1800000, reviewed_bytes=excessive)

    def test_explicit_delta_transfer_review_is_bounded(self):
        plan = self.exercise(compiler_rescan='Measured complete delta', reviewed_rows=500000,
                             reviewed_bytes={'transfer_bytes': 256 * 1024**2})[-1][2]
        budget = publication_budget(plan)
        self.assertEqual(budget.limits.transfer_bytes, 256 * 1024**2)
        with self.assertRaises(BudgetExceeded):
            budget.preflight(journal_estimate_bytes=0, sqlite_write_estimate_bytes=0,
                             rows=0, transfer_bytes=256 * 1024**2 + 1)

    def test_invalid_or_conflicting_options_fail_before_reading_or_resuming_state(self):
        variants = [dict(compiler_rescan=''), dict(compiler_rescan=' '),
                    dict(row_budget_review=Path('review.json')),
                    dict(compiler_rescan=1), dict(compiler_rescan='reason', force=True),
                    dict(compiler_rescan='reason', full_rebuild=True, rebuild_authorization='reason'),
                    dict(compiler_rescan='reason', verify_build_plan=Path('plan.json'))]
        with patch.object(refresh_graph, 'check_existing_identity') as read:
            for options in variants:
                with self.subTest(options=options), self.assertRaises(ContextError):
                    refresh_graph.ensure_fresh(**options)
            read.assert_not_called()


if __name__ == '__main__':
    unittest.main()
