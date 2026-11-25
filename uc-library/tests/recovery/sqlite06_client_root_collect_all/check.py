import json
from pathlib import Path
import subprocess
import sys

mode, *args = sys.argv[1:]
if mode == "native":
    producer, context, fixture = args
    observed = json.loads(subprocess.check_output([sys.executable, "-B", producer, context]))
    assert observed == json.loads(Path(fixture).read_bytes())
elif mode == "portable":
    executable, fixture = args
    entries = json.loads(Path(fixture).read_bytes())
    for entry in entries:
        cases = entry["cases"]
        if isinstance(cases, dict):
            for name, case in cases.items():
                observed = subprocess.check_output([executable, name], text=True).splitlines()
                assert observed == [str(case["result"]), *case["attributes"]], (name, observed, case)
        else:
            assert all(case["unchanged"] for case in cases)
            observed = subprocess.check_output([executable], text=True).splitlines()
            assert observed == ["unchanged", "unchanged"], observed
    print("Portable behavior matched the scoped observations for both firmware roles")
elif mode == "symbols":
    mangled, *paths = args
    for path in paths:
        records = subprocess.check_output(["nm", "--defined-only", path], text=True).splitlines()
        assert any(line.split()[-1] == mangled for line in records if line.strip())
else:
    raise SystemExit(mode)
