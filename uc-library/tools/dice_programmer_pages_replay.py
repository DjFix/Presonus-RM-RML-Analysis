"""Replay frozen offline page witnesses and verify exact fixture input binding."""
import argparse,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--binary',type=Path,required=True);p.add_argument('--stdin',type=Path,required=True);p.add_argument('--fixture',type=Path,required=True);a=p.parse_args()
rows=list(map(json.loads,a.fixture.read_text().splitlines()));assert len(rows)==1904
codes=dict(dump=0,verify=1,write=2);lines=[]
for row in rows:
 c=row['input'];line=[codes[c['kind']],c['descriptor'],c['page']&0xffffffff,c['length']&0xffffffff,c['data'],len(c['steps'])]
 for step in c['steps']:line.extend([step['result']&0xffffffff,step['reply'] or '-'])
 line.extend([len(c['ticks']),*c['ticks']]);lines.append(' '.join(map(str,line)))
stdin='\n'.join(lines)+'\n';assert a.stdin.read_text()==stdin
r=subprocess.run([str(a.binary)],input=stdin,text=True,capture_output=True);assert r.returncode==0,r.stderr
actual=list(map(json.loads,r.stdout.splitlines()));assert len(actual)==len(rows)
for row,value in zip(rows,actual):assert row['expected']==value,(row['index'],row['expected'],value)
print('PASS 1904 original page witnesses, full original transaction/status composition; no device operations')
