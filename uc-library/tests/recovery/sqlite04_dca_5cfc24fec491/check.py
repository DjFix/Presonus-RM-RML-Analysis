"""Compare native and portable dB conversion traces."""

import json
from pathlib import Path
import subprocess
import sys

mode, *args = sys.argv[1:]
if mode == "portable":
    binary, fixture = args
    cases = json.loads(Path(fixture).read_bytes())["cases"]
    for case in cases:
        cmd = [binary, *map(str, case["args"])]
        actual = subprocess.check_output(cmd, text=True).splitlines()
        assert actual == case["expected"], (cmd, actual, case["expected"])
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
