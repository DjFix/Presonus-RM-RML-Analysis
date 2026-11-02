import argparse,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--executable',required=True);p.add_argument('--fixtures',required=True);a=p.parse_args()
f=json.loads(Path(a.fixtures).read_text());fail=[]
for case in f['cases']:
 r=subprocess.run([a.executable,*map(str,case['input'])],capture_output=True,text=True)
 try:actual=json.loads(r.stdout.splitlines()[-1])
 except Exception:raise RuntimeError((case['id'],r.returncode,r.stdout,r.stderr))
 if r.returncode or actual!=case['expected']:
  fail.append(case['id']);print('mismatch',case['id'],'input',case['input']);print('expected',json.dumps(case['expected']));print('actual',json.dumps(actual))
print('surface network differential cases',len(f['cases']),'failures',len(fail))
raise SystemExit(bool(fail))
