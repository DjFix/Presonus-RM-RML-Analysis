"""Real batching, independent slicing, conflict-before-AST and resumability."""
import json
from pathlib import Path
import tempfile
import unittest
from context_batch import build_packets
from context_runtime import ContextError

ROOT = Path(__file__).resolve().parents[1]


class Environment:
    def __init__(self, root):
        self.root = root
        self.calls = []
        self.fail_slice = None

    def selector(self, action, packets, tag):
        self.calls.append((action, tuple(packets)))
        for packet in packets:
            path = self.root / packet / 'context.json'
            value = {'state': 'selected'} if action == 'prepare' else json.loads(path.read_text())
            if action == 'finalize':
                value['state'] = 'dispatch_ready'
            path.write_text(json.dumps(value))

    def slice(self, packet, tag):
        self.calls.append(('slice', (packet,)))
        if packet == self.fail_slice:
            raise ValueError('bad AST')
        (self.root / packet / 'source-slices.json').write_text('{}')


class BatchStagesTests(unittest.TestCase):
    def setUp(self):
        scratch = ROOT / 'temp/test-work/context-stages'
        scratch.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.packets = ['packets/a', 'packets/b', 'packets/c']
        for packet in self.packets:
            (self.root / packet).mkdir(parents=True)
        self.env = Environment(self.root)

    def test_two_selector_calls_for_whole_group(self):
        checked = []
        build_packets(self.root, self.packets, self.env, lambda p, c: checked.append(p), 2)
        selectors = [call for call in self.env.calls if call[0] != 'slice']
        self.assertEqual(selectors, [('prepare', tuple(self.packets)), ('finalize', tuple(self.packets))])
        self.assertEqual(checked, self.packets)

    def test_conflicting_packet_is_parked_before_its_slice(self):
        def conflict(packet, context):
            if packet == self.packets[-1]:
                raise ContextError('overlap')
        with self.assertRaisesRegex(ContextError, 'overlap'):
            build_packets(self.root, self.packets, self.env, conflict, 2)
        self.assertNotIn(('slice', (self.packets[-1],)), self.env.calls)
        self.assertIn(('finalize', tuple(self.packets[:2])), self.env.calls)

    def test_failed_slice_does_not_cancel_independent_packets_and_resume_reuses_them(self):
        self.env.fail_slice = self.packets[1]
        with self.assertRaisesRegex(ContextError, 'independent packets finalized'):
            build_packets(self.root, self.packets, self.env, lambda *_: None, 2)
        for packet in (self.packets[0], self.packets[2]):
            self.assertEqual(json.loads((self.root/packet/'context.json').read_text())['state'], 'dispatch_ready')
        self.env.calls.clear()
        self.env.fail_slice = None
        build_packets(self.root, self.packets, self.env, lambda *_: None, 2)
        self.assertEqual(self.env.calls, [('slice', (self.packets[1],)), ('finalize', (self.packets[1],))])

    def test_partial_selection_is_not_silently_overwritten(self):
        (self.root/self.packets[1]/'TASK.md').write_text('retained')
        with self.assertRaisesRegex(ContextError, 'Interrupted selection'):
            build_packets(self.root, self.packets, self.env, lambda *_: None, 2)
        self.assertEqual(self.env.calls, [])


if __name__ == '__main__':
    unittest.main()
