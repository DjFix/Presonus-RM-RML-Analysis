#!/usr/bin/env python3
import argparse,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--executable',required=True);p.add_argument('--fixtures',required=True);a=p.parse_args()
cases=json.loads(Path(a.fixtures).read_text())['cases']
keys=['method','arg','count','mask','lookup_mask','aux_count','sub_count','sub_present_mask','sub_link_mask','slave_mask','global_cached_component','global_cached_param']
def line(c):return ' '.join(str(int(x)) for x in [*[c[k] for k in keys],*c['params'],*c['scalars'],*c['state']])
r=subprocess.run([a.executable],input='\n'.join(line(c['input']) for c in cases)+'\n',text=True,capture_output=True,check=True)
lines=r.stdout.splitlines();assert len(lines)==len(cases),(len(lines),len(cases))
for i,(actual,c) in enumerate(zip(lines,cases)):
 got=list(map(int,actual.split()))
 if got!=c['observed']:raise SystemExit(f"Mismatch case {i} method {c['input']['method']}: got {got}; native {c['observed']}")
print(f"PASS {len(cases)} original ARM/C++ differential cases across ten targets: state, property entries and provider side effects")
