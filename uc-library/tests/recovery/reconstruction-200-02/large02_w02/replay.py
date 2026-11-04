"""Compare portable observations to independent app instructions/data and Core provider."""
import argparse,json,pathlib,subprocess
PARAM=0x706000
SELF=0x700000
SUPPORTED={1,4,5,7,12,13,14,15,17,18,19,20}
def signed(n):return n if n<0x80000000 else n-0x100000000
def expected(case,id,fixture):
 observed=case['observed'];calls=observed['calls'];writes={w[0]:w[2] for w in observed['writes']}
 cleanup=fixture['source_provider_observation']['core_parameter_cleanup_count']
 if id==4:
  assert [c['target'] for c in calls]==[0x8c630,0x8c630,0x11a53c]
  assert [c['args'][0] for c in calls]==[SELF+0xb8,SELF+0x98,SELF]
  return [f'panel_cleanup {cleanup}']
 if id==14:
  assert calls[0]['target']==0x119e8c and calls[0]['args'][1]==0x3198c0
  assert [c['args'][1] for c in calls if c['target']==0x8c59c]==[0x3f800000]*2
  assert writes[0x88]==0 and writes[0x8c]==0x702000 and writes[0x90]==0x704000
  words=[signed(writes[o]) for o in [0xdc,0xe0,0xe4,0xe8,0xec]]
  return [f'panel_ctor panel {writes[0x28]} 1000 1000 0 0 '+ ' '.join(map(str,words))]
 if id in [15,19]:
  additions=[c for c in calls if c['target']==0x11ec54]
  assert [(c['args'][1],c['args'][2]) for c in additions]==[(0x32690c,134),(0x329504,2)]
  out=[f'front_ctor 136 {writes[0x28]} {writes[0x108]} {writes[0x164]} {signed(writes[0x1b8])} {writes[0x169]} {writes[0x168]}']
  index=0
  for table in fixture['parameter_tables']:
   for record in table['records']:
    bits=record['value_bits']
    out.append(f"param {index} {record['tag']} {record['type']} {bits[0]} {bits[1]} {bits[3]} {record['name_hex']}")
    index+=1
  return out
 if id in [17,18,20]:
  wanted=[0x8c630,0x1228b0,0x6a054,0x6a054,0x5292c,0x8c630,0x8c630,0x11a53c]+([0xac10] if id==20 else [])
  assert [c['target'] for c in calls]==wanted
  freed=int(observed['allocator_model_object_freed'])
  assert freed==(id==20)
  return [f'front_cleanup {cleanup} {freed}']
 out=[]
 for call in calls:
  target=call['target'];a=call['args']
  if target==0x11dc28:out.append(f'changed {(a[0]-PARAM)//256}')
  if target==0x810058:out.append(f'set {(a[0]-PARAM)//256} {a[1]} {a[2]}')
 if id in [1,7]:out.append('dirty '+str(writes[0x168]))
 if id in [12,13]:out.append('return '+str(observed['r0']))
 return out
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--executable',required=True);ap.add_argument('--fixtures',required=True);a=ap.parse_args()
 fixture=json.loads(pathlib.Path(a.fixtures).read_text());count=0
 for case in fixture['cases']:
  id=int(case['packet'].split('_')[-1])
  if id not in SUPPORTED:continue
  s=case['scenario'];argv=[a.executable,str(id),str(s.get('arg1',1)),str(s.get('value',1.0)),str(s.get('param_value',0.0)),str(s.get('count',0)),str(s.get('tag',200)),str(s.get('executing',0)),str(s.get('mode',0)),str(1 if s.get('storing_null') else 2 if s.get('missing8') else 3 if s.get('missing1') else 0),str(s.get('active_index',-1)),str(s.get('active_meter',0))]
  result=subprocess.run(argv,text=True,capture_output=True,check=True)
  actual=[line for line in result.stdout.splitlines() if line.startswith(('set ','return ','dirty ','changed ','panel_ctor ','panel_cleanup ','front_ctor ','front_cleanup ','param '))]
  wanted=expected(case,id,fixture)
  if actual!=wanted:raise AssertionError((id,s,actual,wanted,result.stderr))
  count+=1
 print(f'{count} optimized C++ cases match bounded original app observations and pinned Core provider; constructor metadata checks cover136 records per C1/C2 case')
if __name__=='__main__':main()
