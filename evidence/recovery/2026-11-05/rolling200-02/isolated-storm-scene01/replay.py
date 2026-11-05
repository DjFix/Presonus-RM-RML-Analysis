from pathlib import Path
import argparse, json, subprocess, hashlib
p=argparse.ArgumentParser();p.add_argument('--executable',required=True);p.add_argument('--fixtures',required=True);p.add_argument('--out',required=True);a=p.parse_args()
f=Path(a.fixtures); cases=json.loads(f.read_text())['cases']; results=[]
for c in cases:
 prefix='<null>' if c['prefix'] is None else c['prefix']
 argv=[a.executable,str(c['index']),prefix]
 run=subprocess.run(argv,text=True,capture_output=True,check=True)
 assert run.stdout==c['native_output'],(c,run.stdout)
 results.append({'argv':argv,'stdout':run.stdout,'exit':run.returncode})
Path(a.out).write_text(json.dumps({'passed':True,'case_count':len(cases),'fixture_sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'executable_sha256':hashlib.sha256(Path(a.executable).read_bytes()).hexdigest(),'executions':results},indent=2)+'\n')
print('Pinned-provider C++ replay passed:',len(cases),'cases, 1 function')
