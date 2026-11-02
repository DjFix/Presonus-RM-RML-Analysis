#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
import subprocess
p=argparse.ArgumentParser();p.add_argument('--executable',required=True);p.add_argument('--fixtures',required=True);a=p.parse_args()
names={line.split()[-1] for line in subprocess.check_output(['nm','--defined-only',a.executable],text=True).splitlines() if line.split()}
originals=[r['mangled'] for r in json.loads(Path(a.fixtures).read_text())['ranges']]
missing=[x for x in originals if x not in names]
if missing:raise AssertionError(missing)
print(json.dumps({'matched':originals,'scope':'ELF host name/scope checks only; unencoded return/inheritance/layout/ARM ABI unresolved'}))
