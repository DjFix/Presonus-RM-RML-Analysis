#!/usr/bin/env python3
"""Compare supplied built executable directly against independent ARM fixtures."""
import argparse,json,struct,subprocess
from pathlib import Path

def main():
 p=argparse.ArgumentParser();p.add_argument('--executable',required=True);p.add_argument('--fixtures',required=True);p.add_argument('--packet',type=int);a=p.parse_args()
 d=json.loads(Path(a.fixtures).read_text());count=0
 for n,c in enumerate(d['cases']):
  if a.packet and c['packet']!=a.packet:continue
  cfg={}
  for k,v in c['input'].items():
   if isinstance(v,list):cfg[k.replace('_members','_count')]=len(v);cfg[k.replace('_members','_mask')]=sum(int(x)<<i for i,x in enumerate(v))
   elif k in ['value','remote_value']:cfg[k]=struct.unpack('<I',struct.pack('<f',v))[0]
   else:cfg[k]=int(v)
  argv=[a.executable,'--case',str(c['packet'])]+[f'{k}={v}' for k,v in cfg.items()]
  r=subprocess.run(argv,text=True,capture_output=True)
  expected=['trace\t'+'\t'.join(map(str,t)) for t in c['trace']]
  if c['packet']==8:expected.append('return\t'+str(c['return']))
  expected+=['daw\t'+str(c['daw']),'sound\t'+str(c['sound'])]
  expected+=['old'+''.join('\t'+str(int(v)) for v in c['old_members']),'new'+''.join('\t'+str(int(v)) for v in c['new_members'])]
  if c['packet']==2:
   for tag in range(6,14):
    if str(tag) in c['aliases']:
     expected.append(f"alias\t{tag}\t{c['aliases'][str(tag)]}")
     if tag==6:expected.append('feedback\t6\t'+str(c['feedback'].get(str(tag),0)))
  actual=r.stdout.splitlines()
  if r.returncode or actual!=expected:
   print(json.dumps({'case':n,'argv':argv,'expected':expected,'actual':actual,'returncode':r.returncode,'stderr':r.stderr},indent=2));return 1
  count+=1
 print(json.dumps({'passed':True,'cases':count,'domain':'Original ARM branch paths, composed Capture methods, parameter writes, alias final identities, member vectors and app call traces; external services hooked'}));return 0
if __name__=='__main__':raise SystemExit(main())
