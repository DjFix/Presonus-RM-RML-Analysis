"""Snapshot guard optimization is an authenticated input shortcut, not proof reuse.

All fixtures live under project scratch. Canonical source symlinks emulate the
same inode seen at two bind-mount paths; frozen copies themselves stay regular.
"""
import copy
import json
import os
import pathlib
import sys
import unittest
import uuid
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'dependency-graph'))
import context_runtime as runtime
from context_runtime import ContextError, fingerprint, guard, inventory, sha


class SnapshotGuardTests(unittest.TestCase):
    def setUp(self):
        self.root = ROOT / 'temp/test-work/context-snapshot-guard' / uuid.uuid4().hex
        self.output = self.root / 'temp/recovery-work/batch'
        self.copy_root = self.output / 'snapshot'
        self.source = self.root / 'uc-library/src/input.cpp'
        self.source.parent.mkdir(parents=True)
        self.source.write_text('int frozen_original = 1;\n')
        self.relative = 'uc-library/src/input.cpp'
        self.state = {'files': {self.relative: {'sha256': sha(self.source),
                                              'fingerprint': fingerprint(self.source)}},
                      'source_inventory': inventory(self.root)}
        self.state_path = self.root / 'dependency-graph/state/generation.json'
        self.state_path.parent.mkdir(parents=True)
        self.state_path.write_text(json.dumps(self.state))
        self.active = {'state': 'dependency-graph/state/generation.json',
                       'state_sha256': sha(self.state_path)}
        self.copy = self.copy_root / self.relative
        self.copy.parent.mkdir(parents=True)
        self.copy.write_bytes(self.source.read_bytes())
        state_copy = self.copy_root / self.active['state']
        state_copy.parent.mkdir(parents=True)
        state_copy.write_bytes(self.state_path.read_bytes())
        self.manifest = {'version': 1, 'active': self.active,
                         'files': {self.relative: sha(self.copy), self.active['state']: sha(state_copy)},
                         'guard_fingerprints': {self.relative: fingerprint(self.copy),
                                                self.active['state']: fingerprint(state_copy)}}
        self.manifest_path = self.output / 'SNAPSHOT.json'
        self.manifest_path.write_text(json.dumps(self.manifest))
        self.environment = mock.patch.dict(os.environ, {
            'CONTEXT_SNAPSHOT_MANIFEST': str(self.manifest_path.relative_to(self.root)),
            'CONTEXT_SNAPSHOT_SHA256': sha(self.manifest_path)})
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def bind_receipt(self):
        self.manifest_path.write_text(json.dumps(self.manifest))
        os.environ['CONTEXT_SNAPSHOT_SHA256'] = sha(self.manifest_path)

    def mount_copy(self):
        retained = self.source.with_suffix('.retained')
        self.source.rename(retained)
        self.source.symlink_to(self.copy)

    def assert_rejected(self):
        with self.assertRaises((ContextError, OSError, ValueError)):
            guard(self.root, self.active)

    def test_samefile_pinned_copy_does_not_rehash_source_bytes(self):
        self.mount_copy()
        original_sha = runtime.sha
        def detect_source_hash(path):
            if pathlib.Path(path).resolve() == self.copy.resolve():
                self.fail('Fast path unnecessarily re-read frozen source bytes')
            return original_sha(path)
        with mock.patch.object(runtime, 'sha', side_effect=detect_source_hash):
            self.assertEqual(guard(self.root, self.active), self.state)

    def test_live_dirty_source_cannot_be_blessed_by_valid_snapshot_receipt(self):
        self.source.write_text('int live_dirty = 2;\n')
        self.assert_rejected()

    def test_unmounted_clean_source_falls_back_to_regular_hash_guard(self):
        # Touch changes the normal fingerprint. Samefile is false, so host bytes
        # still need a real current hash even though a valid receipt exists.
        os.utime(self.source, ns=(self.source.stat().st_atime_ns,
                                 self.source.stat().st_mtime_ns + 1000000))
        reads = []
        original_sha = runtime.sha
        def record(path):
            reads.append(pathlib.Path(path).resolve())
            return original_sha(path)
        with mock.patch.object(runtime, 'sha', side_effect=record):
            guard(self.root, self.active)
        self.assertIn(self.source.resolve(), reads)

    def test_wrong_receipt_hash_is_rejected(self):
        self.mount_copy()
        os.environ['CONTEXT_SNAPSHOT_SHA256'] = '0' * 64
        self.assert_rejected()

    def test_manifest_generation_and_expected_digest_changes_are_rejected(self):
        self.mount_copy()
        baseline = copy.deepcopy(self.manifest)
        for mutation in ['active', 'missing', 'digest', 'fp_shape']:
            with self.subTest(mutation=mutation):
                self.manifest = copy.deepcopy(baseline)
                if mutation == 'active': self.manifest['active']['state_sha256'] = '0' * 64
                if mutation == 'missing': self.manifest['files'].pop(self.relative)
                if mutation == 'digest': self.manifest['files'][self.relative] = '0' * 64
                if mutation == 'fp_shape': self.manifest['guard_fingerprints'][self.relative] = [1, 2]
                self.bind_receipt()
                self.assert_rejected()

    def test_valid_shaped_fingerprint_mismatch_falls_back_to_source_hash(self):
        self.mount_copy()
        self.manifest['guard_fingerprints'][self.relative][2] += 1
        self.bind_receipt()
        reads = []
        original_sha = runtime.sha
        def record(path):
            reads.append(pathlib.Path(path).resolve())
            return original_sha(path)
        with mock.patch.object(runtime, 'sha', side_effect=record):
            guard(self.root, self.active)
        self.assertIn(self.copy.resolve(), reads)

    def test_modified_and_replaced_copy_never_uses_old_fastpath(self):
        self.mount_copy()
        self.copy.write_text('int modified_copy = 9;\n')
        self.assert_rejected()
        replacement = self.copy.with_suffix('.replacement')
        replacement.write_text('int replaced_copy = 8;\n')
        replacement.replace(self.copy)
        self.assert_rejected()

    def test_snapshot_symlink_is_not_fastpath_eligible(self):
        # Links must never supply fingerprint-only trust, even with unchanged
        # bytes. Different bytes guarantee the normal guard rejects too.
        self.mount_copy()
        retained = self.copy.with_suffix('.retained')
        self.copy.rename(retained)
        retained.write_text('int untrusted_alias = 7;\n')
        self.copy.symlink_to(retained)
        self.assert_rejected()

    def test_hardlinked_copy_falls_back_to_source_hash(self):
        self.mount_copy()
        alias = self.copy.with_suffix('.alias')
        os.link(self.copy, alias)
        # Pin current metadata to ensure only nlink, not changed ctime, rejects
        # the shortcut. The fallback must still hash matching current bytes.
        self.manifest['guard_fingerprints'][self.relative] = fingerprint(self.copy)
        self.bind_receipt()
        reads = []
        original_sha = runtime.sha
        def record(path):
            reads.append(pathlib.Path(path).resolve())
            return original_sha(path)
        with mock.patch.object(runtime, 'sha', side_effect=record):
            guard(self.root, self.active)
        self.assertIn(self.copy.resolve(), reads)

    def test_missing_copy_and_incomplete_environment_reject(self):
        self.mount_copy()
        self.copy.rename(self.copy.with_suffix('.retained'))
        self.assert_rejected()
        for key in ['CONTEXT_SNAPSHOT_MANIFEST', 'CONTEXT_SNAPSHOT_SHA256']:
            with self.subTest(key=key), mock.patch.dict(os.environ):
                os.environ.pop(key)
                self.assert_rejected()

    def test_source_inventory_addition_and_removal_still_block(self):
        self.mount_copy()
        added = self.source.parent / 'added.cpp'
        added.write_text('int added;')
        self.assert_rejected()
        added.rename(added.with_suffix('.retained'))
        self.source.rename(self.source.with_suffix('.removed'))
        self.assert_rejected()

    def test_escape_absolute_and_malformed_receipts_fail_closed(self):
        self.mount_copy()
        for manifest_path in ['../SNAPSHOT.json', str(self.manifest_path), 'AGENTS.md']:
            with self.subTest(path=manifest_path):
                os.environ['CONTEXT_SNAPSHOT_MANIFEST'] = manifest_path
                self.assert_rejected()
        os.environ['CONTEXT_SNAPSHOT_MANIFEST'] = str(self.manifest_path.relative_to(self.root))
        self.manifest_path.write_text('{malformed')
        os.environ['CONTEXT_SNAPSHOT_SHA256'] = sha(self.manifest_path)
        self.assert_rejected()

    def test_environment_unset_retains_canonical_live_guard(self):
        with mock.patch.dict(os.environ):
            os.environ.pop('CONTEXT_SNAPSHOT_MANIFEST', None)
            os.environ.pop('CONTEXT_SNAPSHOT_SHA256', None)
            guard(self.root, self.active)
            self.source.write_text('int stale_host;')
            self.assert_rejected()


if __name__ == '__main__':
    unittest.main()
