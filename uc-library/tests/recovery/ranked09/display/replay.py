import json,subprocess,sys
from pathlib import Path
f=json.loads(Path(sys.argv[2]).read_text()); cases=f['cases']
r=subprocess.run([sys.argv[1]],input=''.join(str(c['input'])+'\n' for c in cases),text=True,capture_output=True,check=True)
assert list(map(int,r.stdout.split()))==[c['result'] for c in cases]
print(f"{len(cases)} original ARM word-load cases replayed; no pointee dereferences or lifecycle claims")
