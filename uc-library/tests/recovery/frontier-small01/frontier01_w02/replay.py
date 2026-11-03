"""Replay native fixtures and compare actual CCL-backed lifecycle observations."""
import argparse,json,pathlib,subprocess,shlex
p=argparse.ArgumentParser();p.add_argument('--executable',required=True);p.add_argument('--fixtures',required=True);a=p.parse_args()
j=json.loads(pathlib.Path(a.fixtures).read_text());cases=j['cases']
lines=[];expected=[];rack_rows=[]
for c in cases:
 n=c['packet'];tag,msg,count,initial,dirty,mutate=c['inputs']
 if n in (3,4):
  assert len(c['calls'])==1 and c['calls'][0]['target']==0x11a53c
  assert c['calls'][0]['args'][0]==0x400000
  expected_vptr=[3567400,3567460] if n==3 else [3500248,3500300]
  assert c['vptr_words']==expected_vptr and c['calls'][0]['vptr_words_at_call']==expected_vptr
  continue
 lines.append(' '.join(map(str,[n,*c['inputs']])))
 if n==1:
  assert [x['target'] for x in c['calls']]==[0x35984,0x30fe0]
  expected.append([c['rack_state'],0,tag]);rack_rows.append((len(expected)-1,c))
 else:
  assert len(c['calls'])==1 and c['calls'][0]['target']==0x46978
  assert c['calls'][0]['tag_at_call']==tag&0xffffffff
  flat=c['state']+sum(c['children'],[])
  expected.append(flat+[1,tag,msg]+c['calls'][0]['state_at_call']+sum(c['calls'][0]['children_at_call'],[]))
# Provider expected observations are obtained by running actual Component, then
# compared to both app source ports. This is preferred-source behavior, not a
# native Core execution or native deallocation claim.
for _,c in rack_rows:lines.append(' '.join(map(str,[10,*c['inputs']])))
for count in [0,1,3]:
 for n in [30,3,4]:lines.append(f'{n} 0 0 {count} 0 0 0')
r=subprocess.run([a.executable],input='\n'.join(lines)+'\n',text=True,capture_output=True,check=True)
outputs=[shlex.split(line) for line in r.stdout.splitlines()]
assert len(outputs)==len(lines)
for index,(want,got) in enumerate(zip(expected,outputs)):
 assert want==[int(v) for v in got[:len(want)]],(index,lines[index],want,got)
naming=[]
for offset,(index,c) in enumerate(rack_rows):
 got=outputs[index];direct=outputs[len(expected)+offset];tag,_,count,initial,_,_=c['inputs']
 assert [int(v) for v in direct[:3]]==[initial,0,tag]
 assert got[3:]==direct[3:],('base naming mismatch',c['inputs'],got,direct)
 wanted=[]
 for i in range(count):
  number=i+1+(count if tag else 0)
  wanted.extend([str(number),f'Ch. {number}',f'Custom {i+1}' if i%2 else f'Ch. {number}'])
 assert got[3:]==wanted,('live provider naming effects',c['inputs'],got,wanted)
 naming.append({'inputs':c['inputs'],'actual_base':direct,'rack':got})
provider=[]
for offset,count in enumerate([0,1,3]):
 start=len(expected)+len(rack_rows)+offset*3;baseline,global_,geq=[[int(v) for v in row] for row in outputs[start:start+3]]
 assert baseline==global_==geq,(count,baseline,global_,geq)
 assert baseline==[count*2,count,1,1],('missing real cleanup',count,baseline)
 provider.append({'count':count,'actual_component':baseline,'global':global_,'geq':geq})
print(json.dumps({'native_app_cases':len(cases),'portable_app_replays':len(expected),'actual_provider_lifecycle':provider,'actual_base_naming_cases':len(naming),'actual_base_naming':naming,'domain':'valid live parameters; 0/1/3 valid nonnull child states; callback mutation; 0/1/3 live input-channel cascade bindings, default/custom names verified against actual base provider; explicit complete destructor with actual CCL owned children/arrays; no original full declarations/layout/ARM ABI/hardware'},sort_keys=True))
