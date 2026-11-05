#!/usr/bin/env python3
import argparse,json,subprocess,collections
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--executable',required=True);p.add_argument('--fixtures',required=True,type=Path);p.add_argument('--method',type=int);a=p.parse_args()
rows=json.loads(a.fixtures.read_text())['cases'];rows=[r for r in rows if a.method is None or r['input']['method']==a.method];assert rows
lines=[]
for r in rows:
 c=r['input'];lines.append(' '.join(str(c.get(k,d)) or '-' for k,d in [('method',0),('index',0),('section',0),('saved',''),('flags',0),('key','selectedDAW'),('section_name','networksetup'),('count',0),('optional',0),('value',0),('present',1)]))
r=subprocess.run([a.executable],input='\n'.join(lines)+'\n',text=True,capture_output=True);assert r.returncode==0,r.stderr
out=r.stdout.splitlines();assert len(out)==len(rows),(len(out),len(rows),r.stderr)
for i,(row,s) in enumerate(zip(rows,out)):
 got=json.loads(s)
 expected=row['observed']
 if row['input']['method']==3:expected=dict(expected,events=[e for e in expected['events'] if e[0]!='active'])
 assert got==expected,(i,row['input'],got,expected)
print(json.dumps({'passed':True,'cases':len(rows),'per_method':dict(collections.Counter(r['input']['method'] for r in rows))}))
