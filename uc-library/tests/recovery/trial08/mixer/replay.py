"""Compare original ARM boundary observations directly with built source-port output."""
import argparse,json,pathlib,subprocess

def expected(x):
 i=x['packet'];c=x['input'];trace=x['trace'];events=[];result=-1
 if i==1:events=[['server',trace[0][3]]]
 if i==2:events=[['delete-request']] if trace else []
 if i==3:
  events=[['lookup',(t[1]-0x810000)//0x1000,t[2]] for t in trace]
 if i in (3,8,9):result=(x['r0']-0x810000)//0x1000 if x['r0'] else -1
 if i==4:
  for t in trace:
   if t[0]=='filter':events.append(['filter',t[2],t[3]])
   if t[0]=='visitor-state':
    assert t[1]=='00' and t[2]==0 and t[3:6]==[0,0,0] and t[6]==0x802000
    events.append(['load',0,c['attributes'],1])
 if i==5:
  for t in trace:
   if t[0]=='setValue':events.append(['set',1,1 if t[2]==0x3f800000 else 0,t[3]])
 if i==6:
  for t in trace:
   if t[0]=='presetType':events.append(['presetType'])
   if t[0]=='command':events.append(['command',t[4]])
 if i==7:
  for t in trace:
   assert t[0]=='select.setValue' and t[2:4]==[0,0]
   events.append(['set',(t[1]-0x840000)//0x100,0,0])
 if i==10:
  assert trace[0][0]=='provider.removeAll' and trace[1][0]=='provider.builder'
  for t in trace:
   if t[0]=='filter':events.append(['filter',t[2],t[3]])
   if t[0]=='visitor-state':
    assert t[1]=='00' and t[2]==0 and t[3:5]==[0,0]
    events.append(['save',0,1])
 return dict(result=result,flags=x['flags'],events=events)

def main():
 p=argparse.ArgumentParser();p.add_argument('--executable',required=True);p.add_argument('--fixtures',required=True);a=p.parse_args()
 fixtures=json.loads(pathlib.Path(a.fixtures).read_text())
 for n,x in enumerate(fixtures):
  c=x['input'];args=[x['packet'],c.get('count',0),c.get('match',-1),c.get('attributes',0),c.get('enabled',0),c.get('active',0),c.get('excluded',0),c.get('bits',0),c.get('type',0),c.get('flags',c.get('index',0))]
  run=subprocess.run([a.executable,*map(str,args)],text=True,capture_output=True,check=True)
  actual=json.loads(run.stdout.strip().splitlines()[-1]);wanted=expected(x)
  if actual!=wanted:raise AssertionError({'case':n,'input':x,'actual':actual,'expected':wanted})
 print(f'{len(fixtures)} original ARM / C++ boundary replay cases passed; Core provider operations use pinned CCL source; no ARM ABI/hardware claim')
if __name__=='__main__':main()
