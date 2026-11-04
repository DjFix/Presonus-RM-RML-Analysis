import argparse,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--executable',required=True);p.add_argument('--fixtures',required=True);a=p.parse_args()
f=json.loads(Path(a.fixtures).read_text())
for i,c in enumerate(f['cases']):
 v=c['inputs'];argv=[a.executable,str(v['count']),str(int(v['line'])),','.join(map(str,v['channels'])),str(v['mutate_at']),str(v['mutate_count']),str(int(v['feedback']))]
 actual=json.loads(subprocess.check_output(argv,text=True).strip().splitlines()[-1]);assert actual==c['observed'],(i,v,actual,c['observed'])
print(json.dumps({'passed':True,'cases':len(f['cases']),'domain':'real CCL findChild/parameter lookup/changed; signed count and observer mutations; ordered traversal, controller/observer notifications, unchanged values'}))

assert json.loads(subprocess.check_output([a.executable,"--guards"],text=True))=={"source_port_guards":2}
print("source-port-only error adaptations passed; native null-parameter execution excluded")
