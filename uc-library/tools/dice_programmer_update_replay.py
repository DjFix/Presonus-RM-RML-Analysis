"""Replay offline erase/update orchestration with exact retained inputs."""
import argparse,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--binary',type=Path,required=True);p.add_argument('--stdin',type=Path,required=True);p.add_argument('--fixture',type=Path,required=True);a=p.parse_args()
rows=list(map(json.loads,a.fixture.read_text().splitlines()));assert len(rows)==658;codes=dict(all=0,sector=1,update=2);lines=[]
for row in rows:
 c=row['input'];lines.append(' '.join(map(str,[codes[c['kind']],c['sector']&0xffffffff,c['length'],c['initial_wait'],c['enabled'],c['transaction'],c['final_wait'],c['erase_error_at'],c['erase_error'],c['write_error_at'],c['write_error'],c['verify_error_at'],c['verify_error'],c['image']])))
stdin='\n'.join(lines)+'\n';assert a.stdin.read_text()==stdin;r=subprocess.run([str(a.binary)],input=stdin,text=True,capture_output=True);assert r.returncode==0,r.stderr
actual=list(map(json.loads,r.stdout.splitlines()));assert len(actual)==len(rows)
for row,value in zip(rows,actual):assert row['expected']==value,(row['index'],row['expected'],value)
print('PASS 658 original erase/update host-body traces; all physical operations intercepted')
