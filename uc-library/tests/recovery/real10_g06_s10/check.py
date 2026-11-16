import importlib.util,json,shlex,sys
from pathlib import Path
spec=importlib.util.spec_from_file_location('shared',Path(__file__).parent.parent/'real10_g06_s04/check.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
module.main(Path(__file__).parent.name)
if '--compile' not in sys.argv:
 def option(k):return sys.argv[sys.argv.index(k)+1]
 data=json.loads((Path(__file__).parent/'fixtures.json').read_text())
 output,log=module.run([option('--exe'),'strings'])
 rows=[shlex.split(line)[1:] for line in output.splitlines() if line.startswith('SROW ')]
 assert len(rows)==len(data['string_cases'])
 for row,case in zip(rows,data['string_cases']):
  changed=int('changed' in case['connect_calls']);forwarded=case['forwarded']
  assert int(row[0])==changed and int(row[1])==len(forwarded) and row[2]==(forwarded[0] if forwarded else ''),(row,case)
 path=Path(option('--out'));proof=json.loads(path.read_text());domain=' Plus3 independent native string connect paths (empty, nonempty, >63bytes) and native callback helper observations; actual CCL changed observer effects and exact forwarded63-byte text compared. CCL numeric parsing result recorded as provider observation, no ARM provider-body claim.'
 for row in proof['functions']+proof['proposed_readiness']['pending']:
  row['domain']+=domain
  if 'case_count' in row:row['case_count']+=len(rows)
 proof['commands'].append(log);proof['supporting_helper']=data['helper_original_range'];proof['string_observations']=rows;proof['limitations']=[x.replace('String-source connect and helper callback forwarding excluded from this numeric-domain proof; ','') for x in proof['limitations']]
 path.write_text(json.dumps(proof,indent=2)+'\n');print('3 native/CCL string cases PASS')
