#!/usr/bin/env python3
import argparse,json,subprocess,struct
from pathlib import Path
OFF=[140]+list(range(260,320,4))
def stream(c):
 vals=[c['target']]+[int(c.get(k,False)) for k in ('slave','master','merge','blocked','expired','global','cast_fail')]+[c.get('index',0),c.get('count',0),c.get('value',0)]+c.get('args',[0,0,0])+[c.get('solos',{}).get(str(k),0) for k in (0,4,-1)]
 vals += [len(c.get('missing',[]))]+c.get('missing',[])
 for off in OFF:
  v=c.get('values',{}).get(str(off),0);vals +=[v,c.get('normalized',{}).get(str(off),v)]
 for off in OFF:
  ls=c.get('lists',{}).get(str(off),[]);vals+=[len(ls)]+[json.dumps(s) for s in ls]
 vals+=c.get('cache',[0]*13)
 ch=c.get('channels',[]);vals+=[len(ch)]+ch
 vals += [json.dumps(s) for s in c.get('labels',['Aux','Main','Digital','Solo','Tape'])]
 vals += [json.dumps(c.get('separator','/'))]
 return ' '.join(map(str,vals))+'\n'
def canonical(o):
 o=dict(o);o['trace']=[x for x in o['trace'] if x[0] not in ('lookup','remove','append','range','select','timer')]
 return o
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--executable',required=True);p.add_argument('--fixtures',required=True);a=p.parse_args();cases=json.loads(Path(a.fixtures).read_text());counts={}
 for i,row in enumerate(cases):
  result=subprocess.run([str(Path(a.executable).resolve())],input=stream(row['input']),text=True,capture_output=True,check=True)
  actual=json.loads(result.stdout);expected=canonical(row['original'])
  if actual!=expected:
   print('Mismatch',i,row['input']);print('expected',expected);print('actual',actual);raise SystemExit(1)
  t=row['input']['target'];counts[t]=counts.get(t,0)+1
 print('Differential original ARM / portable C++ cases:',len(cases),'per target:',counts)
