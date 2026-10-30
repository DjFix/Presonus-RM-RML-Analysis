"""Offline state and diagnostic comparison with original ARM-derived vectors."""
import argparse
from pathlib import Path
import subprocess
p = argparse.ArgumentParser()
p.add_argument('--executable', type=Path, required=True)
p.add_argument('--fixtures', type=Path, required=True)
p.add_argument('--expected', type=Path, required=True)
a = p.parse_args()
data = a.fixtures.read_text()
assert len(data.splitlines()) == 20700
result = subprocess.run([str(a.executable)], input=data, capture_output=True, text=True)
assert result.returncode == 0, result.stderr
assert result.stderr == 'PASS original_image_geometry_cases=20700\n'
assert result.stdout == a.expected.read_text()
print('PASS original_image_geometry_cases=20700 exact_state_and_diagnostics')
