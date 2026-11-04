import argparse,json,subprocess
from pathlib import Path

def replay(executable,fixture):
 d=json.loads(Path(fixture).read_text());lines=[];expected=[]
 for c in d['cases']:
  k=c['kind']
  if k=='rect':line='rect '+' '.join(map(str,c['values']));result=c['result']
  elif k=='command':line='command '+' '.join(map(str,[c['index'],c['count'],c['aux'],*c['values'],*c['color'],c['initial']]));result=f"{c['result']} {c['result_count']} {c['result_aux']}"
  elif k=='sequence':
   tokens=['sequence',c['count'],c['aux'],c['initial'],len(c['operations'])]
   for op in c['operations']:tokens.extend([op['index'],*op['values'],*op['color']])
   line=' '.join(map(str,tokens));result=f"{c['result']} {c['result_count']} {c['result_aux']}"
  elif k=='map':line='map '+' '.join(map(str,[c['index'],*c['color']]));result=c['name'] if c['index']==10 else str(c['result'])
  elif k=='diff':line='diff '+' '.join(map(str,c['a']+c['b']));result=str(c['result'])
  else:raise ValueError(k)
  lines.append(line);expected.append(result)
 p=subprocess.run([str(executable)],input='\n'.join(lines)+'\n',text=True,capture_output=True,check=True)
 actual=p.stdout.splitlines();assert len(actual)==len(expected),(len(actual),len(expected))
 for i,(a,b) in enumerate(zip(actual,expected)):
  assert a==b,(i,d['cases'][i]['kind'],a,b)
 print(f'PASS {len(actual)} exact native/provider fixture cases')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--executable',required=True);p.add_argument('--fixtures',required=True);a=p.parse_args();replay(a.executable,a.fixtures)
