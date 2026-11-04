import argparse,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--binary',required=True);p.add_argument('--fixtures',required=True);a=p.parse_args()
d=json.loads(Path(a.fixtures).read_text());fail=[]
for case in d['cases']:
 run=subprocess.run([a.binary,*map(str,case['argv'])],capture_output=True,text=True)
 try:got=list(map(int,run.stdout.split()))
 except ValueError:got=run.stdout
 if run.returncode or got!=case['expected']:fail.append({'argv':case['argv'],'expected':case['expected'],'got':got,'returncode':run.returncode,'stderr':run.stderr})
if fail:print(json.dumps(fail,indent=2));raise SystemExit(1)
print(json.dumps({'cases':len(d['cases']),'status':'pass','domain':'native app state projections with explicit external stubs versus actual pinned CCL-backed optimized source port; null/non-null client with actual message serialization, typed origins and route provider; no hardware/ARM ABI claim'}))
