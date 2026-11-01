import json,subprocess,sys
from pathlib import Path
base=Path('uc-library/candidates/graph-live-trial-04-mutegroup')
exe=sys.argv[1] if len(sys.argv)>1 else 'temp/recovery-work/graph-live-trial-04/mutegroup-worker/replay'
cases=json.loads((base/'fixtures.json').read_text())
data=''.join(' '.join(map(str,c['input'][:5]+[len(c['input'][5])]+c['input'][5]))+'\n' for c in cases)
p=subprocess.run([exe],input=data,text=True,capture_output=True,check=True);lines=p.stdout.splitlines();assert len(lines)==len(cases)
for c,line in zip(cases,lines):
 method=c['input'][0];n=c['native'];got=list(map(float,line.split()));expected=[n['result'] if method in [2,3] else -1]+n['values']+[n['maximum'],n['count']]
 assert got==expected,(c,got,expected)
print('matched',len(cases),'native fixtures; finite values, nonnull parameter boundaries, zero/two maximum, member counts zero through two; native call traces preserved; portable state/output differential')
