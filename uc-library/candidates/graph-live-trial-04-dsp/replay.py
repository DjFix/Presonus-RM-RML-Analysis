"""Replay hash-bound original observations against canonical or local C++ executable."""
import argparse,json,pathlib,subprocess,tempfile
p=argparse.ArgumentParser();p.add_argument('--exe',required=True);p.add_argument('--fixture',required=True);p.add_argument('--work',required=True);a=p.parse_args()
d=json.loads(pathlib.Path(a.fixture).read_text());work=pathlib.Path(a.work);work.mkdir(parents=True,exist_ok=True);inp=work/'input.tsv'
keys=['method','mode','index','converter','value','low','high','guard']
inp.write_text(''.join(' '.join(str(c[k]) for k in keys)+'\n' for c in d['cases']))
r=subprocess.run([a.exe,str(inp)],text=True,capture_output=True,check=True);rows=r.stdout.splitlines();assert len(rows)==len(d['cases'])
for i,(c,row) in enumerate(zip(d['cases'],rows)):
 values=list(map(int,row.split()));assert values[0]==c['result'],(i,c,values)
 expected=[]
 for name,regs in c['trace']:
  if name.startswith('0x10010'):
   slot=(int(name,16)-0x1001000)//16
   tag=regs[1] if slot<4 else 0
   if tag>=2**31:tag-=2**32
   val=0 if slot==1 else regs[2] if slot<4 else regs[1]
   expected.extend([slot,tag,val])
 assert values[1]==len(expected)//3 and values[2:]==expected,(i,c,values,expected)
(work/'replay-output.tsv').write_text(r.stdout)
print(f"PASS {len(rows)} original ARM/C++ cases: return bit patterns and ordered dispatch calls/arguments; native raw static-layout writes recorded, source-port lifecycle differs intentionally")
