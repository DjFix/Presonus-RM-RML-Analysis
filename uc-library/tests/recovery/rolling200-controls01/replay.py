"""Bounded app-native trace comparisons; pinned provider effects checked separately."""
import argparse,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--executable',required=True);p.add_argument('--fixtures',required=True);a=p.parse_args();d=json.loads(Path(a.fixtures).read_text());cases=d['cases'];text=''.join(' '.join(map(str,c['input']))+'\n' for c in cases)
r=subprocess.run([a.executable],input=text,text=True,capture_output=True);assert r.returncode==0,(r.returncode,r.stderr);lines=r.stdout.splitlines();assert len(lines)==len(cases),(len(lines),len(cases),r.stderr)
for i,(c,line) in enumerate(zip(cases,lines)):
 values,trace,provider=line.split('|');assert list(map(int,values.split()))==c['expected']['values'],(i,c['input'],line,c['expected']);assert [s.strip() for s in trace.split(';') if s.strip()]==c['expected']['trace'],(i,c['input'],line,c['expected']['trace'])
 target,old,new,arg,msg=c['input'];counts=list(map(int,provider.split()));
 if target:
  # Upstream add allows duplicates; remove removes one. Destroyed injection does
  # not itself remove registrations. Native oracle claims no provider behavior.
  if target==1:expected=[int(old==j)+int(new==j) for j in [1,2]]+[1,int(arg==3 and msg==3),1]
  else:expected=[int(new==j) for j in [1,2]]+[1,0,1]
  assert counts==expected,(i,c['input'],counts,expected)
print(f'PASS {len(cases)} exact original app-range/native boundary cases; real pinned observer duplicate/removal and Control changed/invalidate behavior checked independently')
