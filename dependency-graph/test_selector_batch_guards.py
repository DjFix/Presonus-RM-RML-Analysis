"""Batch entry/exit guards stay mandatory, including failed mutation barriers."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from context_runtime import ContextError

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('tested_batch_selector', ROOT/'dependency-graph/context_selector.py')
selector = importlib.util.module_from_spec(spec)
with patch.dict(sys.modules, {'neo4j': SimpleNamespace(GraphDatabase=MagicMock())}):
    spec.loader.exec_module(selector)


class BatchGuardTests(unittest.TestCase):
    def setUp(self):
        scratch = ROOT/'temp/test-work/selector-batch-guards'
        scratch.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.active = self.root/'ACTIVE.json'
        self.active.write_text('{"state_sha256":"generation"}')
        self.out = self.root/'run'
        self.out.mkdir()
        self.paths = ['packet_a', 'packet_b', 'packet_c']
        (self.out/'batch-run.json').write_text(json.dumps({'action':'finalize', 'packets':self.paths}))

    def run_batch(self, operation, guard):
        work = MagicMock()
        state = {'files': {}}
        with patch.object(selector, 'ROOT', self.root), patch.object(selector, 'ACTIVE', self.active), \
             patch.object(selector, 'guard', guard), patch.object(selector, 'tools', return_value={'tool':'digest'}), \
             patch.object(selector, 'graph_marker'), patch.object(selector, 'memgraph_uri', return_value='bolt://test'), \
             patch.object(selector, 'finalize', side_effect=operation), \
             patch('context_work_batch.BatchWorkValidator', return_value=work), \
             patch.object(sys, 'argv', ['selector', 'batch-run', '--out', 'run']):
            selector._main()
        return work

    def test_common_state_used_by_every_packet_with_two_full_guards(self):
        seen = []
        guard = MagicMock(return_value={'files':{}})
        work = self.run_batch(lambda *args, common: seen.append(common), guard)
        self.assertEqual(guard.call_count, 2)
        self.assertEqual(len(seen), 3)
        self.assertTrue(all(common is seen[0] for common in seen))
        self.assertIs(seen[0]['work'], work)
        work.finish.assert_called_once()
        work.close.assert_called_once()

    def test_common_state_does_not_skip_selected_source_hash_checks(self):
        (self.root/'packet').mkdir()
        (self.root/'AGENTS.md').write_text('policy')
        source = self.root/'source.cpp'
        source.write_text('original')
        packet = {'state':'selected', 'task_id':'packet', 'tool_sha256':{'tool':'digest'},
                  'generation_sha256':'generation', 'packet_sha256':{},
                  'selected_file_sha256':{'source.cpp':selector.sha(source)},
                  'agents_sha256':selector.sha(self.root/'AGENTS.md')}
        (self.root/'packet/context.json').write_text(json.dumps(packet))
        common = {'state':{'files':{}},'tools':{'tool':'digest'},'work':MagicMock()}
        with patch.object(selector,'ROOT',self.root), patch.object(selector,'graph_marker'):
            selector.validate_packet(MagicMock(),self.root/'packet',{'state_sha256':'generation'},
                                     require_ready=False,common=common)
            source.write_text('modified')
            with self.assertRaisesRegex(ContextError,'Reading input changed'):
                selector.validate_packet(MagicMock(),self.root/'packet',{'state_sha256':'generation'},
                                         require_ready=False,common=common)

    def test_packet_failure_does_not_skip_remaining_independent_packets(self):
        seen = []
        def operation(session, output, active, common):
            seen.append(output.name)
            if output.name == 'packet_b':
                raise ContextError('packet-local failure')
        guard = MagicMock(return_value={'files':{}})
        with self.assertRaisesRegex(ContextError,'common barrier passed'):
            self.run_batch(operation, guard)
        self.assertEqual(seen,self.paths)
        self.assertEqual(guard.call_count,2)
        receipt = json.loads(next(self.out.glob('batch-run-results-*.json')).read_text())
        self.assertIsNotNone(receipt['common_exit_seconds'])
        self.assertEqual([r['success'] for r in receipt['receipts']],[True,False,True])

    def test_generation_switch_during_work_rejected(self):
        def operation(*args, **kwargs):
            self.active.write_text('{"state_sha256":"replacement"}')
        with self.assertRaisesRegex(ContextError, 'generation changed'):
            self.run_batch(operation, MagicMock(return_value={'files':{}}))

    def test_final_full_guard_failure_cannot_report_success(self):
        guard = MagicMock(side_effect=[{'files':{}}, ContextError('Graph is stale')])
        with self.assertRaisesRegex(ContextError, 'stale'):
            self.run_batch(lambda *args, **kwargs: None, guard)
        receipt = json.loads(next(self.out.glob('batch-run-results-*.json')).read_text())
        self.assertIsNone(receipt['common_exit_seconds'])


if __name__ == '__main__':
    unittest.main()
