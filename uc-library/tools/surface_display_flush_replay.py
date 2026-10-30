"""Replay each original-role bitmap flush fixture in a fresh process."""
import argparse
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('--executable', type=Path, required=True)
parser.add_argument('--fixture', type=Path, action='append', required=True)
args = parser.parse_args()
repository = Path(__file__).resolve().parents[2]
# Installed under uc-library/tools; this draft is staged, not executed here.
temporary = Path(os.environ['TMPDIR']).resolve()
assert temporary.is_relative_to(repository / 'temp/test-work')
assert temporary.is_dir() and len(args.fixture) == 2
for fixture in args.fixture:
    assert fixture.resolve().is_relative_to(repository / 'uc-library/tests/fixtures')
    result = subprocess.run([str(args.executable.resolve()), str(fixture.resolve())],
                            capture_output=True, text=True)
    print(result.stdout, end='')
    print(result.stderr, end='')
    assert result.returncode == 0, (str(fixture), result.returncode)
