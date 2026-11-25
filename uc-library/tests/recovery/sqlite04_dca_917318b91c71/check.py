"""Compare native and portable dB conversion traces."""

import json
from pathlib import Path
import subprocess
import sys

def normalize_nan(line):
    fields = line.split()
    if fields[0] in ("min", "get", "set", "final"):
        values = (1, 2) if fields[0] == "final" else (2,)
        for index in values:
            bits = int(fields[index])
            if bits & 0x7f800000 == 0x7f800000 and bits & 0x007fffff:
                fields[index] = "NaN"
    return " ".join(fields)


mode, *args = sys.argv[1:]
if mode == "portable":
    binary, fixture = args
    cases = json.loads(Path(fixture).read_bytes())["cases"]
    for case in cases:
        cmd = [binary, *map(str, case["args"])]
        actual = subprocess.check_output(cmd, text=True).splitlines()
        assert list(map(normalize_nan, actual)) == list(map(normalize_nan, case["expected"])), (cmd, actual, case["expected"])
    print(f"{len(cases)} independent native observations match portable traces")
elif mode == "native":
    native, context, binary, fixture = args
    actual = subprocess.check_output([sys.executable, native, context, binary])
    assert json.loads(actual) == json.loads(Path(fixture).read_bytes())
    print("Original ARM replay regenerated the fixture")
elif mode == "symbols":
    owner, binary, expected = args
    for path in (owner, binary):
        output = subprocess.check_output(["nm", "--defined-only", path], text=True)
        assert expected in [line.split()[-1] for line in output.splitlines() if line.strip()]
    print(expected)
else:
    raise SystemExit(f"Unknown check {mode}")
