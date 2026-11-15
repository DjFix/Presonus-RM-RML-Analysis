import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from stage_timing import StageTimings


class StageTimingTests(unittest.TestCase):
    def test_failed_call_is_accounted_and_exception_propagates(self):
        timer=StageTimings()
        def fail():
            raise ValueError('retain failure')
        with self.assertRaisesRegex(ValueError,'retain failure'):
            timer.call('failure',fail)
        self.assertEqual(timer.phases['failure']['calls'],1)
        self.assertGreaterEqual(timer.phases['failure']['wall_seconds'],0)
        self.assertEqual(timer.call('success',lambda:42),42)
        base=Path(__file__).resolve().parents[1]/'temp/test-work'
        base.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=base) as folder:
            output=Path(folder)/'timing.json';timer.save(output)
            result=json.loads(output.read_text())
            self.assertEqual(set(result['phases']),{'success','failure'})
            self.assertGreaterEqual(result['other_seconds'],0)


if __name__=='__main__':unittest.main()
