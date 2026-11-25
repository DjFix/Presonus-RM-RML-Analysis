"""Compare the typed portable metadata assignment with offline ARM observations."""
import json
from pathlib import Path
import subprocess
import sys


def replay(binary, fixture):
    data = json.loads(Path(fixture).read_text())
    count = 0
    for entry in data["entries"]:
        for case in entry["cases"]:
            args = [case["source"], case["destination"], str(int(case["self_assign"]))]
            actual = subprocess.check_output([binary, *args], text=True).splitlines()
            expected = [str(int(case["destination_return"])), case["source"], case["result"]]
            assert actual == expected, (args, actual, expected)
            count += 1
    print(f"{count} portable cases with original assignment observations")


if __name__ == "__main__":
    mode, *args = sys.argv[1:]
    if mode == "portable":
        replay(*args)
    elif mode == "native":
        producer, packet, rootfs, direct, fixture = args
        actual = subprocess.check_output([sys.executable, producer, packet, rootfs, direct])
        assert json.loads(actual) == json.loads(Path(fixture).read_bytes())
        print("Native case rerun matched the fixture")
    elif mode == "symbols":
        owner, binary, exact = args
        for path in (owner, binary):
            output = subprocess.check_output(["nm", "--defined-only", path], text=True)
            assert any(line.split()[-1] == exact for line in output.splitlines() if line.strip())
        print(exact)
    else:
        raise SystemExit(f"Unknown mode {mode}")
