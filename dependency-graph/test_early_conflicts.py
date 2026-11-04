"""Pure guard regressions; no graph, claims, processes or AST runs."""
import copy
from concurrent.futures import ThreadPoolExecutor
import threading
import unittest

from early_conflicts import EarlyConflict, SelectedReadGuard

GEN = 'a' * 64
HASH = 'b' * 64


def request(ident, owned):
    return {'task_id': ident, 'mode': 'reconstruct', 'owned_files': owned,
            'work_binding': {'work_item_id': 'work-' + ident}}


def context(ident, reads):
    return {'task_id': ident, 'state': 'selected', 'generation_sha256': GEN,
            'task_sha256': HASH, 'work_binding': {'work_item_id': 'work-' + ident},
            'selected_file_sha256': {path: HASH for path in reads}}


class EarlyConflictTests(unittest.TestCase):
    def setUp(self):
        self.requests = {'packets/a': request('a', ['src/a.cpp']),
                         'packets/b': request('b', ['src/b.cpp'])}
        self.hashes = {p: HASH for p in self.requests}

    def guard(self, groups=None):
        return SelectedReadGuard(self.requests, GEN, self.hashes, groups)

    def test_first_offender_rejected_before_slice(self):
        called = []
        with self.assertRaises(EarlyConflict) as caught:
            self.guard().check('packets/a', context('a', ['src/b.cpp']), self.requests['packets/a'])
            called.append('slice')
        self.assertEqual(called, [])
        self.assertEqual(caught.exception.detail['writer_packet'], 'packets/b')
        self.assertEqual(caught.exception.detail['packet'], 'packets/a')
        self.assertEqual(caught.exception.detail['read_path'], 'src/b.cpp')

    def test_success_is_not_independence(self):
        out = self.guard().check('packets/a', context('a', ['src/a.cpp']), self.requests['packets/a'])
        self.assertEqual(out['outcome'], 'no_known_selected_overlap')
        self.assertFalse(out['independence_proven'])
        self.assertFalse(out['dispatch_authorized'])

    def test_same_group_owner_overlap_allowed(self):
        groups = [{'task_name': 'both', 'packets': list(self.requests)}]
        self.guard(groups).check('packets/a', context('a', ['src/b.cpp']), self.requests['packets/a'])

    def test_planned_write_conflict_before_selection(self):
        self.requests['packets/b']['owned_files'] = ['src/a.cpp']
        with self.assertRaisesRegex(EarlyConflict, 'planned_write_write_overlap'):
            self.guard()

    def test_read_only_audit_and_research(self):
        for mode in ['audit', 'research']:
            with self.subTest(mode=mode):
                self.requests['packets/a'].update(mode=mode, owned_files=[])
                out = self.guard().check('packets/a', context('a', ['src/a.cpp']), self.requests['packets/a'])
                self.assertEqual(out['outcome'], 'no_known_selected_overlap')
                self.assertFalse(out['independence_proven'])
                self.assertFalse(out['dispatch_authorized'])
                with self.assertRaisesRegex(EarlyConflict, 'selected_read_planned_write_overlap'):
                    self.guard().check('packets/a', context('a', ['src/b.cpp']), self.requests['packets/a'])

    def test_reconstruct_empty_and_audit_writes_rejected(self):
        self.requests['packets/a']['owned_files'] = []
        with self.assertRaisesRegex(EarlyConflict, 'missing_owned_files'):
            self.guard()
        self.requests['packets/a'].update(mode='audit', owned_files=['src/a.cpp'])
        with self.assertRaisesRegex(EarlyConflict, 'audit_must_be_read_only'):
            self.guard()

    def test_duplicate_owned_paths_are_benign_without_request_rewrite(self):
        self.requests['packets/a']['owned_files'].append('src/a.cpp')
        before = copy.deepcopy(self.requests)
        guard = self.guard()
        guard.check('packets/a', context('a', ['src/a.cpp']), self.requests['packets/a'])
        self.assertEqual(before, self.requests)
        with self.assertRaisesRegex(EarlyConflict, 'selected_read_planned_write_overlap'):
            self.guard().check('packets/b', context('b', ['src/a.cpp']), self.requests['packets/b'])
        self.requests['packets/a']['owned_files'].pop()
        with self.assertRaisesRegex(EarlyConflict, 'request_changed_after_planning'):
            self.guard_from_snapshot(before).check('packets/a', context('a', ['src/a.cpp']), self.requests['packets/a'])

    def guard_from_snapshot(self, requests):
        return SelectedReadGuard(requests, GEN, self.hashes)

    def test_current_generation_required(self):
        for generation in [None, 'old', 'c' * 64]:
            entry = context('a', ['src/a.cpp'])
            entry['generation_sha256'] = generation
            with self.subTest(generation=generation), self.assertRaisesRegex(EarlyConflict, 'mixed_or_unknown_generation'):
                self.guard().check('packets/a', entry, self.requests['packets/a'])

    def test_missing_or_malformed_reads_rejected(self):
        for reads in [None, {}, ['src/b.cpp'], {'src/a.cpp': 'bad'}, {'../escape': HASH}, {None: HASH, 'src/a.cpp': HASH}]:
            entry = context('a', ['src/a.cpp'])
            entry['selected_file_sha256'] = reads
            with self.subTest(reads=reads), self.assertRaises(EarlyConflict):
                self.guard().check('packets/a', entry, self.requests['packets/a'])

    def test_unknown_foreign_or_duplicate_packet(self):
        with self.assertRaisesRegex(EarlyConflict, 'unknown_packet'):
            self.guard().check('packets/foreign', context('a', ['src/a.cpp']), self.requests['packets/a'])
        with self.assertRaisesRegex(EarlyConflict, 'foreign_context_task'):
            self.guard().check('packets/a', context('b', ['src/a.cpp']), self.requests['packets/a'])
        guard = self.guard()
        guard.check('packets/a', context('a', ['src/a.cpp']), self.requests['packets/a'])
        with self.assertRaisesRegex(EarlyConflict, 'duplicate_selected_packet'):
            guard.check('packets/a', context('a', ['src/a.cpp']), self.requests['packets/a'])

    def test_changed_live_request_rejected(self):
        guard = self.guard()
        self.requests['packets/a']['owned_files'].append('src/added.cpp')
        with self.assertRaisesRegex(EarlyConflict, 'request_changed_after_planning'):
            guard.check('packets/a', context('a', ['src/a.cpp']), self.requests['packets/a'])

    def test_foreign_request_hash_or_work_rejected(self):
        for field, value, reason in [('task_sha256', 'c' * 64, 'context_request_hash_mismatch'),
                                     ('work_binding', {'work_item_id': 'other'}, 'context_unique_work_mismatch')]:
            entry = context('a', ['src/a.cpp'])
            entry[field] = value
            with self.subTest(field=field), self.assertRaisesRegex(EarlyConflict, reason):
                self.guard().check('packets/a', entry, self.requests['packets/a'])

    def test_group_coverage_duplicates_and_paths_rejected(self):
        bad_groups = [[{'task_name': 'one', 'packets': ['packets/a']}],
                      [{'task_name': 'one', 'packets': ['packets/a', 'packets/a']}],
                      [{'task_name': 'one', 'packets': ['packets/a', 'packets/foreign']}]]
        for groups in bad_groups:
            with self.subTest(groups=groups), self.assertRaises(EarlyConflict):
                self.guard(groups)
        for path in ['../outside', './src/a', '/root', 'src//a']:
            bad = copy.deepcopy(self.requests)
            bad['packets/a']['owned_files'] = [path]
            with self.subTest(path=path), self.assertRaises(EarlyConflict):
                SelectedReadGuard(bad, GEN, self.hashes)
        bad = copy.deepcopy(self.requests)
        bad['packets/b']['work_binding'] = bad['packets/a']['work_binding']
        with self.assertRaisesRegex(EarlyConflict, 'duplicate_unique_work'):
            SelectedReadGuard(bad, GEN, self.hashes)

    def test_concurrent_first_conflict_is_latched(self):
        guard = self.guard()
        barrier = threading.Barrier(2)
        def check(ident, other):
            barrier.wait(timeout=5)
            try:
                guard.check('packets/' + ident, context(ident, ['src/' + other + '.cpp']), self.requests['packets/' + ident])
            except EarlyConflict as error:
                return error.detail
            self.fail('Conflict did not reject')
        with ThreadPoolExecutor(max_workers=2) as pool:
            a = pool.submit(check, 'a', 'b')
            b = pool.submit(check, 'b', 'a')
            first, second = a.result(), b.result()
        self.assertEqual(first, second)
        self.assertEqual(first, guard.first_failure)
        first['packet'] = 'mutated'
        self.assertNotEqual(first, guard.first_failure)

    def test_no_alias_or_proposal_path_guessing(self):
        out = self.guard().check('packets/a', context('a', ['alias/b.cpp']), self.requests['packets/a'])
        self.assertFalse(out['independence_proven'])
        self.requests['packets/b']['owned_files'] = ['proposal/b.cpp']
        out = self.guard().check('packets/a', context('a', ['src/b.cpp']), self.requests['packets/a'])
        self.assertEqual(out['outcome'], 'no_known_selected_overlap')


if __name__ == '__main__':
    unittest.main()
