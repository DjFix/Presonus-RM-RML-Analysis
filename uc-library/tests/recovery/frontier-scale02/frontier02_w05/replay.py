"""Replay native FX+Send effects after independently observed actual Output provider.
Canonical CTest passes its own executable and immutable fixture explicitly.
"""
import argparse,json,pathlib,subprocess,time,shlex
p=argparse.ArgumentParser();p.add_argument('--executable',required=True);p.add_argument('--fixtures',required=True);a=p.parse_args()
j=json.loads(pathlib.Path(a.fixtures).read_text());cases=[c for c in j['cases'] if c['packet']==2]
global_case=next(c for c in j['cases'] if c['packet']==1)
assert [(c['target'],c['literal']) for c in global_case['calls']]==[(0x321c4,'temp'),(0x1289f4,'mixer.scene')]
assert global_case['calls'][0]['args'][:2]==[0x470000,0x430000]
assert global_case['calls'][1]['args'][0]==0x470000
lines=[]
for c in cases:
 for mode in [2,20,30]:lines.append(' '.join(map(str,[mode,*c['inputs']])))
r=subprocess.run([a.executable],input='\n'.join(lines)+'\n',text=True,capture_output=True,check=True)
rows=[[int(v) for v in line.split()] for line in r.stdout.splitlines()];assert len(rows)==len(lines)
for i,c in enumerate(cases):
 actual,send_provider,provider=rows[3*i:3*i+3];tag,msg,count,initial,dirty,mutate=c['inputs']
 assert [call['target'] for call in c['calls']]==[0x46b98,0x46978]
 # Output provider is independently invoked: use its actual residual state as
 # input to measured native Send/FX stores. Neither app method is modeled here.
 want=provider[:];want_send=provider[:]
 native_initial=[initial,initial,initial,initial,dirty]
 for n,out in enumerate([c['state'],*c['children']]):
  # Only selected/expanded original-range stores are admitted.
  addr=0x400000 if n==0 else 0x450000+0x1000*(n-1)
  for location,size,value,pc in c['writes']:
   field={0x178:0,0x17c:1,0x18c:2,0x194:3,0x85:4}.get(location-addr)
   if field is not None:
    want[5*n+field]=value
    if 0x46b98<=pc<0x46c74:want_send[5*n+field]=value
 assert actual==want,(i,c['inputs'],actual,want)
 assert send_provider==want_send,(i,c['inputs'],send_provider,want_send)
 assert actual[5*(count+1):5*(count+1)+3]==[1,tag,msg]
root=pathlib.Path(__file__).resolve().parents[5]
out=root/'temp/recovery-work/frontier-scale02/frontier02_w05'/('provider-path-'+str(time.time_ns()))
r=subprocess.run([a.executable,'path',str(out)],text=True,capture_output=True,check=True)
paths=[shlex.split(s) for s in r.stdout.splitlines()];assert len(paths)==3
for device,got in paths:
 want=str(out/'presonus'/device/'temp'/'mixer.scene')
 assert got==want,(got,want)
print(json.dumps({'native_app_cases':len(j['cases']),'portable_FX_cases':len(cases),'independent_actual_Send_cases':len(cases),'provider_paths':paths,'domain':'Native FX+Send writes and call order; actual Output/Parameter provider baseline effects replayed independently. Actual Send also separately checked against native stores. Native Output/Channel behavior excluded. Global literal/call ordering and pinned provider actual mkdir/path effects. No Core native execution, original declarations/layout/ARM ABI/hardware claims.'}))
