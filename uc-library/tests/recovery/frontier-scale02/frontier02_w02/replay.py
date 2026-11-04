import argparse,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser(); p.add_argument('--executable',required=True);p.add_argument('--fixtures',required=True);a=p.parse_args()
f=json.loads(Path(a.fixtures).read_text())
for c in f['cases']:
 got=json.loads(subprocess.check_output([a.executable,*map(str,c['input'])],text=True))
 assert got[:3]==c['portable_expected'],(got,c)
 # These are independent existing Book source/provider observations, not native-base equivalence.
 assert got[3:]==[0,0,0,1,1,0],got
print(json.dumps({'cases':len(f['cases']),'domain':'FXBook call argument forwarding and borrowed identity stores; actual Book portable empty state'}))
