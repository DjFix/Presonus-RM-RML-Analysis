import argparse,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--executable',required=True);p.add_argument('--fixtures',required=True);a=p.parse_args();cases=json.loads(Path(a.fixtures).read_text())['cases']
r=subprocess.run([a.executable],input=''.join(' '.join(map(str,c['input']))+'\n' for c in cases),capture_output=True,text=True);assert r.returncode==0,(r.returncode,r.stderr);lines=r.stdout.splitlines();assert len(lines)==len(cases),(len(lines),len(cases),r.stderr)
for i,(c,line) in enumerate(zip(cases,lines)):
 value,trace,provider=line.split('|');assert list(map(int,value.split()))==c['expected']['values'],(i,c['input'],line,c['expected']);assert [s.strip() for s in trace.split(';') if s.strip()]==c['expected']['trace'],(i,c['input'],line,c['expected']['trace']);_,sn,dn,controller,sr,dr,old,new=c['input'];assert list(map(int,provider.split()))==[int(controller and sn==2 and sr==j)+int(controller and dn==2 and dr==j) for j in [1,2]],(i,line)
print(f'PASS {len(cases)} native attribute/setter range cases; real CCL controller mixin and BMP resource loader/BitmapReference executed separately; test-only name resolver boundary')
