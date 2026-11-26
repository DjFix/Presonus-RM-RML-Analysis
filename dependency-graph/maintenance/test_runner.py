"""Offline runner checks; invoke is mocked, no Git/graph/systemd execution."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
import runner

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / 'temp/test-work/graph-resume-job'
WORK.mkdir(parents=True, exist_ok=True)
GUARD = Path(__file__).resolve().parents[1] / 'production_write_stop.py'


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(dir=WORK)
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.job = self.root / 'job'
        self.job.mkdir()
        self.graph = self.root / 'dependency-graph'
        self.graph.mkdir()
        self.policy = self.graph / 'PRODUCTION_GRAPH_STOP.json'
        self.prior = b'{ "version":1, "production_graph_updates":"stopped" }\n'
        self.policy.write_bytes(self.prior)
        self.head = 'a' * 40
        self.calls = []
        self.refresh_result = 0
        self.foreign = None
        self.refresh_exception = None
        guard = GUARD.read_text().replace(
            "PRODUCTION_ROOT = Path('/home/rs/projects/opencs/ai-line-analysis')",
            'PRODUCTION_ROOT = Path(' + repr(str(self.root)) + ')')
        (self.graph / 'production_write_stop.py').write_text(guard)
        (self.graph / 'refresh_graph.py').write_text('# never executed\n')
        (self.graph / 'publication_budget.py').write_text(
            'class BudgetLimits:\n journal_bytes=3*1024**3\n sqlite_write_bytes=12*1024**3\n transfer_bytes=3*1024**3\n rows=30000000\n')
        self.receipt = self.job / 'boundary.json'
        self.receipt.write_text(json.dumps(dict(version=1, accepted=True,
            committed=True, package_scope='actual-fixture-package', commit=self.head)))
        self.activation = self.job / 'activation.json'
        self.activation.write_text(json.dumps(dict(version=2,
            production_graph_updates='maintenance_update', authority='explicit fixture review',
            boundary=dict(receipt=self.ref(self.receipt),
                          package_scope='actual-fixture-package', commit=self.head))))
        self.config = dict(root=str(self.root), unit=runner.UNIT,
            package_scope='actual-fixture-package', boundary_receipt=self.ref(self.receipt),
            guard=self.ref(self.graph / 'production_write_stop.py'),
            refresh=self.ref(self.graph / 'refresh_graph.py'),
            budget=self.ref(self.graph / 'publication_budget.py'),
            activation_policy=self.ref(self.activation),
            prior_stopped_policy_sha256=runner.digest(self.prior),
            compiler_rescan_reason='Explicit fixture authorization after committed source freeze')
        self.config_path = self.job / 'CONFIG.json'
        self.save()

    def ref(self, path):
        return dict(path=str(path.relative_to(self.root)),
                    sha256=hashlib.sha256(path.read_bytes()).hexdigest())

    def save(self):
        self.config_path.write_text(json.dumps(self.config))

    def invoke(self, argv, **kwargs):
        self.calls.append(argv)
        if argv[:3] == ['git', 'rev-parse', 'HEAD']:
            return subprocess.CompletedProcess(argv, 0, stdout=self.head + '\n')
        self.assertEqual(argv[-2:], ['--compiler-rescan', self.config['compiler_rescan_reason']])
        self.assertEqual(len(argv), 5)
        self.assertEqual(json.loads(self.policy.read_bytes())['production_graph_updates'],
                         'maintenance_update')
        if self.foreign is not None:
            self.policy.write_bytes(self.foreign)
        if self.refresh_exception:
            raise self.refresh_exception
        return subprocess.CompletedProcess(argv, self.refresh_result)

    def execute(self):
        return runner.run(self.config_path, invoke=self.invoke)

    def test_success_restores_exact_prior_bytes_and_preserves_start_identity(self):
        self.assertEqual(self.execute(), 0)
        self.assertEqual(self.policy.read_bytes(), self.prior)
        self.assertEqual((self.job / 'PRIOR-STOPPED-POLICY.json').read_bytes(), self.prior)
        status = json.loads((self.job / 'STATUS.json').read_bytes())
        self.assertTrue(status['terminal'] and status['policy_restored'])
        self.assertEqual(status['phase'], 'terminal')
        self.assertGreater(status['pid'], 0)
        self.assertIn('invocation_id', status)

    def test_failure_restores_and_records_original_exit(self):
        self.refresh_result = 9
        self.assertEqual(self.execute(), 9)
        self.assertEqual(self.policy.read_bytes(), self.prior)
        self.assertEqual(json.loads((self.job / 'STATUS.json').read_bytes())['refresh_returncode'], 9)

    def test_launch_exception_restores_policy(self):
        self.refresh_exception = OSError('mock launch failure')
        self.assertEqual(self.execute(), 1)
        self.assertEqual(self.policy.read_bytes(), self.prior)

    def test_head_mismatch_never_activates_or_invokes_refresh(self):
        self.head = 'b' * 40
        self.assertEqual(self.execute(), 1)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.policy.read_bytes(), self.prior)
        self.assertFalse((self.job / 'PRIOR-STOPPED-POLICY.json').exists())

    def test_foreign_policy_change_is_preserved_and_fails_terminal(self):
        self.foreign = b'{"version":1,"production_graph_updates":"stopped","authority":"other actor"}'
        self.assertEqual(self.execute(), 1)
        self.assertEqual(self.policy.read_bytes(), self.foreign)
        status = json.loads((self.job / 'STATUS.json').read_bytes())
        self.assertTrue(status['restoration_blocked'])
        self.assertFalse(status['policy_restored'])

    def test_changed_guard_blocks_before_activation(self):
        (self.graph / 'production_write_stop.py').write_text('# mismatched\n')
        self.assertEqual(self.execute(), 1)
        self.assertEqual(self.policy.read_bytes(), self.prior)
        self.assertEqual(len(self.calls), 1)

    def test_changed_budget_limits_block_before_activation(self):
        path = self.graph / 'publication_budget.py'
        path.write_text(path.read_text().replace('journal_bytes=3*', 'journal_bytes=4*'))
        self.config['budget'] = self.ref(path)
        self.save()
        self.assertEqual(self.execute(), 1)
        self.assertEqual(self.policy.read_bytes(), self.prior)
        self.assertEqual(len(self.calls), 1)

    def test_boundary_hash_mismatch_never_calls_git_or_activates(self):
        self.receipt.write_text('{}')
        self.assertEqual(self.execute(), 1)
        self.assertFalse(self.calls)
        self.assertEqual(self.policy.read_bytes(), self.prior)

    def test_existing_started_receipt_prohibits_retry(self):
        self.assertEqual(self.execute(), 0)
        prior_status = (self.job / 'STATUS.json').read_bytes()
        with self.assertRaises(FileExistsError):
            self.execute()
        self.assertEqual((self.job / 'STATUS.json').read_bytes(), prior_status)
        self.assertEqual(len(self.calls), 2)


if __name__ == '__main__':
    unittest.main()
