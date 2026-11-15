import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from context_batch import Environment
from context_runtime import ContextError

class PreviousInspection(unittest.TestCase):
    def exercise(self, code, stdout, stderr):
        scratch=Path(__file__).resolve().parents[1]/'temp/test-work'
        scratch.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='missing-inspection-',dir=scratch) as folder:
            output=Path(folder);old=output/'environment-handles-old.json'
            old.write_text(json.dumps({'containers':{'runner':'context-batch-runner-exact'}}))
            env=object.__new__(Environment);env.root=output;env.output=output
            env.handle_path=output/'environment-handles-current.json'
            result=subprocess.CompletedProcess(['docker','inspect'],code,stdout,stderr)
            with patch('context_batch.subprocess.run',return_value=result):env.check_previous()
            self.assertEqual(len(list(output.glob('resume-inspect-*.json'))),1)
    def test_modern_lowercase_absent(self):
        self.exercise(1,'\n','error: no such object: context-batch-runner-exact\n')
    def test_previous_uppercase_absent(self):
        self.exercise(1,'','Error: No such object: context-batch-runner-exact\n')
    def test_stopped_is_allowed(self):self.exercise(0,'false\n','')
    def test_live_unknown_permission_and_wrong_identity_reject(self):
        cases=[(0,'true\n',''),(1,'','permission denied connecting to Docker daemon'),
               (1,'','unknown daemon failure'),(1,'','error: no such object: another-container'),
               (1,'true','error: no such object: context-batch-runner-exact'),
               (1,'','error: permission denied; No such object: context-batch-runner-exact'),
               (2,'','error: no such object: context-batch-runner-exact')]
        for values in cases:
            with self.subTest(values=values),self.assertRaises(ContextError):self.exercise(*values)

if __name__=='__main__':unittest.main()
