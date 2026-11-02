#!/usr/bin/env python3
"""CTest adapter: compare actual built C++ output with retained ARM fixtures."""
import argparse,json,subprocess,sys
from pathlib import Path

def serialize(c):
 keys=['method','index','flag','param','name','tag','msg','enabled','recalling','busy','stored','old_remote','all_group','observer','connected','remote_component','load_ok','message_match']
 out=[str(c[k]&0xffffffff) if k=='index' else str(c[k]) for k in keys]+[str(v) for v in c['values']]
 for k in ['loose','delayed','local_tags','remote_tags','timer_present','executing','elapsed']:out += [str(len(c[k]))]+[str(v) for v in c[k]]
 return ' '.join(out)
def main():
 p=argparse.ArgumentParser();p.add_argument('--executable',required=True);p.add_argument('--fixtures',required=True);a=p.parse_args();d=json.loads(Path(a.fixtures).read_text())
 proc=subprocess.run([a.executable],input='\n'.join(serialize(x['input']) for x in d['cases'])+'\n',text=True,capture_output=True,timeout=120)
 if proc.returncode:print(proc.stdout,proc.stderr);raise SystemExit(proc.returncode)
 observed=[];debug=[]
 for line in proc.stdout.splitlines():
  if line.startswith('OBS '):
   value=json.loads(line[4:]);value['debug']=debug;debug=[];observed.append(value)
  elif line.startswith('recallMutes '):debug.append(line)
  elif line:raise AssertionError(f'unexpected output {line}')
 assert len(observed)==len(d['cases']),(len(observed),len(d['cases']))
 failures=[]
 for c,o in zip(d['cases'],observed):
  if c['expected']!=o:failures.append({'id':c['id'],'input':c['input'],'expected':c['expected'],'actual':o})
 if failures:
  print(json.dumps(failures[:8],indent=2));print('mismatches',len(failures));raise SystemExit(1)
 print(f"matched {len(observed)} original ARM observations across all ten targets: result, memory state, mutation and required app-call traces; bounded dependency stubs")
if __name__=='__main__':main()
