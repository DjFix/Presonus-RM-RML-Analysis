#!/usr/bin/env python3
"""Compare explicit C++ executable observations directly to independent ARM fixtures."""
import argparse,json,subprocess
from pathlib import Path

def encode(c):
 parts=[str(c[k]) for k in ['held','active','long','faders','page_exists']]+[c['page'],str(len(c['params']))]
 for k,v in c['params'].items():parts += [k,str(v)]
 parts += [str(len(c['selections'])),*map(str,c['selections']),str(len(c['channels'])),*map(str,c['channels']),str(len(c['ops']))]
 for op in c['ops']:parts+=list(map(str,op))
 return ' '.join(parts)+'\n'
def replay(executable,fixtures):
 data=json.loads(fixtures.read_text());count=0
 for row in data['cases']:
  r=subprocess.run([str(executable.resolve())],input=encode(row['input']),text=True,capture_output=True,check=True)
  actual=[line for line in r.stdout.splitlines() if line.startswith('@')]
  if actual!=row['expected']:
   print(row['input']['name']);print('EXPECTED',json.dumps(row['expected']));print('ACTUAL',json.dumps(actual));raise SystemExit(1)
  count+=1
 print(f'Passed {count} original ARM scenarios; state/parameter reads/writes and ordered app-boundary traces match.')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--executable',type=Path,required=True);p.add_argument('--fixtures',type=Path,required=True);a=p.parse_args();replay(a.executable,a.fixtures)
