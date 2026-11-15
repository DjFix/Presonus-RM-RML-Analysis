"""Every public preparation entry point must use the raised finite copy profile."""
import contextlib
import importlib.util
import inspect
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import context_batch

ROOT=Path(__file__).resolve().parents[1]


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


class SnapshotBudgetDefaultsTests(unittest.TestCase):
    def test_library_defaults_share_one_gib_profile(self):
        expected=1024**3
        self.assertEqual(context_batch.DEFAULT_SNAPSHOT_COPY_BYTES,expected)
        for function in (context_batch.run,context_batch.freeze_snapshot):
            self.assertEqual(inspect.signature(function).parameters['copy_budget_bytes'].default,expected)

    def test_production_cli_default_and_explicit_override(self):
        operator=load('budget_operator',ROOT/'uc-library/tools/recovery/select_context.py')
        for arguments,expected in (([],1024**3),(['--snapshot-copy-budget-bytes','123'],123)):
            with patch.dict(sys.modules,{'budget_operator':operator}), patch.object(sys,'argv',['select_context','batch-prepare','--tasks','unused.json','--out','temp/recovery-work/unused',*arguments]), \
                 patch.object(context_batch,'run',return_value=Path('unused.json')) as run, \
                 contextlib.redirect_stdout(io.StringIO()):
                operator.main()
            self.assertEqual(run.call_args.kwargs['copy_budget_bytes'],expected)

    def test_measurement_cli_default_and_explicit_override(self):
        measure=load('budget_measure',ROOT/'dependency-graph/measure_context_preparation.py')
        scratch=ROOT/'temp/recovery-work'
        scratch.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='budget-test-',dir=scratch) as folder:
            base=Path(folder);manifest=base/'TASKS.json';manifest.write_text('{}')
            for index,(arguments,expected) in enumerate((([],1024**3),(['--copy-budget-mib','2'],2*1024**2))):
                out=base/str(index)
                with patch.object(sys,'argv',['measure','--out',str(out.relative_to(ROOT)),
                      '--tasks',str(manifest.relative_to(ROOT)),*arguments]), \
                     patch.object(context_batch,'run',return_value=out/'dispatch.json') as run, \
                     contextlib.redirect_stdout(io.StringIO()):
                    measure.main()
                self.assertEqual(run.call_args.kwargs['copy_budget_bytes'],expected)


if __name__=='__main__':unittest.main()
