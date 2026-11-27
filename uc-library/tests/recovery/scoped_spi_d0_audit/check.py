"""Read-only CTest adapter: replay canonical archive D0 against sealed native cases."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

FIXTURE_SHA256 = "2c94b28e1835dee3ac3f1b030ce3ff36a15d25d527d75ca8c4fdfc2e625db90b"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--exe", type=Path, required=True)
    parser.add_argument("--fixtures", type=Path, required=True)
    args = parser.parse_args()
    data = args.fixtures.read_bytes()
    if hashlib.sha256(data).hexdigest() != FIXTURE_SHA256:
        raise RuntimeError("Sealed native fixture hash changed")
    fixture = json.loads(data)
    expected = [case["output"] for case in fixture["targets"][0]["cases"]]
    result = subprocess.run([str(args.exe.resolve())], check=True, text=True,
                            capture_output=True)
    observed = [list(map(int, line.split())) for line in result.stdout.splitlines()]
    if observed != expected:
        raise RuntimeError((observed, expected))
    diagnostics = result.stderr.splitlines()
    if len(diagnostics) != len(expected) or any(
            not line.startswith("sized_deletes=1 unsized_deletes=0 allocation_size=")
            for line in diagnostics):
        raise RuntimeError(result.stderr)
    print(f"SPI D0 canonical archive: {len(expected)} heap cases passed; actual sized delete once")

if __name__ == "__main__":
    main()
