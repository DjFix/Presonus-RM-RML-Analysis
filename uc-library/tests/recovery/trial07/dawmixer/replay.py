#!/usr/bin/env python3
"""Compare canonical built C++ executable directly with original ARM observations."""
import argparse,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--executable',required=True);p.add_argument('--fixtures',required=True);a=p.parse_args()
f=json.loads(Path(a.fixtures).read_text());cases=f['cases']
request=''.join(' '.join(map(str,c['input']))+'\n' for c in cases)
r=subprocess.run([str(Path(a.executable).resolve())],input=request,text=True,capture_output=True,check=True)
lines=r.stdout.splitlines()
assert len(lines)==len(cases),(len(lines),len(cases),r.stderr)
for i,(c,line) in enumerate(zip(cases,lines)):
 expected=','.join(map(str,c['observed']))+''.join(';'+e for e in c['events'])
 assert line==expected,{'case':i,'input':c['input'],'actual':line,'native':expected}
print(f'{len(cases)} original ARM/C++ differential cases passed across ten methods; state, target identities, parameter writes/edit flags and ordered app call traces')
