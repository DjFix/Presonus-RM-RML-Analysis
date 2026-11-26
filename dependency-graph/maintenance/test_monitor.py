"""Offline fixtures only; never queries systemd, DB, graph or live job."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).parent
WORK = HERE.resolve().parents[1] / 'temp/test-work/graph-maintenance-monitor'
WORK.mkdir(parents=True, exist_ok=True)
spec = importlib.util.spec_from_file_location('graph_monitor', HERE / 'monitor.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class StatusFixtures(unittest.TestCase):
    def props(self, active='inactive', sub='dead', **extra):
        return dict(LoadState='loaded', ActiveState=active, SubState=sub,
                    ExecMainCode='0', ExecMainStatus='0', Result='success', **extra)

    def test_missing_is_not_started(self):
        self.assertEqual(m.classify(m.parse_show('LoadState=not-found\n'), 4), ('not_started', False))

    def test_query_failure_never_terminal(self):
        self.assertEqual(m.classify({}, None), ('unknown', False))
        self.assertEqual(m.classify(self.props(), 1), ('unknown', False))
        self.assertEqual(m.classify({'LoadState': 'error'}, 0), ('unknown', False))

    def test_default_exit_zero_is_not_completion(self):
        self.assertEqual(m.classify(self.props(), 0), ('not_started', False))

    def test_active_and_transition(self):
        self.assertEqual(m.classify(self.props('active', 'running'), 0), ('running', False))
        self.assertEqual(m.classify(self.props('deactivating', 'stop'), 0), ('deactivating', False))

    def test_actual_finished_and_failure(self):
        p = self.props(ExecMainExitTimestamp='Thu 2026-11-26 21:00:00 UTC', InvocationID='a')
        p['ExecMainCode'] = '1'
        self.assertEqual(m.classify(p, 0), ('finished', True))
        p['ExecMainStatus'] = '9'
        p['Result'] = 'exit-code'
        self.assertEqual(m.classify(p, 0), ('failed', True))
        self.assertEqual(m.classify(self.props('failed', 'failed'), 0), ('failed', True))

    def test_instance_binding_blocks_old_terminal(self):
        self.assertEqual(m.bind_instance({'InvocationID': 'old'}, 'finished', True, 'new'), ('instance_mismatch', False, False))
        self.assertEqual(m.bind_instance({'InvocationID': 'old'}, 'finished', True, None), ('unbound_finished', False, False))
        self.assertEqual(m.bind_instance({'InvocationID': 'new'}, 'finished', True, 'new'), ('finished', True, True))

    def test_atomic_latest_and_terminal_survives_unknown(self):
        with tempfile.TemporaryDirectory(dir=WORK, prefix='offline-fixture-') as folder:
            p = Path(folder)
            m.persist(p, {'state': 'finished', 'terminal': True, 'systemd': {'InvocationID': 'fixture'}})
            m.persist(p, {'state': 'unknown', 'terminal': False})
            self.assertEqual(json.loads((p / 'LATEST.json').read_text())['state'], 'unknown')
            self.assertEqual(json.loads((p / 'TERMINAL.json').read_text())['state'], 'finished')
            self.assertEqual(len((p / 'HOURLY.jsonl').read_text().splitlines()), 2)


if __name__ == '__main__':
    unittest.main()
