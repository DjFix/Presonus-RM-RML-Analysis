import argparse,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--executable',required=True);p.add_argument('--fixtures',required=True);a=p.parse_args()
f=json.loads(Path(a.fixtures).read_text());cases=f['cases'];data=''.join(' '.join(map(str,c['input']))+'\n' for c in cases)
result=subprocess.run([a.executable],input=data,text=True,capture_output=True,check=True);lines=result.stdout.splitlines();assert len(lines)==len(cases),(len(lines),len(cases))
for c,line in zip(cases,lines): assert c['output']==line,(c['input'],c['output'],line)
print(json.dumps({'cases':len(cases),'domain':f['domain'],'result':'passed'}))
