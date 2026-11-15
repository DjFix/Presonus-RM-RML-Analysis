"""Only a completed common barrier may retain packet-local failures."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from context_batch import Environment
from context_runtime import ContextError

ROOT = Path(__file__).resolve().parents[1]


class PartialFailureTests(unittest.TestCase):
    def exercise(self, action, barrier, packets=None):
        scratch = ROOT/'temp/test-work/context-partial'
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as folder:
            root = Path(folder)
            env = Environment(root, root)
            def command(argv, tag):
                receipt = {'action':action,'common_exit_seconds':barrier,
                           'receipts':[{'packet':p,'success':p!='bad','error':'failed' if p=='bad' else None}
                                       for p in (packets or ['good','bad'])]}
                (root/('selector-'+tag)/'batch-run-results-1.json').write_text(json.dumps(receipt))
                raise ContextError('process failed')
            with patch.object(env,'command',side_effect=command):
                return env.selector(action,['good','bad'],'test')

    def test_packet_error_after_successful_common_barrier_is_returned(self):
        result = self.exercise('prepare',0.1)
        self.assertEqual([x['packet'] for x in result],['bad'])

    def test_common_barrier_failure_is_fatal(self):
        with self.assertRaisesRegex(ContextError,'process failed'):
            self.exercise('prepare',None)

    def test_incomplete_receipt_is_fatal(self):
        with self.assertRaisesRegex(ContextError,'process failed'):
            self.exercise('prepare',0.1,['bad'])

    def test_final_validation_never_allows_partial_success(self):
        with self.assertRaisesRegex(ContextError,'process failed'):
            self.exercise('validate',0.1)


if __name__=='__main__':
    unittest.main()
