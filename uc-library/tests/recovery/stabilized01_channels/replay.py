import argparse,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--executable',required=True);p.add_argument('--fixtures',required=True);a=p.parse_args()
f=json.loads(Path(a.fixtures).read_text());cases=f['cases']
r=subprocess.run([a.executable],input='\n'.join(c['line'] for c in cases)+'\n',text=True,capture_output=True,check=True)
lines=r.stdout.splitlines();assert len(lines)==len(cases),(len(lines),len(cases),r.stderr)
for i,(text,c) in enumerate(zip(lines,cases)):
 observed=c['observed'];actual=text if isinstance(observed,str) else int(text) if isinstance(observed,int) else list(map(int,text.split()))
 assert actual==observed,(i,c['inputs'],actual,observed)
print(json.dumps({'passed':True,'cases':len(cases),'original_ranges':len(f['ranges']),'domain':'Initialized real CCL Component trees, typed cast adaptation and NumericParam values; cached path and complete all9-group null-cache scan'}))
