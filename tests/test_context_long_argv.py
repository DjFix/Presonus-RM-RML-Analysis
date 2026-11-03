import json
import pathlib
import subprocess
import sys
import unittest
import uuid
from unittest import mock
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'dependency-graph'))
from context_batch import Environment

class LongArgvTests(unittest.TestCase):
    def test_large_argv_preserves_all_literals(self):
        out=ROOT/'temp/test-work/context-long-argv'/uuid.uuid4().hex
        out.mkdir(parents=True)
        env=Environment(ROOT,out)
        values=['mount'+str(i)+'x'*100 for i in range(2000)]
        values+=['space quote\' dollar$(touch NEVER) `touch NEVER`\nnewline']
        argv=[sys.executable,'-c','import json,sys;print(json.dumps(sys.argv[1:]))',*values]
        actual_run=subprocess.run
        def run(command,**kwargs):
            self.assertEqual(command[:3],['sg','docker','-c'])
            self.assertLess(len(command[3]),4096)
            return actual_run(['/bin/sh','-c',command[3]],**kwargs)
        with mock.patch('context_batch.subprocess.run',side_effect=run):env.command(argv,'large')
        self.assertEqual(json.loads((out/'large.log').read_text()),values)
        receipt=json.loads((out/'large.json').read_text())
        self.assertEqual(receipt['argv'],argv)
        self.assertTrue(receipt['command_file_sha256'])
        self.assertFalse((ROOT/'NEVER').exists())

if __name__=='__main__':unittest.main()
