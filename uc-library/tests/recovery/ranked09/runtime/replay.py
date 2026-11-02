import argparse
import json
import subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--executable',required=True);p.add_argument('--fixtures',required=True);a=p.parse_args()
f=json.loads(Path(a.fixtures).read_text());cases=f['cases']
r=subprocess.run([a.executable],input=''.join(f"{c['target']} {c['link']} {c['field']} {c['seed']}\n" for c in cases),text=True,capture_output=True,check=True)
lines=r.stdout.splitlines();assert len(lines)==len(cases)
for i,(c,line) in enumerate(zip(cases,lines)):
    words=line.split();result,after,count=map(int,words[:3]);rest=words[3:]
    trace=[[rest[j],int(rest[j+1]),int(rest[j+2])] for j in range(0,len(rest),3)]
    assert len(trace)==count
    assert (c['result'] is None or result==c['result']) and after==c['shutdown_word'] and trace==c['trace'], (i,c,line)
print(f"PASS {len(cases)} cases: original ARM register words and ordered guest data reads/writes; shutdown return excluded")
