#!/usr/bin/env python3
"""Compare a supplied built executable directly with original ARM fixtures."""
import argparse
import json
import math
import struct
import subprocess
from pathlib import Path

def floating(v):return struct.unpack('<f',struct.pack('<I',v))[0]
def main():
 p=argparse.ArgumentParser();p.add_argument('--executable',required=True);p.add_argument('--fixtures',required=True);p.add_argument('--method',type=int);args=p.parse_args()
 fixture=json.loads(Path(args.fixtures).read_text());count=0
 for case in fixture['cases']:
  if args.method and case['input'][0]!=args.method:continue
  run=subprocess.run([str(Path(args.executable).resolve())],input=' '.join(map(str,case['input'])),text=True,capture_output=True)
  if run.returncode:raise RuntimeError(f"{case['id']}: exit {run.returncode}: {run.stderr}")
  actual=list(map(int,run.stdout.split()));expected=case['expected']
  # Exact final state, return and observable application event words.
  bad=[]
  if len(actual)!=len(expected):bad.append(['length',len(actual),len(expected)])
  else:
   for i,(a,e) in enumerate(zip(actual,expected)):
    if a==e:continue
    bad.append([i,a,e])
  if bad:raise AssertionError(f"{case['id']} method {case['input'][0]} mismatch {bad}; actual={actual}; native={expected}; input={case['input']}")
  count+=1
 assert count
 print(json.dumps({'status':'passed','cases':count,'method':args.method,'domain':'Native target state/return/app trace differential; CCL source-provider getters excluded for lookup-created parameters; host powf boundary shared; all output words exact.'}))
if __name__=='__main__':main()
