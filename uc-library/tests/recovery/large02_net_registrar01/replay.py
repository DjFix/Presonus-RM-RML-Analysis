"""Replay bounded host observations against independently executed ARM fixtures."""
import argparse,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--driver',required=True);p.add_argument('--fixtures',required=True);a=p.parse_args();j=json.loads(Path(a.fixtures).read_text())
for c in j['cases']:
 argv=[a.driver,str(c['index']),str(c['count']),str(int(c['holes'])),str(c['storage'])]
 r=subprocess.run(argv,capture_output=True,text=True,check=True)
 actual=json.loads(r.stdout)
 assert actual==c['native']['observed'],dict(case=c,actual=actual)
print('replayed',len(j['cases']),'exact per-ELF cases; raw vptr writes retained separately, host ABI excluded')

r=subprocess.run([a.driver,'9','0','0','0'],capture_output=True,text=True,check=True)
assert json.loads(r.stdout)=={'borrowed_preserved':True,'singleton_stable':True}
print('independent borrowed-domain/singleton regression passed; no original symbol credit')
