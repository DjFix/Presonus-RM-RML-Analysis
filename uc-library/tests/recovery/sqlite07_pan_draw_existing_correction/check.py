"""Compare a freshly executed ARM gate matrix with the CS18-linked renderer."""

import json
from pathlib import Path
import subprocess
import sys

from native import run

fixtures = json.loads(Path(__file__).with_name("fixtures.json").read_text())
cases, traces = run()
assert cases == fixtures["cases"], (cases, fixtures["cases"])
result = subprocess.check_output([sys.argv[1]], text=True)
rows = [tuple(map(int, line.split())) for line in result.splitlines()]
expected = [
    (case["vertical_bit"], case["view_disabled_bit"], case["parameter_enabled"],
     2 if case["gate"] == "reached_render_path" else 0)
    for case in cases
]
assert rows == expected, (rows, expected)
print(json.dumps(dict(cases=cases, arm_pcs=traces, portable_rows=rows), indent=2))
