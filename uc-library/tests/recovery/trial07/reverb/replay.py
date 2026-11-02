#!/usr/bin/env python3
"""Compare canonical C++ executable to independent original-ARM observations."""
import argparse,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--executable',required=True);p.add_argument('--fixtures',required=True);a=p.parse_args()
f=json.loads(Path(a.fixtures).read_text())
for i,c in enumerate(f['cases']):
 text=f"{c['target']} {c['index']} {c['value']} {c['count']} {c['before']} {c.get('presets',f['presets'])} {c['property']}\n"
 r=subprocess.run([a.executable],input=text,text=True,capture_output=True,check=True)
 lines=r.stdout.splitlines();actual={'after':lines[0],'result':int(lines[1]),'trace':[[int(v) for v in x.split()] for x in lines[2:]]}
 for field in actual:
  if actual[field]!=c[field]:
   if field=='after':
    b=bytes.fromhex(actual[field]);e=bytes.fromhex(c[field]);detail=[(hex(k),e[k:k+4].hex(),b[k:k+4].hex()) for k in range(0,len(b),4) if b[k:k+4]!=e[k:k+4]]
   else:detail=(c[field],actual[field])
   raise SystemExit(f'case {i} target {c["target"]} index {c["index"]} mismatch {field}: {detail}')
print(f"PASS {len(f['cases'])} original ARM fixture cases; exact state bytes, getValue bits and app/count call traces")
