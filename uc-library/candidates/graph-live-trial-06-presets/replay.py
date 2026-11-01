#!/usr/bin/env python3
import argparse,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--executable',required=True);p.add_argument('--fixtures',required=True);a=p.parse_args()
cases=json.loads(Path(a.fixtures).read_text())['cases'];totals={}
for n,case in enumerate(cases):
 r=subprocess.run([str(Path(a.executable).resolve()),*map(str,case['argv'])],capture_output=True,text=True,check=True)
 actual=json.loads(r.stdout)
 if actual!=case['expected']:
  print(json.dumps(dict(case=n,argv=case['argv'],expected=case['expected'],actual=actual),indent=2));raise SystemExit(1)
 method=case['argv'][0];totals[method]=totals.get(method,0)+1
print(json.dumps(dict(passed=len(cases),per_target=totals,domain='fixed and seeded bounded state/branch cases; original external calls stubbed and captured')))
