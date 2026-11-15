import copy
import json
import unittest
import test_code_identity as fixtures
ROOT = fixtures.ROOT
from code_identity import normalize_ast as reference
from stage_normalization import normalize_ast


class StageNormalizationTests(unittest.TestCase):
    def test_exact_reference_outputs_and_independent_mutable_result(self):
        case=fixtures.IdentityTests()
        for tu in ('tu:old','tu:new'):
            original=case.ast(tu)
            original['diagnostics']=[{'items':['unchanged']}]
            target=original['edges'][0][1]
            evidence=json.dumps({'target':target,'tu':tu})
            original['edges'].extend([['function:f',target,'USES',evidence]]*100)
            before=copy.deepcopy(original)
            actual=normalize_ast(ROOT,case.row(),original)
            self.assertEqual(actual,reference(ROOT,case.row(),original))
            self.assertEqual(normalize_ast(ROOT,case.row(),actual[0])[0],actual[0])
            actual[0]['diagnostics'][0]['items'].append('new')
            actual[0]['unresolved'][0]['site']['line']=99
            next(iter(actual[0]['nodes'].values()))['metadata']['new']=['value']
            self.assertEqual(original,before)

    def test_conflicting_nodes_still_rejected(self):
        case=fixtures.IdentityTests();original=case.ast('tu:old')
        original['nodes']['tu:other']={'kind':'TranslationUnit','metadata':{}}
        for function in (reference,normalize_ast):
            with self.assertRaises(ValueError):function(ROOT,case.row(),original)


if __name__=='__main__':unittest.main()
