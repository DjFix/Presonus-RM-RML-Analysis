import argparse, json, subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--executable',required=True);a=p.parse_args()
symbols={line.split()[-1]:line.split()[0] for line in subprocess.check_output(['/usr/bin/nm','--defined-only',a.executable],text=True).splitlines() if line.split()}
expected=['_ZN8Presonus2UC15EventDispatcher'+v+'Ev' for v in ['C1','C2','D1','D2']]
for name in expected:assert name in symbols,name
assert '_ZN8Presonus2UC15EventDispatcherD0Ev' not in symbols,'invented virtual deleting destructor'
print(json.dumps({'passed':True,'symbols':{n:symbols[n] for n in expected},'host_aliases':{'C1_C2':symbols[expected[0]]==symbols[expected[1]],'D1_D2':symbols[expected[2]]==symbols[expected[3]]},'object_format':'ELF64 Linux, no extra leading underscore','scope':'names/scopes/constructor variants only; no ARM32 layout or binary ABI claim'}))
