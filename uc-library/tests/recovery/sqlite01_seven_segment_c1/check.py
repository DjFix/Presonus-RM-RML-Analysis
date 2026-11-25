"""Verify the native fixture, exact Linux constructor symbols and portable state."""
import json
from pathlib import Path
import struct
import subprocess
import sys


def replay(binary, fixture):
    entries = json.loads(fixture.read_text())["entries"]
    tests = 0
    for entry in entries:
        for case, base in zip(entry["cases"], entry["base_cases"], strict=True):
            actual = subprocess.check_output(
                [binary, str(case["seed"]), str(case["argument"])], text=True)
            derived_row, base_row = (list(map(int, line.split())) for line in actual.splitlines())
            assert derived_row == case["portable"]
            assert base_row == list(struct.unpack_from("<iIIIIi", bytes.fromhex(base["after"]), 20))
            tests += 1
    print(f"{tests} portable constructor and explicit-tag Control compositions")


def symbols(owner, binary, variant):
    exact = f"_ZN8Presonus5Panel15SevenSegControlC{variant}Ev"
    for item in (owner, binary):
        output = subprocess.check_output(["nm", "--defined-only", item], text=True)
        names = {line.split()[-1] for line in output.splitlines() if line.strip()}
        assert exact in names
    print(exact)


if __name__ == "__main__":
    mode, *args = sys.argv[1:]
    if mode == "portable":
        replay(args[0], Path(args[1]))
    elif mode == "native":
        producer, packet, rootfs, fixture = args
        actual = subprocess.check_output([sys.executable, producer, packet, rootfs])
        assert json.loads(actual) == json.loads(Path(fixture).read_bytes())
        print("6 native SevenSegControl and 6 native Control executions")
    elif mode == "symbols":
        symbols(*args)
    else:
        raise SystemExit(f"Unknown mode {mode}")
