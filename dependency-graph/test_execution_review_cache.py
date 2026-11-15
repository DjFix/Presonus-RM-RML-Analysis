"""Invocation-local reuse must preserve exact identity and mutation rejection."""
import copy
import json
import os
from unittest import mock
import unittest

import execution_review as gate
from test_execution_review import ExecutionReviewTests


class BatchExecutionReviewTests(ExecutionReviewTests):
    def test_repeated_reviews_scan_native_once_and_hash_once(self):
        with mock.patch.object(gate, '_node_identities', wraps=gate._node_identities) as scan:
            with gate.batch_validation(self.root) as session:
                for _ in range(4):
                    self.assertEqual(gate.validate(self.root, self.task, self.review)['observations'], 3)
                self.assertEqual(scan.call_count, 1)
                self.assertEqual(len(session.cache.files), 1)
        # A fresh invocation cannot inherit that lookup or byte verification.
        with mock.patch.object(gate, '_node_identities', wraps=gate._node_identities) as scan:
            with gate.batch_validation(self.root):
                gate.validate(self.root, self.task, self.review)
            self.assertEqual(scan.call_count, 1)

    def test_changed_bytes_with_restored_mtime_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'evidence changed'):
            with gate.batch_validation(self.root):
                gate.validate(self.root, self.task, self.review)
                observed = self.database.stat()
                with self.database.open('r+b') as stream:
                    stream.seek(-1, 2)
                    value = stream.read(1)
                    stream.seek(-1, 2)
                    stream.write(bytes([value[0] ^ 1]))
                os.utime(self.database, ns=(observed.st_atime_ns, observed.st_mtime_ns))
                gate.validate(self.root, self.task, self.review)

    def test_replaced_database_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'evidence changed'):
            with gate.batch_validation(self.root):
                gate.validate(self.root, self.task, self.review)
                replacement = self.root / 'replacement.sqlite'
                replacement.write_bytes(self.database.read_bytes())
                replacement.replace(self.database)
                gate.validate(self.root, self.task, self.review)

    def test_retargeted_symlink_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'path changed'):
            original = self.root / 'original.sqlite'
            self.database.rename(original)
            self.database.symlink_to(original)
            with gate.batch_validation(self.root):
                gate.validate(self.root, self.task, self.review)
                replacement = self.root / 'replacement.sqlite'
                replacement.write_bytes(original.read_bytes())
                self.database.unlink()
                self.database.symlink_to(replacement)
                gate.validate(self.root, self.task, self.review)

    def test_native_pointer_switch_is_rejected_even_for_identical_bytes(self):
        with gate.batch_validation(self.root):
            gate.validate(self.root, self.task, self.review)
            replacement = self.root / 'replacement.sqlite'
            replacement.write_bytes(self.database.read_bytes())
            pointer = self.root / 'dependency-graph/NATIVE_ACTIVE.json'
            active = json.loads(pointer.read_text())
            active['database'] = 'replacement.sqlite'
            pointer.write_text(json.dumps(active))
            with self.assertRaisesRegex(ValueError, 'generation changed within batch'):
                gate.validate(self.root, self.task, self.review)

    def test_cached_lookup_still_rejects_missing_observations_and_targets(self):
        with gate.batch_validation(self.root):
            gate.validate(self.root, self.task, self.review)
            broken = copy.deepcopy(self.review)
            broken['execution_boundary_review']['observations'].pop()
            with self.assertRaisesRegex(ValueError, 'exact direct/tail'):
                gate.validate(self.root, self.task, broken)
            target = copy.deepcopy(self.task)
            target['targets'][0]['size'] += 1
            with self.assertRaisesRegex(ValueError, 'Exact native target/range'):
                gate.validate(self.root, target, self.review)

    def test_final_guard_rejects_change_without_another_review(self):
        with self.assertRaisesRegex(ValueError, 'evidence changed'):
            with gate.batch_validation(self.root):
                gate.validate(self.root, self.task, self.review)
                self.database.write_bytes(self.database.read_bytes() + b'changed')

    def test_cached_typed_evidence_keeps_kind_and_scope_checks(self):
        from reconstruction_contract import evidence
        with gate.batch_validation(self.root) as session:
            evidence(self.root, [self.evidence])
            invalid = dict(self.evidence, kind='invented')
            with self.assertRaisesRegex(ValueError, 'Typed evidence kind'):
                evidence(self.root, [invalid])
            with self.assertRaisesRegex(ValueError, 'Evidence scope'):
                evidence(self.root, [dict(self.evidence, scope='')])
            self.assertEqual(len(session.cache.files), 1)


if __name__ == '__main__':
    unittest.main()
