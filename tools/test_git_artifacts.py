"""Exercise the guard against real staged Git blobs, without recovery execution."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from check_git_artifacts import check

ROOT = Path(__file__).resolve().parents[1]


class GitArtifactPolicyTests(unittest.TestCase):
    def setUp(self):
        scratch = ROOT / 'temp/test-work/git-artifact-policy'
        scratch.mkdir(parents=True, exist_ok=True)
        self.repo = Path(tempfile.mkdtemp(dir=scratch))
        self.git('init', '-q')
        self.git('config', 'user.name', 'Artifact policy test')
        self.git('config', 'user.email', 'policy-test@example.invalid')
        self.policy = {'max_added_blob_bytes': 20 * 1024 * 1024,
                       'legacy_test_inputs': {'evidence/fixtures.txt': 'test fixture'}}
        self.put('tools/git-artifact-policy.json', json.dumps(self.policy))
        self.git('add', 'tools/git-artifact-policy.json')
        self.git('commit', '-qm', 'Test baseline')

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.repo), *args])

    def put(self, path, content):
        p = self.repo / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)

    def test_force_added_ignored_report_is_rejected(self):
        self.put('.gitignore', '/evidence/\n')
        self.put('evidence/FINAL_SOURCE_DRIFT01.json', '{}')
        self.git('add', '-f', 'evidence/FINAL_SOURCE_DRIFT01.json')
        self.assertTrue(any('FINAL_SOURCE_DRIFT01' in x for x in check(str(self.repo))))

    def test_index_only_removal_preserves_local_bytes(self):
        self.put('uc-library/validation/proof.json', '{"historical":true}')
        self.git('add', '.')
        self.git('commit', '-qm', 'Historical report before policy hook')
        before = (self.repo / 'uc-library/validation/proof.json').read_bytes()
        self.git('rm', '--cached', 'uc-library/validation/proof.json')
        self.assertEqual([], check(str(self.repo), tracked=True))
        self.assertEqual(before, (self.repo / 'uc-library/validation/proof.json').read_bytes())

    def test_restored_historical_report_is_rejected(self):
        self.put("evidence/report.json", "{}")
        self.git("add", ".")
        self.git("commit", "-qm", "Historical report")
        self.git("rm", "--cached", "evidence/report.json")
        self.git("add", "-f", "evidence/report.json")
        self.assertTrue(check(str(self.repo), tracked=True))

    def test_sources_and_named_legacy_fixture_allowed(self):
        self.put('uc-library/tests/recovery/fixtures.json', '[1,2]')
        self.put('evidence/fixtures.txt', 'expected output\n')
        self.git('add', '.')
        self.assertEqual([], check(str(self.repo), tracked=True))

    def test_unstaged_policy_exception_does_not_bless_report(self):
        self.put('evidence/report.json', '{}')
        self.git('add', 'evidence/report.json')
        self.policy['legacy_test_inputs']['evidence/report.json'] = 'unstaged'
        self.put('tools/git-artifact-policy.json', json.dumps(self.policy))
        self.assertTrue(check(str(self.repo)))

    def test_oversize_new_blob_rejected(self):
        self.put('large.txt', 'x' * (20 * 1024 * 1024 + 1))
        self.git('add', 'large.txt')
        self.assertTrue(any('staged-blob limit' in x for x in check(str(self.repo))))


if __name__ == '__main__':
    unittest.main()
