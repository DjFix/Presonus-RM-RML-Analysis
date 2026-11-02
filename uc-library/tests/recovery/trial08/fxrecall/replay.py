import argparse,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--executable',required=True);p.add_argument('--fixtures',required=True);a=p.parse_args()
fixtures=json.loads(Path(a.fixtures).read_text())
for i,c in enumerate(fixtures):
 args=[a.executable,c['method'],str(c['slot']),str(c['loaded']),str(c['type']),str(c['effect']),c['path'],str(c['arg']),str(c['msg']),str(c['children']),str(c['registered']),str(int(c['exists'])),str(int(c['cache'])),str(i),c.get('type_name','unused')]
 out=subprocess.check_output(args,text=True);actual={'trace':[]}
 for line in out.splitlines():
  k,v=line.split('=',1)
  if k=='trace':actual[k].append(v)
  elif k in ['slot']:actual[k]=float(v)
  elif k in ['return','registered','idle']:actual[k]=int(v)
  else:actual[k]=v
 assert actual==c['expected'],(i,c['method'],actual,c['expected'])
print(f'PASS {len(fixtures)} original ARM versus portable C++ cases')
