"""Replay portable typed deletion using the sealed native observations."""
import argparse
import json
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("binary", type=Path)
    parser.add_argument("fixture", type=Path)
    args = parser.parse_args()
    empty, concrete = json.loads(args.fixture.read_text())["cases"]
    if empty["nonnull"] or empty["events"] or empty["allocation_unmapped"]:
        raise ValueError("Unexpected native null side effects")
    destructor, _, _, release = concrete["events"][-4:]
    if (not concrete["nonnull"] or not concrete["allocation_unmapped"]
            or not destructor[0].endswith("D0Ev") or release[0] != "operator delete PLT"
            or destructor[1] != release[1]):
        raise ValueError("Native dynamic destructor and allocator receiver must match")
    expected = [
        f"null 0 0 0 0 {int(empty['surface_unchanged'])}",
        f"concrete 0 0 0 0 {int(concrete['surface_unchanged'])}",
        f"derived 1 1 1 1 {int(concrete['surface_unchanged'])}",
    ]
    result = subprocess.run([str(args.binary.resolve())], text=True,
                            capture_output=True, check=True).stdout.splitlines()
    if result != expected:
        raise ValueError(f"Portable lifecycle differs from expected outcomes: {result!r}")
    print(f"Portable cases: {len(result)}")


if __name__ == "__main__":
    main()
