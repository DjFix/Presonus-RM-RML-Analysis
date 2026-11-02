#!/usr/bin/env python3
"""Compare original ARM observations directly against an explicit C++ executable."""
import argparse,json,subprocess
from pathlib import Path
KEYS='handlers present color tag mode mods value msg root same blink ex0 long0 was0 ex1 long1'.split()
def main():
 p=argparse.ArgumentParser();p.add_argument('--executable',required=True);p.add_argument('--fixtures',required=True);a=p.parse_args();d=json.loads(Path(a.fixtures).read_text())
 for i,c in enumerate(d['cases']):
  cfg=c['input'];argv=[str(Path(a.executable).resolve()),str(c['target'])]+[str(cfg.get(k,1 if k=='present' else 0)) for k in KEYS]
  r=subprocess.run(argv,text=True,capture_output=True,check=True);lines=r.stdout.splitlines();o=c['observation'];expected=o['trace']+[f'PARAM {k} {v}' for k,v in sorted(o['parameter_bits'].items(),key=lambda x:int(x[0]))]+[f"STATE {o['blink']} {o['timers'][0]} {o['timers'][1]} {o.get('return',0)}"]
  if lines!=expected:raise AssertionError(json.dumps({'case':i,'input':cfg,'target':c['target'],'expected':expected,'actual':lines},indent=2))
 print(f"PASS {len(d['cases'])} original ARM / C++ cases; all ten targets; ordered calls, parameters, blink and timer execution state")
if __name__=='__main__':main()
