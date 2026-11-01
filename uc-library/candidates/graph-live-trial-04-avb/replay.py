import argparse,json,re,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--executable',required=True);p.add_argument('--fixtures',required=True);a=p.parse_args()
d=json.loads(Path(a.fixtures).read_text());cases=d['cases'];raw=''.join(' '.join(map(str,c['input']))+'\n' for c in cases)
r=subprocess.run([a.executable],input=raw,text=True,capture_output=True);assert r.returncode==0,(r.returncode,r.stderr)
observed=[];current=None
for line in r.stdout.splitlines():
 if line.startswith('CASE '):
  current={'trace':[]};observed.append(current)
 elif line.startswith('AvbComponent::'):
  m=re.search(r'index = (\d+) clock to listener \? (\d+)',line);assert m,line;current['trace'].append(['debug',int(m[1]),int(m[2])])
 else:
  parts=line.split();assert parts,line
  event=[parts[0]]+[int(x) for x in parts[1:]]
  if parts[0]=='state':current['state']=event[1:]
  else:current['trace'].append(event)
assert len(observed)==len(cases)
for i,(case,obs) in enumerate(zip(cases,observed)):
 expected={k:case['expected'][k] for k in ['trace','state']}
 if expected!=obs:
  print(json.dumps({'case':i,'input':case['input'],'expected':expected,'observed':obs},indent=2));sys.exit(1)
print(json.dumps({'passed':True,'cases':len(cases),'domain':'five native targets; enum dispatch, old/null slots, bools, signed modes, link modes and 64-bit stream bit patterns; ordered manager/debug/route/packet trace and final state; non-null provider returns'}))
