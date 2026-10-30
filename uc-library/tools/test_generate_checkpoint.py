"""Checkpoint consumer checks; all fixtures remain in project temp/."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import generate_checkpoint as checkpoint

ROOT = Path(__file__).resolve().parents[2]


class CheckpointTests(unittest.TestCase):
    def setUp(self):
        base = ROOT / 'temp' / 'checkpoint-tests'
        base.mkdir(parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=base)
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.library = self.root / 'uc-library'
        (self.library / 'validation').mkdir(parents=True)
        log = self.root / 'test.log'
        log.write_text('passing\n')
        self.integration = dict(platform='linux', ctest_passed=True,
                                test_log='test.log', test_log_sha256=checkpoint.sha256(log), test_suites=321)
        self.write_integration()
        self.ready = [dict(original_elf_sha256='elf', mangled='_ZN1A1fEv', role='client')]
        self.pending = [dict(original_elf_sha256='elf', mangled='_ZN1A1gEv')]
        outer = self
        class FakeSnapshot:
            def __init__(self, db): self.db = db
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def load_registry(self, status):
                return {'functions': outer.ready if status == 'ready' else outer.pending}
            def provenance(self): return {'database': 'fixture', 'snapshot': 'readonly'}
        self.patch = patch.object(checkpoint, 'RegistrySnapshot', FakeSnapshot)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.resolve = patch.object(checkpoint, 'resolve_db', return_value=self.root / 'fixture.sqlite')
        self.resolve.start()
        self.addCleanup(self.resolve.stop)

    def write_integration(self):
        (self.library / 'validation' / 'integration.json').write_text(json.dumps(self.integration))

    def test_counts_identities_and_provenance_without_json_ledgers(self):
        result = checkpoint.snapshot(self.library, self.root, 'test')
        self.assertEqual(result['ready_entries'], 1)
        self.assertEqual(result['declaration_pending_entries'], 1)
        self.assertEqual(result['roles'], {'client': 1})
        self.assertEqual(result['ready_identities'], [['elf', '_ZN1A1fEv']])
        self.assertEqual(result['registry']['snapshot'], 'readonly')
        self.assertEqual(len(result['inputs']), 1)

    def test_duplicate_and_overlap_rejected(self):
        self.ready.append(self.ready[0].copy())
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            checkpoint.snapshot(self.library, self.root, 'test')
        self.ready.pop()
        self.pending[:] = self.ready
        with self.assertRaisesRegex(ValueError, 'overlap'):
            checkpoint.snapshot(self.library, self.root, 'test')

    def test_integration_and_log_guards(self):
        self.integration['platform'] = 'darwin'
        self.write_integration()
        with self.assertRaisesRegex(ValueError, 'Linux'):
            checkpoint.snapshot(self.library, self.root, 'test')
        self.integration['platform'] = 'linux'
        self.integration['test_log_sha256'] = 'wrong'
        self.write_integration()
        with self.assertRaisesRegex(ValueError, 'hash/path'):
            checkpoint.snapshot(self.library, self.root, 'test')
        outside = self.root.parent / 'outside.log'
        self.integration['test_log'] = str(outside)
        self.write_integration()
        with self.assertRaisesRegex(ValueError, 'hash/path'):
            checkpoint.snapshot(self.library, self.root, 'test')


if __name__ == '__main__':
    unittest.main()
