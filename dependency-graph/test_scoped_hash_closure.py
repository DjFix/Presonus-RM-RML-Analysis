"""Scoped preparation caching must not expand or hide compiler dependencies."""
import ast
from pathlib import Path
import unittest
from reuse_observations import _closure, _safe_sha_leaf
from refresh_graph import PRODUCERS

ROOT=Path(__file__).resolve().parents[1]


class ScopedHashClosureTests(unittest.TestCase):
    def source(self):
        return (ROOT/'dependency-graph/context_runtime.py').read_text()

    def test_current_hash_only_import_remains_a_verified_leaf(self):
        self.assertTrue(_safe_sha_leaf(ast.parse(self.source())))
        closure=_closure(ROOT)
        self.assertFalse(set(closure)-{'dependency-graph/'+name for name in PRODUCERS})
        self.assertNotIn('dependency-graph/snapshot_runtime.py',closure)

    def test_changed_hash_helper_requires_full_dependency_scan(self):
        source=self.source().replace("return hashlib.file_digest(stream, 'sha256').hexdigest()",
            "return another_module.digest(stream)")
        self.assertFalse(_safe_sha_leaf(ast.parse(source)))

    def test_initializer_and_decorator_changes_are_not_safe_leaves(self):
        for source in (self.source()+"\nextra = execute_project_code()\n",
                       self.source().replace("contextvars.ContextVar('context_input_hashes', default=None)","load_project_cache()"),
                       self.source().replace('@contextlib.contextmanager','@project_wrapper')):
            self.assertFalse(_safe_sha_leaf(ast.parse(source)))

    def test_rebinding_a_hash_dependency_is_not_a_safe_leaf(self):
        self.assertFalse(_safe_sha_leaf(ast.parse(self.source()+'\nfrom another_module import _digest\n')))


if __name__=='__main__':unittest.main()
