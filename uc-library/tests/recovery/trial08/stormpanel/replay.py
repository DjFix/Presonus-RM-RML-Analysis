"""Compare a caller-selected C++ executable with independent ARM observations."""
import argparse,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--executable',required=True);p.add_argument('--fixtures',type=Path,required=True);a=p.parse_args()
cases=json.loads(a.fixtures.read_text())['cases']
for n,c in enumerate(cases):
 result=subprocess.run([a.executable,*[str(c[k]) for k in ['target','index','flag','scenario']]],check=True,capture_output=True,text=True)
 actual=json.loads(result.stdout)
 if actual!=c['trace']:
  raise SystemExit(f"Case {n} target {c['target']}: expected {c['trace']}, got {actual}")
print(f'PASS: {len(cases)} ARM/C++ trace comparisons across ten original targets')
