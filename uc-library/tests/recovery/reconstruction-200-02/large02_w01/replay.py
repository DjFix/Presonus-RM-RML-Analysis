"""Compare optimized C++ observations to sealed independent native fixtures."""
import argparse,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--executable',required=True);p.add_argument('--fixtures',required=True);a=p.parse_args()
data=json.loads(Path(a.fixtures).read_text())
EXTRA=['eqpage','geqcount','bankOffset','secondaryInputs','channelLink','busLink','busMain','channelMain','channelMainPresent','busPresent','groupPresent','meter','bankSwitchBlocked','tag','mix','monoPresent','usernamePresent']
DEFAULT=[0,4,3,0,0,0,0,0,0,1,1,0,0,0,33,0,1]
for number,case in enumerate(data['cases']):
 v=case['args'];argv=[a.executable,str(case['index']),str(int(v.get('controller',True))),str(v.get('radio',-1)),str(int(v.get('present',True))),str(int(v.get('component',True))),v.get('username','Bus') if case['index']==1 else v.get('text',''),str(int(v.get('long',False))),str(v.get('saved',0)),str(int(v.get('mixer',False))),str(int(v.get('secondary',False))),','.join(str(int(v.get(key,default))) for key,default in zip(EXTRA,DEFAULT))]
 argv += [str(v.get('values',{}).get(str(1000 if case['index']==15 and tag==255 else tag),0)) for tag in range(256)]
 proc=subprocess.run(argv,text=True,capture_output=True)
 if proc.returncode:raise RuntimeError(f'case {number}: process {proc.returncode} {proc.stderr}')
 actual=json.loads(proc.stdout)
 if actual!=case['expected']:raise RuntimeError(f'case {number}: {case} actual {actual}')
print(json.dumps({'passed':True,'cases':len(data['cases']),'domain':'per-fixture exact native provider-boundary outputs and traces; optimized C++ with actual CCL parameters/vector/timer'}))
