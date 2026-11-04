"""Compare compiled source-port observations to hash-bound native fixtures."""
import argparse,json,subprocess
from pathlib import Path

def main():
 p=argparse.ArgumentParser();p.add_argument('--driver',required=True);p.add_argument('--fixtures',required=True);p.add_argument('--indices',default='');a=p.parse_args();j=json.loads(Path(a.fixtures).read_text());indices={int(x)for x in a.indices.split(',')if x};count=0
 for c in j['cases']:
  if indices and c['index'] not in indices:continue
  s=c['state'];args=[str(c['index'])]+[str(int(s.get(k,False)))for k in ['parameter','saved','component']]+[str(s.get(k,0))for k in ['value','saved_value','connectors','activators','message']]+[str(int(s.get('same',True))),str(s.get('arg',0))]+[str(int(s.get(k,False)))for k in ['peer','selected','global','found']]
  r=subprocess.run([a.driver]+args,capture_output=True,text=True,check=True)
  actual=json.loads(next(x for x in r.stdout.splitlines()if x.startswith('{')))
  native={k:v for k,v in c['native'].items()if k not in ['native_object_writes','native_deallocation'] and (k!='result_present' or c['index'] in [5,11,12])}
  if actual!=native:raise AssertionError({'case':c,'actual':actual,'stdout':r.stdout})
  sent=['sendEvent'] in c['native']['trace']
  concrete=[x for x in r.stdout.splitlines()if x.startswith('CONCRETE_MANAGER_RESULT ')]
  assert concrete==(['CONCRETE_MANAGER_RESULT 101']if sent else []),(c,r.stdout)
  routes=[x for x in r.stdout.splitlines()if x.startswith('ROUTES ')]
  assert routes==(['ROUTES 17 23']if sent else []),(c,r.stdout)
  payloads=[x[len('PAYLOAD '):]for x in r.stdout.splitlines()if x.startswith('PAYLOAD ')]
  if sent and c['index'] in [14,15,16]:
   expected={};key=None
   for t in c['native']['trace']:
    if t[0]=='attributes':expected['id']=t[1]
    if t[0]=='url':expected['url']=t[1]
    if t[0]=='attribute':key=t[1]
    if t[0]=='string':expected[key]=t[1]
    if t[0]=='integer':
     value=t[1]|(t[2]<<32);expected[key]=value-(1<<64)if value&(1<<63)else value
   assert len(payloads)==1 and json.loads(payloads[0])==expected,(c,payloads,expected)
  else:assert not payloads,(c,payloads)
  count+=1
 assert count
 regression=subprocess.run([a.driver]+['0']*15,capture_output=True,text=True,check=True)
 assert regression.stdout.strip()=='REGRESSION ok'
 guards=subprocess.run([a.driver,'17']+['0']*14,capture_output=True,text=True,check=True)
 assert guards.stdout.strip()=='ORIGIN_GUARDS ok'
 print('compiled/native matches',count)
if __name__=='__main__':main()
