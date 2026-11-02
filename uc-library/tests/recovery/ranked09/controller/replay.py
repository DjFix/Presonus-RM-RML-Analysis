import json,subprocess,sys
from pathlib import Path
f=json.loads(Path(sys.argv[2]).read_text());cases=f['cases']
data=''.join(f"{c['old']} {c['incoming']} {c['dirty']}\n" for c in cases)
r=subprocess.run([sys.argv[1]],input=data,text=True,capture_output=True,check=True)
actual=[list(map(int,x.split())) for x in r.stdout.splitlines()]
expected=[[c['rate'],c['dirty_after']] for c in cases]
assert actual==expected, next(((i,a,e) for i,(a,e) in enumerate(zip(actual,expected)) if a!=e),'count mismatch')
print(f"{len(cases)} native/C++ cases match; finite/raw NaN/infinity/subnormal/signed-zero inputs; dirty and exact rate bits")
