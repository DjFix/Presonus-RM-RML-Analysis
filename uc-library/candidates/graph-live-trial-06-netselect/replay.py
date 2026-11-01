#!/usr/bin/env python3
"""Compare explicit built C++ executable with independent original ARM fixtures."""
import argparse,json,subprocess
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--executable',required=True);ap.add_argument('--fixtures',required=True);a=ap.parse_args()
d=json.loads(Path(a.fixtures).read_text());cases=d['cases'];p=subprocess.run([str(Path(a.executable).resolve())],input=''.join(' '.join(map(str,c['input']))+'\n' for c in cases),text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
if p.returncode:raise SystemExit(f'C++ failed {p.returncode}: {p.stderr}\n{p.stdout[-2000:]}')
lines=[x[3:].split() for x in p.stdout.splitlines() if x.startswith('OBS')]
if len(lines)!=len(cases):raise SystemExit(f'observation count {len(lines)} != {len(cases)}')
for i,(line,c) in enumerate(zip(lines,cases)):
 if line!=c['observed']:raise SystemExit(f'case {i} input={c["input"]}\nARM={c["observed"]}\nC++={line}')
counts={str(t):sum(c['input'][0]==t for c in cases) for t in range(1,11)}
print(json.dumps({'passed':True,'case_count':len(cases),'per_target':counts,'scope':'Original target instruction executions with explicit offline application/Core call boundaries versus portable C++ semantic call traces, parameter writes, return/selected strings. No hardware or ARM object ABI claim.'},sort_keys=True))
