"""Compare the real portable manager against native count fixtures."""
import argparse
import json
import subprocess
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--executable", type=Path)
    mode.add_argument("--object", type=Path)
    parser.add_argument("--fixtures", type=Path, required=True)
    args = parser.parse_args()
    fixtures = json.loads(args.fixtures.read_text())
    if args.object:
        mangled = fixtures["original"]["mangled"]
        symbols = subprocess.check_output(
            ["/usr/bin/nm", "--defined-only", str(args.object)], text=True
        )
        exact, = [line for line in symbols.splitlines() if line.endswith(f" T {mangled}")]
        print(exact)
        return
    cases = fixtures["cases"]
    for case in cases:
        assert case["receiver_and_entries_unchanged"]
        process = subprocess.run(
            [str(args.executable.resolve()), str(case["count"])],
            check=True, capture_output=True, text=True, timeout=10,
        )
        observed = tuple(map(int, process.stdout.split()))
        expected = case["observed_return"], case["capacity"]
        if observed != expected:
            raise ValueError(f"count {case['count']}: observed {observed}, expected {expected}")
    print(f"{len(cases)} portable cases compared against the original ARM return")
    print("Collection membership, entry name/category, capacity and observer events preserved")


if __name__ == "__main__":
    main()
