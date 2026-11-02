#!/usr/bin/env python3
import argparse,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--executable',required=True);p.add_argument('--expected',required=True);a=p.parse_args()
r=subprocess.run(['nm','--defined-only',a.executable],check=True,text=True,capture_output=True)
actual={line.split()[-1] for line in r.stdout.splitlines() if line.split()}
expected=Path(a.expected).read_text().splitlines()
missing=set(expected)-actual
if missing:raise SystemExit('missing original ELF identities: '+str(sorted(missing)))
print(f'PASS {len(expected)} exact ELF original mangled symbols; Linux ELF has no Mach-O decoration')
