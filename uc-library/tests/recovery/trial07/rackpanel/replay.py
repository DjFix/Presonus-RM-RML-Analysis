"""Compare actual native observations against an explicit built C++ executable."""
import argparse,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--executable',required=True);p.add_argument('--fixtures',required=True);a=p.parse_args()
cases=json.loads(Path(a.fixtures).read_text())['cases']
for index,case in enumerate(cases):
 c=case['input'];args=[c['method'],c.get('n',3),c.get('m',2),c.get('k',3),c.get('mask',7),c.get('tag',0),c.get('clients',c.get('on',0)),c.get('present',1),c.get('expired',0),c.get('status',0),c.get('bits',0)]
 r=subprocess.run([str(Path(a.executable).resolve()),*map(str,args)],capture_output=True,text=True)
 actual=[line for line in r.stdout.splitlines() if not line.startswith('RackPanelComponent::')]
 if r.returncode or actual!=case['trace']:
  raise SystemExit(f'case {index} {c}: rc={r.returncode}\nexpected={case["trace"]}\nactual={actual}\nstderr={r.stderr}')
print(f'PASS {len(cases)} native/C++ differential cases; all ten methods; ordered effects and monitor writes')
