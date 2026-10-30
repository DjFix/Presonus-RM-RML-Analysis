#!/usr/bin/env python3
"""Compare built packet logging with saved application ARM output."""
import argparse
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--executable', type=Path, required=True)
    parser.add_argument('--fixtures', type=Path, required=True)
    parser.add_argument('--role', choices=('client', 'server'), required=True)
    parser.add_argument('--commands', action='store_true')
    args = parser.parse_args()
    total = 0
    selections = [None] if args.commands else range(5)
    for index in selections:
        if args.commands:
            if args.role != 'server':
                raise SystemExit('command table witness is NOAA/server only')
            invocation = [str(args.executable.resolve()), 'server', 'commands']
            expected = args.fixtures / 'noaa-command-arm-output.txt'
            stdin, count = None, 256
        else:
            invocation = [str(args.executable.resolve()), args.role]
            fixture = args.fixtures / f'{args.role}-{index}-fixtures.txt'
            expected = args.fixtures / f'{args.role}-{index}-arm-output.txt'
            stdin = fixture.read_bytes()
            header = stdin.splitlines()[0].split()
            if len(header) != 2:
                raise SystemExit('invalid clock/count fixture header')
            count = int(header[1])
        oracle = expected.read_bytes()
        if count <= 0 or len(oracle.splitlines()) != count:
            raise SystemExit('invalid retained ARM trace count')
        result = subprocess.run(invocation, input=stdin, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        if result.returncode:
            sys.stderr.buffer.write(result.stderr)
            raise SystemExit(result.returncode)
        if result.stdout != oracle:
            actual, wanted = result.stdout.splitlines(), oracle.splitlines()
            mismatch = next((i for i, pair in enumerate(zip(actual, wanted))
                             if pair[0] != pair[1]), min(len(actual), len(wanted)))
            raise SystemExit(f'{expected.name}: native/ARM mismatch at row {mismatch}')
        total += count
    print(f'PASS {total} {args.role} original ARM packet logging/command cases')


if __name__ == '__main__':
    main()
