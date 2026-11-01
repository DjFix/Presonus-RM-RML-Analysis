"""Compare independently recorded original state and bounded call ordering."""
import argparse,collections,json,pathlib,subprocess
ap=argparse.ArgumentParser();ap.add_argument('--executable',required=True);ap.add_argument('--fixtures',required=True);ap.add_argument('--work-dir',required=True);args=ap.parse_args()
work=pathlib.Path(args.work_dir).resolve();work.mkdir(parents=True,exist_ok=True)
fixture=work/'preset.json';fixture.write_text('{}\n')
rows=json.loads(pathlib.Path(args.fixtures).read_text())['cases'];counts=collections.Counter();excluded=[]
semantic={'slot','empty','filename','folder','lookup-cache','preset-info','update','toString','fromString','reset','stored','recalled','recall'}
for index,row in enumerate(rows):
 c=row['input'];m=c['method']
 if m==10 and not c['reserve_ok'] and len(c['delegates'])>=c['capacity']:
  excluded.append(index);continue
 filename=str(fixture if c['load'] else work/'absent.preset')
 argv=[args.executable,str(m),str(c['present']),c['name'],c['marker'],str(c['slot']),str(c['empty']),str(c['load']),str(c['recall_result']),str(c['slot_parameter_present']),','.join(map(str,c['delegates'])),str(c['tag']),str(c['target']),str(c['msg']),c['info_name'],c['info_category'],filename]
 process=subprocess.run(argv,text=True,capture_output=True,check=True)
 actual=json.loads(process.stdout)
 if actual['observed']!=row['observed']:
  raise AssertionError((index,c,actual['observed'],row['observed']))
 expected=[t for t in row['native_trace'] if t[0] in semantic]
 if actual['trace']!=expected:raise AssertionError(('trace',index,c,actual['trace'],expected))
 counts[m]+=1
print(json.dumps(dict(result='pass',compared_cases=sum(counts.values()),per_symbol=dict(counts),native_only_allocation_failure_cases=excluded,domain='Explicit synthetic app callbacks; actual CCL containers, lookup, archive file load; callback mutation, allocation failure in actual provider, original layout/returns/ARM ABI excluded.')))
