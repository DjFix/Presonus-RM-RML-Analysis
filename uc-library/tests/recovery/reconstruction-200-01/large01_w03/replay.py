import argparse,json,subprocess
from pathlib import Path
from oracle import generate
p=argparse.ArgumentParser();p.add_argument('--executable',required=True);p.add_argument('--fixtures',required=True);p.add_argument('--native-out');a=p.parse_args()
f=json.loads(Path(a.fixtures).read_text());native=generate()
if native != f:raise SystemExit('Fresh native oracle differs from sealed fixture')
if a.native_out:Path(a.native_out).write_text(json.dumps(native,indent=2)+'\n')
text=''.join(' '.join(map(str,[c['method']]+c['input']))+'\n' for c in f['cases'])
r=subprocess.run([a.executable],input=text,text=True,capture_output=True,check=True)
lines=r.stdout.splitlines();assert len(lines)==len(f['cases']),(len(lines),len(f['cases']))
for i,(line,c) in enumerate(zip(lines,f['cases'])):
 got=list(map(int,line.split()))
 if got!=c['expected']:raise SystemExit(f'case {i} {c} actual {got}')
print(json.dumps({'passed':True,'case_count':len(lines),'domain':f['limitations']}))
