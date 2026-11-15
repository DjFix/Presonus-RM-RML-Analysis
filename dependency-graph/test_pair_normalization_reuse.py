"""Both inputs are authenticated even when deterministic normalization is shared."""
from pathlib import Path
import unittest
from unittest.mock import patch
import test_unchanged_observations as fixtures
from code_identity import normalize_ast as reference

import unchanged_observations as module

class PairReuseTests(unittest.TestCase):
    def setUp(self):
        self.case=fixtures.ObservationEquivalenceTests()
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)

    def test_equal_verified_pair_normalizes_once(self):
        with patch.object(module,'normalize_ast',wraps=reference) as normalizer:
            self.assertTrue(self.case.check())
            self.assertEqual(normalizer.call_count,1)
        self.assertIsNone(self.case.v._comparison)

    def test_different_ast_takes_full_comparison(self):
        self.case.mutate('ast',lambda data:data.update(diagnostics=['changed']))
        with patch.object(module,'normalize_ast',wraps=reference) as normalizer:
            self.assertFalse(self.case.check())
            self.assertEqual(normalizer.call_count,2)
        self.assertIsNone(self.case.v._comparison)

    def test_retargeted_include_directory_does_not_reuse_old_context(self):
        left=self.case.root/'left';right=self.case.root/'right';alias=self.case.root/'includes'
        left.mkdir();right.mkdir();alias.symlink_to(left)
        self.case.row['arguments'].insert(1,'-I'+str(alias))
        self.case.old=self.case.write_pair('old',self.case.ast,self.case.gcc)
        self.case.new=self.case.write_pair('new',dict(self.case.ast,seconds=9),dict(self.case.gcc,seconds=8))
        self.case.previous=dict(self.case.old,command=self.case.row,inputs=self.case.ast['input_sha256'],external_inputs=[])
        calls=[]
        def change_after_first(*args):
            result=reference(*args);calls.append(True)
            if len(calls)==1:
                alias.unlink();alias.symlink_to(right)
            return result
        with patch.object(module,'normalize_ast',side_effect=change_after_first):
            self.assertFalse(self.case.check())
        self.assertEqual(len(calls),2)

    def test_corrupt_second_capture_is_not_hidden_by_reuse(self):
        self.case.mutate('gcc',lambda data:data.update(argv=['wrong']))
        self.assertFalse(self.case.check())
        self.assertIsNone(self.case.v._comparison)

    def test_identical_invalid_ast_still_requires_normalization(self):
        for name in ('old','new'):
            import json
            path=Path(getattr(self.case,name)['ast']);value=json.loads(path.read_text())
            value['nodes']['extra']={'kind':'TranslationUnit','metadata':{}}
            path.write_text(json.dumps(value))
        self.case.previous['ast_sha256']=self.case.v.sha(self.case.old['ast'])
        self.assertFalse(self.case.check())
        self.assertIsNone(self.case.v._comparison)

if __name__=='__main__':unittest.main()
