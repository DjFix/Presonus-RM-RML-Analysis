"""Extraction import closure keeps unrelated lazy runtime helpers out of reuse."""
import hashlib
from pathlib import Path
import tempfile
import unittest

from reuse_observations import EXTRACTORS, _closure

ROOT = Path(__file__).resolve().parents[1]


class ExtractionClosureTests(unittest.TestCase):
    def setUp(self):
        base = ROOT / 'temp/test-work'
        base.mkdir(parents=True, exist_ok=True)
        temporary = tempfile.TemporaryDirectory(prefix='extraction-closure-', dir=base)
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.producers = self.root / 'dependency-graph'
        self.producers.mkdir()
        for name in EXTRACTORS:
            self.write(name, '')
        self.write('refresh_extract', 'from context_runtime import sha\n')
        self.write('context_runtime', '''import pathlib
import hashlib

def sha(path):
    with pathlib.Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def unused_guard():
    from snapshot_runtime import verify
''')
        self.write('snapshot_runtime', 'from snapshot_observations import verify\n')
        self.write('snapshot_observations', 'def verify(): pass\n')

    def write(self, module, text):
        (self.producers / (module + '.py')).write_text(text)

    def append_runtime(self, text):
        path = self.producers / 'context_runtime.py'
        path.write_text(path.read_text() + text)

    def test_unrelated_lazy_ignored_but_whole_module_bound(self):
        found = _closure(self.root)
        self.assertNotIn('dependency-graph/snapshot_runtime.py', found)
        self.assertNotIn('dependency-graph/snapshot_observations.py', found)
        digest = hashlib.sha256((self.producers / 'context_runtime.py').read_bytes()).hexdigest()
        self.assertEqual(found['dependency-graph/context_runtime.py'], digest)

    def test_local_sha_import_is_followed(self):
        path = self.producers / 'context_runtime.py'
        path.write_text(path.read_text().replace('    with pathlib',
                                                '    import relevant\n    with pathlib'))
        self.write('relevant', '')
        self.assertIn('dependency-graph/relevant.py', _closure(self.root))

    def test_local_sha_callee_dependency_is_not_ignored(self):
        self.write('context_runtime', '''def helper():
    import relevant

def sha(path):
    return helper()
''')
        self.write('relevant', '')
        self.assertIn('dependency-graph/relevant.py', _closure(self.root))

    def test_dynamic_sha_import_rejected(self):
        self.write('context_runtime', "def sha(path):\n    return __import__('relevant')\n")
        with self.assertRaisesRegex(ValueError, 'Dynamic'):
            _closure(self.root)

    def test_other_from_name_and_general_import_full_closure(self):
        for statement in ('from context_runtime import sha, unused_guard\n',
                          'import context_runtime\n'):
            with self.subTest(statement=statement):
                self.write('refresh_extract', statement)
                self.assertIn('dependency-graph/snapshot_observations.py', _closure(self.root))

    def test_module_initializer_callee_uses_full_fallback(self):
        self.append_runtime('unused_guard()\n')
        self.assertIn('dependency-graph/snapshot_observations.py', _closure(self.root))

    def test_implicit_decorator_calls_use_full_fallback(self):
        self.append_runtime('''def deco(function):
    import decorator_dependency
    return function

@deco
def guarded(): pass
''')
        self.write('decorator_dependency', '')
        self.assertIn('dependency-graph/decorator_dependency.py', _closure(self.root))

    def test_nonconstant_default_uses_full_fallback(self):
        self.append_runtime('def guarded(value=1+2): pass\n')
        self.assertIn('dependency-graph/snapshot_observations.py', _closure(self.root))

    def test_annotation_uses_full_fallback(self):
        self.append_runtime('def guarded(value: int): pass\n')
        self.assertIn('dependency-graph/snapshot_observations.py', _closure(self.root))

    def test_constant_false_default_keeps_leaf_specialization(self):
        self.append_runtime('def guarded(value=False): pass\n')
        self.assertNotIn('dependency-graph/snapshot_observations.py', _closure(self.root))


if __name__ == '__main__':
    unittest.main()
