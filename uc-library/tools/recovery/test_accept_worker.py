"""Boundary checks for worker acceptance; no firmware or registry mutations."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

import accept_worker as worker


class AcceptanceTests(unittest.TestCase):
    def setUp(self):
        scratch = worker.ROOT / 'temp/test-work'
        scratch.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        artifact = self.base / 'bound.txt'
        artifact.write_text('fixture')
        relative = str(artifact.relative_to(worker.ROOT))
        artifacts = []
        for kind in ('source', 'test', 'fixture', 'replay', 'proof'):
            p = self.base / kind
            p.write_text(kind)
            artifacts.append(dict(kind=kind, path=str(p.relative_to(worker.ROOT)),
                                  sha256=worker.digest(p)))
        artifacts.append(dict(kind='packet', path=relative, sha256=worker.digest(artifact)))
        self.data = dict(version=1, task_id='test', namespace='Test',
                         packet_manifest=relative, validation_domain='bounded',
                         limitations=['not semantic proof'], build_integration={'partition': 'common'},
                         originals=[dict(elf_sha256='a'*64, firmware='test', role='client',
                                         mangled='_Ztest', address=0, size=4, section='.text')],
                         artifacts=artifacts,
                         checks=[dict(kind=k, argv=[sys.executable, '-c', 'pass'], timeout_seconds=10)
                                 for k in ('format', 'compile', 'symbols', 'replay')])

    def run_accept(self, data):
        manifest = self.base / 'HANDOFF.json'
        manifest.write_text(json.dumps(data))
        return worker.accept(manifest, self.base / 'out')

    def test_success_is_not_admission(self):
        result = self.run_accept(self.data)
        self.assertTrue(result['local_acceptance_passed'])
        self.assertFalse(result['readiness_admitted'])
        self.assertEqual(len(result['checks']), 4)

    def test_stale_fixture_rejected(self):
        (self.base / 'fixture').write_text('changed')
        with self.assertRaisesRegex(ValueError, 'Stale artifact'):
            self.run_accept(self.data)

    def test_failure_is_logged_and_stops(self):
        self.data['checks'][0]['argv'] = [sys.executable, '-c', 'raise SystemExit(7)']
        with self.assertRaisesRegex(ValueError, 'Check failed'):
            self.run_accept(self.data)
        result = json.loads((self.base / 'out/acceptance.json').read_text())
        self.assertFalse(result['local_acceptance_passed'])
        self.assertEqual(len(result['checks']), 1)
        self.assertEqual(result['checks'][0]['returncode'], 7)

    def test_changed_input_after_replay_rejected(self):
        self.data['checks'][-1]['argv'] = [sys.executable, '-c',
            'from pathlib import Path; Path(' + repr(str(self.base / 'fixture')) + ').write_text("changed")']
        with self.assertRaisesRegex(ValueError, 'Stale artifact'):
            self.run_accept(self.data)

    def test_missing_check_or_oracle_rejected(self):
        for field in ('checks', 'originals'):
            data = copy.deepcopy(self.data)
            data[field] = []
            with self.assertRaises(ValueError):
                worker.validate(data)

    def test_escape_rejected(self):
        for value in ('../outside', '/etc/passwd'):
            with self.assertRaises(ValueError):
                worker.inside(value)


if __name__ == '__main__':
    unittest.main()
