import unittest
from native_graph import execution_targets

class ExecutionTargetsTests(unittest.TestCase):
    def test_mapping_and_data_are_not_callees(self):
        self.assertEqual(execution_targets(0x1000,{0x1000:['mapping','data','C1','C2']},{'C1','C2'}),['C1','C2'])

    def test_unknown_endpoint_stays_unknown(self):
        self.assertEqual(execution_targets(0x1000,{0x1000:['mapping','data']},set()),[])

    def test_thumb_normalization(self):
        self.assertEqual(execution_targets(0x1001,{0x1000:['func']},{'func'}),['func'])

    def test_import_function_identity_preserved(self):
        self.assertEqual(execution_targets(0x1000,{0x1000:['import','mapping']},{'import'}),['import'])

if __name__=='__main__':unittest.main()
