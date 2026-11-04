import argparse,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--driver',required=True);p.add_argument('--fixtures',required=True);a=p.parse_args();fixture=json.loads(Path(a.fixtures).read_text())
observations=[]
for index,c in enumerate(fixture['cases']):
 r=subprocess.run([a.driver]+c['argv'],capture_output=True,text=True,check=True,timeout=10)
 actual=json.loads(r.stdout)
 observations.append(dict(index=index,argv=c['argv'],application=actual,actual_provider_observations=r.stderr))
 expected=c['native']['observed']
 if c['packet']==1 and c['setup'].get('alias',1)==0:
  # Preserve the raw original null-this provider call. Real pinned CCL's member
  # requires an object, so production skips it; compare application dispatch.
  calls=[b for b in c['native']['boundaries'] if b['address']==0x120e24]
  assert len(calls)==1 and calls[0]['arguments'][0]==0
  assert expected[0][0]=='alias'
  expected=expected[1:]
  provider=dict(line.split('=',1) for line in r.stderr.splitlines() if '=' in line)
  assert provider['actual_Control_final_parameter']==c['native']['final_control_parameter']
  assert provider['actual_CCL_alias_signals']=='0'
  observations[-1]['intentional_provider_adaptation']='Raw original null-this AliasParam::setOriginal request retained; source guard avoids invoking actual CCL with no object.'
 assert actual==expected,dict(index=index,args=c['argv'],actual=actual,expected=expected)
print('replayed',len(fixture['cases']),'bounded original ARM application observations with real CCL/Control providers; no hardware/ARM ABI claim')

out=Path('temp/recovery-work/stabilized01_mapping-null-alias01-local/host-observations.json');out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(observations,indent=2)+'\n')
