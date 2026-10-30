"""Replay frozen receiver constructor/post witnesses; transport is intercepted."""
import argparse
import json
from pathlib import Path
import subprocess

p = argparse.ArgumentParser()
p.add_argument('--binary', type=Path, required=True)
p.add_argument('--fixture', type=Path, required=True)
p.add_argument('--stdin', type=Path, required=True)
a = p.parse_args()
rows = [json.loads(line) for line in a.fixture.read_text().splitlines()]
assert len(rows) == 5120
expected = ''.join(f"{r['kind']} {int(r['lazy'])} {r['before']} {r['packet']}\n" for r in rows)
assert a.stdin.read_text() == expected
r = subprocess.run([str(a.binary), str(a.stdin)], capture_output=True, text=True)
print(r.stdout, end='')
print(r.stderr, end='')
assert r.returncode == 0
assert 'PASS c1=512 c2=512 post=4096 actual_ccl_lazy_registry=1' in r.stdout
