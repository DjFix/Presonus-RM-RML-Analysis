#!/usr/bin/env python3
"""Compare the built UART parser's event traces with saved original ARM traces."""
import argparse
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--executable', required=True, type=Path)
    parser.add_argument('--fixtures', required=True, type=Path)
    parser.add_argument('--expected', required=True, type=Path)
    args = parser.parse_args()
    fixtures = args.fixtures.read_bytes()
    expected = args.expected.read_bytes()
    count = int(fixtures.splitlines()[0])
    if len(expected.splitlines()) != count or count == 0:
        raise SystemExit('invalid original ARM trace count')
    result = subprocess.run([str(args.executable.resolve())], input=fixtures,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        sys.stderr.buffer.write(result.stderr)
        raise SystemExit(result.returncode)
    if result.stdout != expected:
        actual_lines = result.stdout.splitlines()
        expected_lines = expected.splitlines()
        mismatch = next((i for i, (a, b) in enumerate(zip(actual_lines, expected_lines))
                         if a != b), min(len(actual_lines), len(expected_lines)))
        raise SystemExit(f'UART ARM trace mismatch at case {mismatch}; '
                         f'actual rows={len(actual_lines)}, expected rows={count}')
    print(f'PASS {count} UART original ARM/native event traces')


if __name__ == '__main__':
    main()
