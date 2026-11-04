import argparse,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--driver',required=True);p.add_argument('--fixtures',required=True);a=p.parse_args()
data=json.loads(Path(a.fixtures).read_text())
for i,c in enumerate(data['cases']):
 p=subprocess.run([a.driver,str(c['n']),str(c['arg']),str(c['enabled'])],capture_output=True,text=True)
 assert p.returncode==0,(i,c,p.stdout,p.stderr)
 actual=json.loads(p.stdout.rsplit('RESULT ',1)[1])
 assert actual==c['expected'],(i,c['n'],c['arg'],c['enabled'],[(k,actual.get(k),v) for k,v in c['expected'].items() if actual.get(k)!=v])
print(len(data['cases']),'optimized portable cases agree with bounded native observations')
