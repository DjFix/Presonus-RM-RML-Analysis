import argparse,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--executable',required=True);p.add_argument('--fixtures',required=True);a=p.parse_args()
f=json.loads(Path(a.fixtures).read_text());cases=f['cases'];data=''.join(f"{c['method']} {len(c['input'])} "+' '.join(map(str,c['input']))+'\n' for c in cases)
r=subprocess.run([a.executable],input=data,text=True,capture_output=True);assert r.returncode==0,(r.returncode,r.stderr)
lines=r.stdout.splitlines();assert len(lines)==len(cases),(len(lines),len(cases))
for n,(case,line) in enumerate(zip(cases,lines)):
 v=list(map(int,line.split()));assert v[0]==len(v)-1
 assert v[1:]==case['expected'],dict(index=n,method=case['method'],input=case['input'],actual=v[1:],expected=case['expected'])
print(json.dumps(dict(passed=True,cases=len(cases),methods=sorted({c['method'] for c in cases}))))
