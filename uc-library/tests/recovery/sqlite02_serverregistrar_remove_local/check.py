"""Compare portable registrar and observed original roster/call order."""
import json
from pathlib import Path
import subprocess
import sys


def replay(binary, fixture):
    data = json.loads(Path(fixture).read_text())
    mode = data["mode"]
    count = 0
    for entry in data["entries"]:
        for case in entry["cases"]:
            listeners = case.get("listeners", 0)
            argument = case["argument"]
            argv = [binary, mode, "" if argument is None else str(argument),
                    str(case.get("port", 0)), str(listeners),
                    str(int(case.get("full", False))), str(int(argument is None)),
                    *(str(i) for i in case["initial"])]
            actual = subprocess.check_output(argv, text=True).splitlines()
            expected = []
            for event, identity, roster in case["events"]:
                ids = " ".join(str(i) for i in (identity, *roster))
                if event == "delete":
                    expected.extend([f"destructor 0 {ids}", f"delete 0 {ids}"])
                else:
                    expected.extend(f"{event} {number} {ids}"
                                    for number in range(1, listeners + 1))
            expected.append(" ".join(["final", *(str(i) for i in case["final"])]))
            assert actual == expected, (argv, actual, expected)
            count += 1
    print(f"{count} portable cases with original roster and call order")


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
