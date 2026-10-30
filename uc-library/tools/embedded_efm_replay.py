"""Replay the saved EFM line-oriented fixtures against an active executable."""
import argparse
import gzip
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--executable", type=Path, required=True)
parser.add_argument("--fixtures", type=Path, required=True)
parser.add_argument("--expected", type=Path, required=True)
parser.add_argument("--cases", type=int, required=True)
parser.add_argument("--binary-records", action="store_true")
args = parser.parse_args()
def read_fixture(path):
    data = path.read_bytes()
    return gzip.decompress(data) if path.suffix == '.gz' else data


fixtures = read_fixture(args.fixtures)
expected = read_fixture(args.expected)
if args.binary_records:
    assert len(fixtures) == args.cases * 4100
    assert len(expected) == args.cases * 4097
else:
    assert len(fixtures.splitlines()) == args.cases
    assert len(expected.splitlines()) == args.cases
result = subprocess.run([str(args.executable)], input=fixtures, capture_output=True)
if result.returncode:
    raise SystemExit(result.stderr.decode(errors="replace") or result.returncode)
assert result.stdout == expected, "EFM fixture output differs from saved original execution"
print(f"PASS {args.cases} EFM fixture cases")
