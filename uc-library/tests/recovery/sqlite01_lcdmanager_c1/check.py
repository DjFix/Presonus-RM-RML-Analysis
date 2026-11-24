"""Compare native null binding with the equivalent portable construction state."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", type=Path, required=True)
    parser.add_argument("--object", type=Path, required=True)
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--fixture-sha256", required=True)
    parser.add_argument("--variant", choices=("C1", "C2"), required=True)
    args = parser.parse_args()
    assert digest(args.fixtures) == args.fixture_sha256
    observations = json.loads(args.fixtures.read_text())["observations"]
    assert {item["role"] for item in observations} == {"client", "server"}
    nm = subprocess.check_output(["nm", "--defined-only", args.object], text=True)
    symbols = [line.split()[-1] for line in nm.splitlines() if line.strip()]
    for variant in ("C1", "C2"):
        assert symbols.count(f"_ZN8Presonus5Panel10LCDManager{variant}Ev") == 1
    count = 0
    for item in observations:
        assert item["mangled"] == f"_ZN8Presonus5Panel10LCDManager{args.variant}Ev"
        assert len(item["cases"]) == 2
        for case in item["cases"]:
            result = subprocess.check_output([args.exe.resolve(), args.variant], text=True)
            assert result == f"{int(case['portable_initial_binding_present'])}\n"
            count += 1
    print(json.dumps({
        "passed": True, "variant": args.variant, "case_count": count,
        "fixtures_sha256": args.fixture_sha256, "object_sha256": digest(args.object),
        "exe_sha256": digest(args.exe), "compiled_symbols": [
            name for name in symbols
            if name in ("_ZN8Presonus5Panel10LCDManagerC1Ev", "_ZN8Presonus5Panel10LCDManagerC2Ev")
        ],
    }))


if __name__ == "__main__":
    main()
