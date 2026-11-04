import argparse,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--executable',required=True);a=p.parse_args()
rows=subprocess.check_output(['/usr/bin/nm','--defined-only',a.executable],text=True).splitlines();symbols={r.split()[-1]:r.split()[0] for r in rows if r.split()}
originals=['_ZN8Presonus2UC14AdapterHandlerC1Ev','_ZN8Presonus2UC14AdapterHandlerC2Ev']
for name in originals:assert name in symbols,name
print(json.dumps(dict(passed=True,symbols={s:symbols[s] for s in originals},decoration='Linux ELF none',scope='Encoded name and case-sensitive namespace only; original layout/ARM ABI unresolved')))
