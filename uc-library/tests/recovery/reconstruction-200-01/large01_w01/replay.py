import argparse,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--executable',required=True);p.add_argument('--fixtures',required=True);a=p.parse_args()
f=json.loads(Path(a.fixtures).read_text());cases=f['cases'];inp=''.join(' '.join(map(str,c['args']))+'\n' for c in cases)
r=subprocess.run([a.executable],input=inp,text=True,capture_output=True);assert r.returncode==0,r.stderr
lines=r.stdout.splitlines();assert len(lines)==len(cases),(len(lines),len(cases))
for i,(line,c) in enumerate(zip(lines,cases)):
 actual=list(map(int,line.split()));assert actual==c['expected'],(i,c['args'],actual,c['expected'])
print(f'{len(cases)} native/provider differential cases passed; alias outputs, signed boundaries, all listener masks, slave positions and actual provider child cleanup')
