"""Replay current native evidence and compare portable observations."""
import json
from pathlib import Path
import subprocess
import sys


def replay(binary, fixture):
    count = 0
    for entry in json.loads(Path(fixture).read_text())["entries"]:
        for case in entry["cases"]:
            argument = case["input"]
            if entry["provider_boundary"] is None:
                actual = subprocess.check_output([binary, str(argument)], text=True)
                assert int(actual) == case["receiver_result"]
            else:
                assert case["calls"][0]["name"] == argument
                args = [binary, "name"]
                if argument is not None:
                    args.append(argument)
                subprocess.run(args, check=True)
            count += 1
    print(f"{count} portable cases")


if __name__ == "__main__":
    mode, *args = sys.argv[1:]
    if mode == "portable":
        replay(*args)
    elif mode == "native":
        producer, packet, rootfs, fixture = args
        result = subprocess.check_output([sys.executable, producer, packet, rootfs])
        assert json.loads(result) == json.loads(Path(fixture).read_bytes())
        print("Native cases matched fixture")
    elif mode == "symbols":
        owner, binary, exact = args
        for path in (owner, binary):
            output = subprocess.check_output(["nm", "--defined-only", path], text=True)
            assert any(line.split()[-1] == exact for line in output.splitlines() if line.strip())
        print(exact)
    else:
        raise SystemExit(f"Unknown mode {mode}")
