"""Bounded ownership checks; no graph or reconstruction tools are invoked."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from plan_preflight import PlanError, analyze


class PlanPreflightTests(unittest.TestCase):
    def setUp(self):
        # Project-local scratch, including when launched by unittest.
        scratch = Path(__file__).resolve().parents[1] / 'temp/recovery-work/performance-stabilization01/plan-preflight'
        scratch.mkdir(parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'source').write_text('source')
        (self.root / 'other').write_text('other')

    def write(self, path, data):
        p = self.root / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data))
        return hashlib.sha256(p.read_bytes()).hexdigest()

    def run_plan(self, a, b, same_owner=False):
        self.write('a.json', dict(task_id='a', **a))
        self.write('b.json', dict(task_id='b', **b))
        plan = {'tasks': ['a.json', 'b.json']}
        if same_owner:
            plan['groups'] = [{'task_name': 'group', 'packets': ['packets/a', 'packets/b']}]
        self.write('plan.json', plan)
        return analyze(self.root, 'plan.json')

    def test_declared_read_write(self):
        out = self.run_plan({'owned_files': ['source']}, {'owned_files': ['other'], 'declared_source_dependencies': ['source']})
        self.assertEqual(out['conflicts'][0]['kind'], 'declared write/read')
        self.assertFalse(out['dispatch_authorized'])

    def test_symlink_alias_and_hardlink(self):
        (self.root / 'alias').symlink_to('source')
        out = self.run_plan({'owned_files': ['source']}, {'owned_files': ['alias']})
        self.assertEqual(out['conflicts'][0]['kind'], 'write/write')
        (self.root / 'hard').hardlink_to(self.root / 'source')
        self.assertTrue(self.run_plan({'owned_files': ['source']}, {'owned_files': ['hard']})['conflicts'])

    def test_non_normalized_path_rejected(self):
        for path in ['dir/../source', './source', 'dir//file', '/source', 'dir\\source']:
            with self.subTest(path=path), self.assertRaises(PlanError):
                self.run_plan({'owned_files': ['source']}, {'owned_files': [path]})

    def test_symlink_dotdot_resolves_after_link(self):
        (self.root / 'dir').mkdir()
        (self.root / 'link').symlink_to('dir')
        (self.root / 'alias').symlink_to('link/../source')
        self.assertTrue(self.run_plan({'owned_files': ['source']}, {'owned_files': ['alias']})['conflicts'])

    def test_outside_symlink_rejected_without_target_read(self):
        (self.root / 'escape').symlink_to('/nonexistent-outside-preflight/file')
        with self.assertRaisesRegex(PlanError, 'escapes'):
            self.run_plan({'owned_files': ['source']}, {'owned_files': ['escape']})
        (self.root / 'escape2').symlink_to('../outside')
        with self.assertRaisesRegex(PlanError, 'escapes'):
            self.run_plan({'owned_files': ['source']}, {'owned_files': ['escape2/file']})

    def test_case_typo_rejected(self):
        with self.assertRaisesRegex(PlanError, 'casing'):
            self.run_plan({'owned_files': ['source']}, {'owned_files': ['SOURCE']})

    def test_disjoint_and_unknown_implicit_reads(self):
        out = self.run_plan({'owned_files': ['source']}, {'owned_files': ['future/new.cpp']})
        self.assertEqual(out['outcome'], 'no_known_declared_conflicts')
        self.assertFalse(out['independence_proven'])
        self.assertFalse(out['task_scope']['b']['declared_reads_present'])
        self.assertIn('unknown', out['task_scope']['b']['implicit_reads'])

    def test_same_group_overlap_permitted(self):
        out = self.run_plan({'owned_files': ['source']}, {'owned_files': ['source']}, same_owner=True)
        self.assertFalse(out['conflicts'])

    def test_proposal_read_stays_canonical(self):
        digest = self.write('map.json', {'worker': 'a', 'destinations': {'source': 'proposal'}})
        out = self.run_plan({'owned_files': ['proposal'], 'source_proposal_map': {'path': 'map.json', 'sha256': digest}},
                            {'owned_files': ['other'], 'declared_source_dependencies': ['source']})
        self.assertFalse(out['conflicts'])

    def test_malformed_and_hash_mismatch_mapping(self):
        for ref in [{'path': 'map.json'}, {'path': '../outside', 'sha256': '0' * 64}]:
            with self.subTest(ref=ref), self.assertRaises((PlanError, FileNotFoundError)):
                self.run_plan({'owned_files': ['source'], 'source_proposal_map': ref}, {'owned_files': ['other']})
        digest = self.write('map.json', {'worker': 'a', 'destinations': {'source': 'unowned'}})
        with self.assertRaisesRegex(PlanError, 'outside actual owned_files'):
            self.run_plan({'owned_files': ['source'], 'source_proposal_map': {'path': 'map.json', 'sha256': digest}}, {'owned_files': ['other']})
        with self.assertRaisesRegex(PlanError, 'hash mismatch'):
            self.run_plan({'owned_files': ['source'], 'source_proposal_map': {'path': 'map.json', 'sha256': '0' * 64}}, {'owned_files': ['other']})

    def test_historical_hint_is_not_fresh_independence(self):
        out = self.run_plan({'owned_files': ['source']}, {'owned_files': ['other']})
        digest = self.write('context.json', {'task_id': 'b', 'generation_sha256': 'old',
                                           'selected_file_sha256': {'source': '0' * 64}})
        self.write('hints.json', {'contexts': [{'task_id': 'b', 'path': 'context.json', 'sha256': digest}]})
        out = analyze(self.root, 'plan.json', 'hints.json')
        self.assertFalse(out['conflicts'])
        self.assertEqual(out['historical_conflicts'][0]['writer_paths'], ['source'])
        self.assertIn('stale_or_unknown', out['task_scope']['b']['historical_context_scope'])
        self.assertFalse(out['dispatch_authorized'])
        self.assertFalse(out['independence_proven'])
        self.write('context.json', {'task_id': 'b', 'selected_file_sha256': {}})
        with self.assertRaisesRegex(PlanError, 'hash mismatch'):
            analyze(self.root, 'plan.json', 'hints.json')

    def test_group_coverage_rejected(self):
        self.write('a.json', {'task_id': 'a', 'owned_files': ['source']})
        self.write('plan.json', {'tasks': ['a.json'], 'groups': [{'task_name': 'owner', 'packets': ['packets/wrong']}]})
        with self.assertRaises(PlanError):
            analyze(self.root, 'plan.json')


if __name__ == '__main__':
    unittest.main()
