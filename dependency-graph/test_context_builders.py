"""Pre-slice builder integration tests; synthetic data is not firmware evidence."""
import hashlib
import json
from pathlib import Path
import tempfile
import threading
import unittest

from context_batch import _build_packet
from early_conflicts import EarlyConflict, SelectedReadGuard

ROOT = Path(__file__).resolve().parents[1]
GENERATION = 'a'*64


class Environment:
    def __init__(self, root, requests, reads):
        self.root, self.requests, self.reads = root, requests, reads
        self.events = []
        self.on_prepare = None

    def selector(self, action, packets, label):
        packet = packets[0]
        self.events.append(action)
        path = self.root/packet/'context.json'
        if action == 'prepare':
            request = self.requests[packet]
            context = {'state': 'selected', 'task_id': request['task_id'],
                'generation_sha256': GENERATION,
                'task_sha256': hashlib.sha256((self.root/packet/'request.json').read_bytes()).hexdigest(),
                'work_binding': request['work_binding'],
                'selected_file_sha256': {p: 'b'*64 for p in self.reads[packet]}}
            path.write_text(json.dumps(context))
            if self.on_prepare:
                self.on_prepare()
        elif action == 'finalize':
            context = json.loads(path.read_text())
            context['state'] = 'dispatch_ready'
            path.write_text(json.dumps(context))
        else:
            raise AssertionError(action)

    def slice(self, packet, label):
        self.events.append('slice')
        (self.root/packet/'source-slices.json').write_text('{}')


class BuilderTests(unittest.TestCase):
    def setUp(self):
        scratch = ROOT/'temp/test-work/context-builders'
        scratch.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.requests = {}
        for name in ('task_a', 'task_b'):
            packet = 'packets/'+name
            request = {'task_id': name, 'mode': 'reconstruct',
                'owned_files': ['uc-library/src/'+name+'.cpp'],
                'work_binding': {'work_item_id': name}}
            self.requests[packet] = request
            directory = self.root/packet
            directory.mkdir(parents=True)
            (directory/'request.json').write_text(json.dumps(request))
        self.packet = 'packets/task_a'
        self.stopped = threading.Event()

    def guard(self, groups=None):
        hashes = {p: hashlib.sha256((self.root/p/'request.json').read_bytes()).hexdigest()
                  for p in self.requests}
        return SelectedReadGuard(self.requests, GENERATION, hashes, groups)

    def build(self, environment, callback, slicing=None):
        return _build_packet(self.root, self.packet, environment, threading.Semaphore(1),
            slicing or threading.Semaphore(1), callback, self.stopped)

    def test_real_guard_rejects_selected_conflict_before_slice(self):
        environment = Environment(self.root, self.requests,
            {self.packet: ['uc-library/src/task_b.cpp']})
        guard = self.guard()
        with self.assertRaises(EarlyConflict) as caught:
            self.build(environment, lambda p, c: guard.check(p, c, self.requests[p]))
        self.assertEqual(caught.exception.detail['reason'], 'selected_read_planned_write_overlap')
        self.assertEqual(environment.events, ['prepare'])
        self.assertFalse((self.root/self.packet/'source-slices.json').exists())

    def test_success_keeps_prepare_check_slice_finalize_order(self):
        environment = Environment(self.root, self.requests, {self.packet: ['uc-library/src/borrowed.cpp']})
        guard = self.guard()
        def check(packet, context):
            environment.events.append('check')
            result = guard.check(packet, context, self.requests[packet])
            self.assertFalse(result['dispatch_authorized'])
        self.assertTrue(self.build(environment, check))
        self.assertEqual(environment.events, ['prepare', 'check', 'slice', 'finalize'])

    def test_same_owner_overlap_remains_permitted(self):
        environment = Environment(self.root, self.requests, {self.packet: ['uc-library/src/task_b.cpp']})
        groups = [{'task_name': 'one_owner', 'packets': list(self.requests)}]
        guard = self.guard(groups)
        self.assertTrue(self.build(environment, lambda p, c: guard.check(p, c, self.requests[p])))
        self.assertIn('slice', environment.events)

    def test_stopped_queued_builder_does_no_selection_or_slice(self):
        environment = Environment(self.root, self.requests, {})
        self.stopped.set()
        self.assertFalse(self.build(environment, lambda *_: self.fail('check after stop')))
        self.assertEqual(environment.events, [])

    def test_stop_after_selection_prevents_slice(self):
        environment = Environment(self.root, self.requests, {self.packet: ['uc-library/src/borrowed.cpp']})
        environment.on_prepare = self.stopped.set
        self.assertFalse(self.build(environment, lambda *_: self.fail('check after stop')))
        self.assertEqual(environment.events, ['prepare'])

    def test_stop_while_waiting_slice_does_not_launch_ast(self):
        environment = Environment(self.root, self.requests, {self.packet: ['uc-library/src/borrowed.cpp']})
        entered = threading.Event()
        slicing = threading.Semaphore(0)
        results = []
        def check(*_):
            entered.set()
        worker = threading.Thread(target=lambda: results.append(self.build(environment, check, slicing)))
        worker.start()
        self.assertTrue(entered.wait(5))
        self.stopped.set()
        slicing.release()
        worker.join(5)
        self.assertFalse(worker.is_alive())
        self.assertEqual(results, [False])
        self.assertEqual(environment.events, ['prepare'])

    def test_existing_slice_still_checks_before_finalize(self):
        environment = Environment(self.root, self.requests, {self.packet: ['uc-library/src/borrowed.cpp']})
        environment.selector('prepare', [self.packet], 'initial')
        (self.root/self.packet/'source-slices.json').write_text('{}')
        environment.events.clear()
        self.assertTrue(self.build(environment, lambda *_: environment.events.append('check')))
        self.assertEqual(environment.events, ['check', 'finalize'])

    def test_ready_packet_is_checked_without_rebuilding(self):
        environment = Environment(self.root, self.requests, {self.packet: ['uc-library/src/borrowed.cpp']})
        environment.selector('prepare', [self.packet], 'initial')
        environment.selector('finalize', [self.packet], 'initial')
        environment.events.clear()
        guard = self.guard()
        self.assertTrue(self.build(environment, lambda p, c: guard.check(p, c, self.requests[p])))
        self.assertEqual(environment.events, [])


if __name__ == '__main__':
    unittest.main()
