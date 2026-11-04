import argparse,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--executable',required=True);p.add_argument('--fixtures',required=True);a=p.parse_args()
r=json.loads(Path(a.fixtures).read_text())
for i,c in enumerate(r['cases']):
 k=c['kind'];v=c['inputs'];args=[a.executable,k]
 if k=='static':args+=[str(v['mode'])]
 elif k=='route':args+=[str(int(v['present'])),str(v['index'])]
 elif k=='spectrum':args+=[str(v['a']),str(v['b'])]
 elif k=='destructor':args+=[str(c['address']),str(int(v['present']))]
 elif k=='param':args+=[str(v['msg']),str(int(v['own'])),v['name'],str(v['value'])]
 s=subprocess.check_output(args,text=True);actual=json.loads(s.strip().splitlines()[-1]);expected={x:y for x,y in c['observed'].items() if x not in ('vptr_writes','memory_writes')}
 assert actual==expected,(i,c,actual,expected)
print(json.dumps({'cases':len(r['cases']),'passed':True,'domain':'original ARM packet traces; null/present listeners; modes; signed spectrum inputs; original destructor variants; actual pinned Core child cleanup; native vptr observations retained separately, never host destroyed-object reads'}))
