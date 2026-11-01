import importlib.util
import pathlib
import unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('context_transport_operator',ROOT/'uc-library/tools/recovery/select_context.py')
operator=importlib.util.module_from_spec(spec);spec.loader.exec_module(operator)

class TransportTests(unittest.TestCase):
    def test_canonical_root_and_output_paths_are_preserved(self):
        out=ROOT/'temp/recovery-work/test-packet'
        argv=operator.selector_command(ROOT,out,'prepare')
        self.assertIn(str(ROOT)+':'+str(ROOT)+':ro',argv)
        self.assertIn(str(out)+':'+str(out)+':rw',argv)
        self.assertIn(str(ROOT/'dependency-graph/context_selector.py'),argv)
        self.assertEqual(argv[argv.index('--workdir')+1],str(ROOT))
        self.assertFalse(any('/workspace' in arg for arg in argv))

    def test_registration_allows_atomic_active_replacement(self):
        argv=operator.selector_command(ROOT,ROOT/'temp/recovery-work/test-register','register')
        base=ROOT/'dependency-graph'
        self.assertIn(str(base)+':'+str(base)+':rw',argv)
        self.assertFalse(any('ACTIVE.json:' in arg for arg in argv))
