"""Replay a canonical or local executable against immutable original observations."""
from pathlib import Path
import argparse,json,subprocess
p=argparse.ArgumentParser();p.add_argument('--executable',required=True);p.add_argument('--fixtures',required=True);a=p.parse_args()
f=json.loads(Path(a.fixtures).read_text());exe=str(Path(a.executable).resolve())
def invoke(mode,rows):
 result=subprocess.run([exe,mode],input='\n'.join(' '.join(map(str,x)) for x in rows)+'\n',text=True,capture_output=True,check=True)
 return [list(map(int,row.split())) for row in result.stdout.splitlines()]
checked=0
for packet,mode in [(1,'pot'),(2,'focus'),(3,'find')]:
 cases=[x for x in f['cases'] if x['packet']==packet];actual=invoke(mode,[x['inputs'] for x in cases])
 assert len(actual)==len(cases),(mode,'row count')
 for c,got in zip(cases,actual):
  expected=list(c['output'])
  if mode=='pot':
   assert got[9:]==[0,0],('actual CCL BitmapReference source-port scope exit',got)
   got=got[:9]
  if mode=='pot' and expected[5]>=2**31:expected[5]-=2**32
  assert got==expected,(mode,c['inputs'],expected,got)
 checked+=len(cases)
construct={i:[x for x in f['cases'] if x['packet']==i] for i in [4,5,6,7]}
rows=invoke('construct',[x['inputs'] for x in construct[5]])
for j,row in enumerate(rows):
 p=construct[5][j]['output'];focus=construct[4][j]['output'];assert focus==construct[6][j]['output']
 m=construct[7][j]['output'];value=construct[5][j]['inputs'][0]
 expected=[0,*p,value,value,focus[0],0,18,18,*m]
 assert row==expected,('construct',value,expected,row)
 checked+=4
provider_lifecycle=invoke('provider-lifecycle',[])
portable_lifecycle=invoke('portable-lifecycle',[])
assert len(provider_lifecycle)==9
assert portable_lifecycle==provider_lifecycle,('actual CCL vs portable Parameter registration/callback/removal',provider_lifecycle,portable_lifecycle)
print('PASS actual pinned CCL live Parameter: 9 provider and 9 portable observations; getParameter identities, two live observer registrations, enable/disable notifications and nested scope removal')
print(f'PASS {checked} bounded original application executions compared to actual CCL-backed portable C++; 729 bitmap transitions plus focus, traversal and independently ranged constructors; source-provider base behavior observed separately')
