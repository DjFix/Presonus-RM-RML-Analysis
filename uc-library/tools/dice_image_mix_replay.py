#!/usr/bin/env python3
"""Stream exact saved ARM event traces into a built portable mixer test."""
import argparse
import gzip
import hashlib
import json
import shutil
import subprocess
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--executable", type=Path, required=True)
    p.add_argument("--oracle", type=Path, required=True)
    a = p.parse_args()
    oracle_path = a.oracle.resolve()
    oracle = json.loads(oracle_path.read_text())
    directory = oracle_path.parent
    fixtures = directory / "arm-fixtures.txt"
    traces = directory / "exact-traces.txt.gz"
    for path, expected in ((fixtures, oracle["fixture_sha256"]), (traces, oracle["exact_trace_sha256"])):
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, path
    process = subprocess.Popen([str(a.executable.resolve()), str(fixtures)], stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:
        with gzip.open(traces, "rb") as stream:
            shutil.copyfileobj(stream, process.stdin)
    except BrokenPipeError:
        pass
    finally:
        try:
            process.stdin.close()
        except BrokenPipeError:
            pass
    output = process.stdout.read().decode()
    code = process.wait()
    print(output, end="")
    if code:
        raise SystemExit(code)
    assert output.startswith(f'PASS: {sum(oracle["counts"].values())} original ARM cases;')


if __name__ == "__main__":
    main()
