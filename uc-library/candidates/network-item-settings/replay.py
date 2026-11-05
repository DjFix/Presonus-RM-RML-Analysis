#!/usr/bin/env python3
import argparse, collections, json, subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--executable',required=True);p.add_argument('--fixtures',type=Path,required=True);p.add_argument('--method',type=int);a=p.parse_args()
rows=json.loads(a.fixtures.read_text())['cases'];rows=[r for r in rows if a.method is None or r['input']['method']==a.method];assert rows
lines=[]
for row in rows:
 c=row['input'];lines.append(' '.join([str(c[k]) for k in ('method','section','value_present','flags','live','dirty')]+[json.dumps(c[k]) for k in ('section_name','key','saved','identity')]))
r=subprocess.run([a.executable],input='\n'.join(lines)+'\n',text=True,capture_output=True);assert r.returncode==0,r.stderr
outputs=r.stdout.splitlines();assert len(outputs)==len(rows),(len(outputs),len(rows),r.stderr)
for i,(row,line) in enumerate(zip(rows,outputs)):
 got=json.loads(line);assert got==row['observed'],(i,row['input'],got,row['observed'])
print(json.dumps({'passed':True,'cases':len(rows),'per_method':dict(collections.Counter(r['input']['method'] for r in rows)),'domain':'native caller / actual CCL differential, terminated0..63 identity, flags, missing section/value, null clearing, dirty preservation, unrelated settings, saved truncation'}))
