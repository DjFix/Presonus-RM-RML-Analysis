#!/usr/bin/env python3
import argparse,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--binary',required=True);p.add_argument('--fixtures',required=True);a=p.parse_args()
r=subprocess.run(['nm','-g','--defined-only',a.binary],text=True,capture_output=True,check=True)
symbols={line.split()[-1] for line in r.stdout.splitlines() if line.split()}
fixture=json.loads(Path(a.fixtures).read_text())
primary=fixture['original_targets'];helpers=fixture['helper_ranges'];originals=primary+helpers
missing=[x['mangled'] for x in originals if x['mangled'] not in symbols]
print(json.dumps({'checked_original_identities':len(primary),'checked_helper_identities':len(helpers),'missing':missing,'object_format':'Linux ELF; no Mach-O leading underscore decoration','scope':'Exact mangling only, no original return/layout/ARM ABI assertion'},indent=2))
raise SystemExit(bool(missing))
