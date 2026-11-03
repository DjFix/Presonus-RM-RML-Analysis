from pathlib import Path
import json,subprocess,sys

def execute(exe,lines):
 p=subprocess.run([exe],input='\n'.join(lines)+'\n',capture_output=True,text=True,check=True)
 return [[int(v) for v in line.split()] for line in p.stdout.splitlines()]

def replay(exe,fixture):
 native=fixture['native'];lines=[];expected=[]
 for c in native['controls']:
  i=c['input'];lines.append('C %d %d %d %s'%(i['enabled'],i['mutate'],len(i['rows']),' '.join(str(v) for row in i['rows'] for v in row)));expected.append(c['observed'])
 for c in native['messages']:
  i=c['input'];lines.append('M %d %s'%(i['accepted'],' '.join(map(str,i['identity']))));expected.append(c['observed'])
 actual=execute(exe,lines)
 for i,(a,e) in enumerate(zip(actual,expected)):
  assert a==e,(i,a,e)
 assert len(actual)==len(expected)
 provider=fixture['provider'];lines=[];expected=[]
 for target in [0,3,4,5,6,7,8]:
  for case in provider:
   lines.append('D %d %d'%(target,case['children_mask']));expected.append(case['actual_ccl_observation'])
 actual=execute(exe,lines);assert actual==expected,(actual,expected)
 print('160 ARM-bound control/message cases and 56 actual pinned CCL lifecycle cases matched; native D1 external-provider boundary remains separate')
if __name__=='__main__':
 if sys.argv[1]=='--observe-provider':
  rows=execute(sys.argv[2],['D 0 '+str(mask) for mask in range(8)])
  observed=[{'children_mask':mask,'actual_ccl_observation':row} for mask,row in enumerate(rows)]
  Path(sys.argv[3]).write_text(json.dumps(observed,indent=2)+'\n')
  print('8 independent direct pinned CCL provider lifecycle observations')
 else:replay(sys.argv[1],json.loads(Path(sys.argv[2]).read_text()))
