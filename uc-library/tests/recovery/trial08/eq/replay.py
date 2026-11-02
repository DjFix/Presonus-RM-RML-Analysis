"""Compare explicit built executable directly to independent original fixtures."""
import argparse,json,pathlib,subprocess
p=argparse.ArgumentParser();p.add_argument('--executable',required=True);p.add_argument('--fixtures',required=True);a=p.parse_args()
cases=json.loads(pathlib.Path(a.fixtures).read_text())['cases'];inputs=[];expected=[]
for c in cases:
 t=c['target']
 if t in [2,5]:
  inputs.append([t,c['index'],c['count']]+[x for row in c['states'] for x in row]);expected.append([c['result'] if t==5 else -1]+c['dirty'])
 elif t==4:
  inputs.append([t,c['state'],c['present'],c['valid']]);expected.append([c['buffered'],c['final_present'],c['final_valid'],c['calls'].count('release'),c['calls'].count('initBands')])
 elif t in [8,9,10]:
  inputs.append([t,c['index'],c['count'],int(c['present'])]);expected.append([c['result_bits'],len(c['calls'])])
 elif t in [1,3]:
  inputs.append([t,0,0,c['value']]);expected.append(c['result'])
 elif t==6:
  inputs.append([t,0,c['value']]);expected.append(c['result'])
 elif t==7:
  inputs.append([t,0,0,c['text']]);expected.append([c['result']])
 else:raise AssertionError(t)
text=''.join(' '.join(map(str,line))+'\n' for line in inputs)
r=subprocess.run([a.executable],input=text,text=True,capture_output=True,check=True)
lines=r.stdout.splitlines();assert len(lines)==len(cases),(len(lines),len(cases),r.stderr)
for c,line,want in zip(cases,lines,expected):assert list(map(int,line.split()))==want,(c,line,want)
print(f'{len(cases)} native/C++ differential cases passed; targets {sorted(set(c["target"] for c in cases))}')
