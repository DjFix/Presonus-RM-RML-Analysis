#!/usr/bin/env python3
"""Compare a specified compiled C++ executable directly to original observations."""
import argparse,json,subprocess,collections,hashlib
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--executable',required=True);p.add_argument('--fixtures',required=True);p.add_argument('--fixture-sha256');a=p.parse_args()
if a.fixture_sha256 and hashlib.sha256(Path(a.fixtures).read_bytes()).hexdigest()!=a.fixture_sha256:raise SystemExit('fixture SHA-256 mismatch')
x=json.loads(Path(a.fixtures).read_text());counts=collections.Counter();fail=[]
for i,case in enumerate(x['cases']):
 r=subprocess.run([str(Path(a.executable).resolve()),*map(str,case['input'])],text=True,capture_output=True)
 counts[case['input'][0]]+=1
 if r.returncode or r.stdout.strip()!=case['output']:
  fail.append({'case':i,'input':case['input'],'expected':case['output'],'actual':r.stdout.strip(),'stderr':r.stderr,'returncode':r.returncode})
print(json.dumps({'cases':sum(counts.values()),'per_target':dict(counts),'failures':len(fail),'examples':fail[:10]},indent=2))
raise SystemExit(bool(fail))
