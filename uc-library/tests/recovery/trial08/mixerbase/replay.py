#!/usr/bin/env python3
"""Compare a supplied built portable executable with original ARM observations."""
import argparse
import json
import subprocess

p = argparse.ArgumentParser()
p.add_argument('--executable', required=True)
p.add_argument('--fixtures', required=True)
a = p.parse_args()
cases = json.load(open(a.fixtures))['cases']
for c in cases:
    actual = subprocess.check_output([a.executable, str(c['method']), str(c['value']), str(c['initial_flag'])], text=True).strip()
    expected = str(c['expected']) + '\n' + ' '.join(map(str, c['observed_state']))
    if actual != expected:
        raise SystemExit(f"mismatch: {c}: {actual}")
print(f"PASS {len(cases)} original ARM differential cases")
