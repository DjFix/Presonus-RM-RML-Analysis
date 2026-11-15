import argparse,hashlib,json,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--exe',required=True);p.add_argument('--object',required=True);p.add_argument('--integration',required=True);p.add_argument('--out',required=True);a=p.parse_args()
d=Path(__file__).parent
native=json.loads(subprocess.check_output([sys.executable,str(d/'native.py')]))
assert native==json.loads((d/'fixtures.json').read_text())
symbols=subprocess.check_output(['nm','--defined-only',a.object],text=True);assert '_ZN8Presonus7Surface14CascadeHandlerC1ERNS0_20SurfaceRootComponentE' in symbols
replay=subprocess.check_output([a.exe],text=True)
proof={'native':native,'replay_output':replay,'object_sha256':hashlib.sha256(Path(a.object).read_bytes()).hexdigest(),'executable_sha256':hashlib.sha256(Path(a.exe).read_bytes()).hexdigest(),'integration':a.integration,'symbols':symbols}
template=json.loads(Path('uc-library/candidates/rolling10_reserve25_names_01/worker-proof.json').read_text())
entry=template['proposed_readiness']['pending'][0]
for path,digest in entry['sources'].items():assert hashlib.sha256((Path('uc-library')/path).read_bytes()).hexdigest()==digest
for path,digest in entry['repository_sources'].items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest
proof.update(supplements=template.get('supplements',[]),provider_provenance=template.get('provider_provenance'),proposed_readiness=template['proposed_readiness'],canonical_binding_pending=True,integration_sha256=hashlib.sha256(Path(a.integration).read_bytes()).hexdigest())
Path(a.out).write_text(json.dumps(proof,indent=2))
