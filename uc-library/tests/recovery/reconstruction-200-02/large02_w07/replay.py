#!/usr/bin/env python3
import argparse,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--executable',required=True);p.add_argument('--fixtures',required=True);a=p.parse_args()
cases=json.loads(Path(a.fixtures).read_text())['cases']
failed=[]
for c in cases:
 r=subprocess.run([a.executable,str(c['id']),str(c['variant'])],text=True,capture_output=True)
 actual=[int(x) for x in r.stdout.split()] if r.returncode==0 else {'exit':r.returncode,'stderr':r.stderr}
 if actual!=c['expected']:failed.append({'id':c['id'],'variant':c['variant'],'expected':c['expected'],'actual':actual})
print(json.dumps({'cases':len(cases),'failed':failed},indent=2))
raise SystemExit(bool(failed))
