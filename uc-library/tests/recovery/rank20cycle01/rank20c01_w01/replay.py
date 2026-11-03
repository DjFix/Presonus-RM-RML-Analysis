"""Portable replay against independently captured original observations."""
import argparse,json,pathlib,subprocess
p=argparse.ArgumentParser();p.add_argument('--executable',required=True);p.add_argument('--fixtures',required=True);args=p.parse_args()
fixtures=json.loads(pathlib.Path(args.fixtures).read_text());cases=[c for c in fixtures['cases'] if c['packet'] in (5,23)]
inputs=''.join(' '.join(map(str,[c['packet'],*c['inputs']]))+'\n' for c in cases)
r=subprocess.run([args.executable],input=inputs,text=True,capture_output=True,check=True)
lines=r.stdout.splitlines();assert len(lines)==len(cases)
for c,line in zip(cases,lines):
 out=list(map(int,line.split()));assert out[:3]==c['output'],(c['inputs'],out,c['output'])
 assert len(c['calls'])==out[3]==1
 call=c['calls'][0];i=c['inputs'];assert out[4]==(i[1] if c['packet']==5 else i[2])
 raw=bytes.fromhex(call['object_at_call'])
 expected=[raw[0x85],int.from_bytes(raw[0x17c:0x180],'little'),int.from_bytes(raw[0x190:0x194],'little')]
 assert out[5:]==expected,(out,expected)
print(len(cases),'portable executions match original poststate and ordered application call observations')
