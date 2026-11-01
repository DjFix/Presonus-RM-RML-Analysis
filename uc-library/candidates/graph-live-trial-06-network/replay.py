#!/usr/bin/env python3
"""Compare regression observations directly with an explicit built executable.
Runtime reads only regression fixtures, never operational handoff/proof metadata.
"""
import argparse,json,subprocess,sys,collections
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--executable',required=True);p.add_argument('--fixtures',type=Path,required=True);p.add_argument('--method',type=int);a=p.parse_args()
rows=json.loads(a.fixtures.read_text());rows=[r for r in rows if a.method is None or r['input'][0]==a.method]
assert rows
proc=subprocess.run([a.executable],input=''.join(' '.join(map(str,r['input']))+'\n' for r in rows),text=True,capture_output=True)
if proc.returncode:print(proc.stderr);raise SystemExit(proc.returncode)
actual=proc.stdout.splitlines();assert len(actual)==len(rows),(len(actual),len(rows))
for i,(r,s) in enumerate(zip(rows,actual)):
 got=json.loads(s)
 if got!=r['observed']:
  print('MISMATCH',i,'input',r['input']);print('native',json.dumps(r['observed'],sort_keys=True));print('C++',json.dumps(got,sort_keys=True));raise SystemExit(1)
print(json.dumps({'passed':True,'cases':len(rows),'per_method':dict(collections.Counter(r['input'][0] for r in rows)),'domain':'bounded initialized state; exact original target bodies with explicit app/provider boundary models, real CCL C++ containers/parameters and real UC event sender'},sort_keys=True))
