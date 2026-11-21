import argparse,hashlib,json,subprocess,sys,copy
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--exe',required=True);p.add_argument('--object',required=True);p.add_argument('--integration',required=True);p.add_argument('--out',required=True);p.add_argument('--source-transition');p.add_argument('--source-transition-sha256');a=p.parse_args()
d=Path(__file__).parent
native=json.loads(subprocess.check_output([sys.executable,str(d/'native.py')]))
assert native==json.loads((d/'fixtures.json').read_text())
symbols=subprocess.check_output(['nm','--defined-only',a.object],text=True);assert '_ZN8Presonus7Surface14CascadeHandlerC1ERNS0_20SurfaceRootComponentE' in symbols
replay=subprocess.check_output([a.exe],text=True)
proof={'native':native,'replay_output':replay,'object_sha256':hashlib.sha256(Path(a.object).read_bytes()).hexdigest(),'executable_sha256':hashlib.sha256(Path(a.exe).read_bytes()).hexdigest(),'integration':a.integration,'symbols':symbols}
template=json.loads(Path('uc-library/candidates/rolling10_reserve25_names_01/worker-proof.json').read_text())
historical_proof=Path('uc-library/candidates/rolling10_reserve25_names_01/worker-proof.json')
entry=copy.deepcopy(template['proposed_readiness']['pending'][0])
transition_receipt=None
if a.source_transition or a.source_transition_sha256:
 assert a.source_transition and a.source_transition_sha256
 transition_path=Path(a.source_transition)
 assert hashlib.sha256(transition_path.read_bytes()).hexdigest()==a.source_transition_sha256
 transition=json.loads(transition_path.read_text())
 assert transition['version']==1 and transition['kind']=='explicit-current-source-port-compatibility-transition'
 binding=transition['tasks']['rolling10_reserve25_names_01']
 assert binding['historical_proof']==str(historical_proof)
 assert hashlib.sha256(historical_proof.read_bytes()).hexdigest()==binding['historical_proof_sha256']
 assert hashlib.sha256(Path(binding['historical_checker']).read_bytes()).hexdigest()==binding['historical_checker_sha256']
 changes=transition['source_transitions']
 allowed={'include/presonus/surface_panel/ControlHelpers.hpp','include/presonus/surface/sl_mixer_encoder.hpp'}
 assert len(changes)==len({change['path'] for change in changes})
 assert {'include/presonus/surface_panel/ControlHelpers.hpp'} <= {change['path'] for change in changes} <= allowed
 for change in changes:
  assert entry['sources'][change['path']]==change['previous_sha256']
  if change.get('previous_frozen_read_path'):
   assert hashlib.sha256(Path(change['previous_frozen_read_path']).read_bytes()).hexdigest()==change['previous_sha256']
  if change.get('current_frozen_read_path'):
   assert hashlib.sha256(Path(change['current_frozen_read_path']).read_bytes()).hexdigest()==change['current_sha256']
  assert hashlib.sha256((Path('uc-library')/change['path']).read_bytes()).hexdigest()==change['current_sha256']
  entry['sources'][change['path']]=change['current_sha256']
 transition_receipt={'path':str(transition_path),'sha256':a.source_transition_sha256,'binding':binding,'changes':transition['source_transitions'],'scope':transition['scope']}
for path,digest in entry['sources'].items():assert hashlib.sha256((Path('uc-library')/path).read_bytes()).hexdigest()==digest
current_readiness=copy.deepcopy(template['proposed_readiness']);current_readiness['pending']=[entry]
proof['source_transition']=transition_receipt
proof['historical_template']={'path':str(historical_proof),'sha256':hashlib.sha256(historical_proof.read_bytes()).hexdigest()}
proof['current_producer_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
for path,digest in entry['repository_sources'].items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest
proof.update(supplements=template.get('supplements',[]),provider_provenance=template.get('provider_provenance'),proposed_readiness=current_readiness,canonical_binding_pending=True,integration_sha256=hashlib.sha256(Path(a.integration).read_bytes()).hexdigest())
Path(a.out).write_text(json.dumps(proof,indent=2))
