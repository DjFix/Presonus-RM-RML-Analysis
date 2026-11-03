import argparse,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--exe',required=True);p.add_argument('--fixtures',required=True);a=p.parse_args()
cases=json.loads(Path(a.fixtures).read_text())['cases']
import oracle
for c in cases:
 observed=oracle.observe(oracle.ROOT/c['packet'],c['op'],c['present'],c['value'])
 assert all(observed[k]==c[k] for k in ['result','events','memory_unchanged','range'])
data=''.join(f"{c['op']} {c['present']} {c['value']}\n" for c in cases)
r=subprocess.run([a.exe],input=data,text=True,capture_output=True,check=True)
actual=r.stdout.splitlines();expected=[f"{c['result']} {''.join(c['events']) or '-'}" for c in cases]
assert actual==expected,(actual,expected,r.stderr)
print('portable/native boundary replay passed',len(cases),'cases; app memory unchanged in native oracle; return and call order matched')
