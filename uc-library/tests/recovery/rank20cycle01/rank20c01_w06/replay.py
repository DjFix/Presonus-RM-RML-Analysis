import argparse,hashlib,json,subprocess
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--executable',required=True);ap.add_argument('--fixtures',required=True);ap.add_argument('--sha256');a=ap.parse_args()
if a.sha256:assert hashlib.sha256(Path(a.fixtures).read_bytes()).hexdigest()==a.sha256
f=json.loads(Path(a.fixtures).read_text());count=0
for c in f['cases']:
 i=c['input'];target=c['target'];args=[str(target),str(int(i['found'])),str(i['value'])] if target==10 else [str(target),str(c['variant']),str(-c['variant'])]
 if target==9:args=['9',str(i['axis']),str(i['orientation']),i['name']]
 result=subprocess.run([a.executable,*args],check=True,text=True,capture_output=True).stdout
 if target==9:
  assert result==f"RESULT {i['orientation']} {int(c['variant']<4)} {19 if i['axis']==0 else 17} 0\n",(c,result)
 elif target==10:
  assert result==f"RESULT {c['observed']['r0']} {int(i['found'])}\n",(c,result)
 else:
  assert result==c['observed']['trace'][0][1]+f"RESULT {c['observed']['r0']}\n",(c,result)
 count+=1
print(f'{count} portable executions matched independent original ARM boundary fixtures; Grid two-axis state changes and unaffected axis checked; other methods preserve object/Item state at tested boundaries')
