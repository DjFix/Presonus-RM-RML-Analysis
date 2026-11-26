import argparse,hashlib,json,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--exe',required=True);p.add_argument('--object',required=True);p.add_argument('--integration',required=True);p.add_argument('--out',required=True);p.add_argument('--source-transition');p.add_argument('--source-transition-sha256');a=p.parse_args()
d=Path(__file__).parent
native=json.loads(subprocess.check_output([sys.executable,str(d/'native.py')]))
assert native==json.loads((d/'fixtures.json').read_text())
symbols=subprocess.check_output(['nm','--defined-only',a.object],text=True);assert '_ZN8Presonus7Surface19PageHeaderComponent19disconnectMappablesEv' in symbols
replay=subprocess.check_output([a.exe],text=True)
proof={'native':native,'replay_output':replay,'object_sha256':hashlib.sha256(Path(a.object).read_bytes()).hexdigest(),'executable_sha256':hashlib.sha256(Path(a.exe).read_bytes()).hexdigest(),'integration':a.integration,'symbols':symbols}
template_path = Path('uc-library/candidates/rolling10_next100_pageheader_disconnect/worker-proof.json')
template = json.loads(template_path.read_text())
entry = template['proposed_readiness']['pending'][0]
if bool(a.source_transition) != bool(a.source_transition_sha256):
    p.error('Supply both source transition arguments')
if a.source_transition:
    transition_path = Path(a.source_transition)
    assert hashlib.sha256(transition_path.read_bytes()).hexdigest() == a.source_transition_sha256
    transition = json.loads(transition_path.read_text())
    assert transition['historical_template'] == {
        'path': str(template_path),
        'sha256': hashlib.sha256(template_path.read_bytes()).hexdigest(),
    }
    approved = {'include/presonus/MappablePageComponent.hpp', 'src/Presonus/MappablePageComponent.cpp'}
    if 'w13_predecessor' in transition:
        prior = transition['w13_predecessor']
        for predecessor in (prior['manifest'], prior['checker']):
            assert hashlib.sha256(Path(predecessor['path']).read_bytes()).hexdigest() == predecessor['sha256']
        approved.update(('include/presonus/surface/PageHeaderComponent.hpp', 'src/Presonus/Surface/PageHeaderComponent.cpp'))
    changes = transition['source_transitions']
    assert len(changes) == len(approved) and {row['path'] for row in changes} == approved
    for row in changes:
        assert entry['sources'][row['path']] == row['previous_sha256']
        assert hashlib.sha256(Path(row['historical_source']).read_bytes()).hexdigest() == row['previous_sha256']
        assert hashlib.sha256(Path(row['current_frozen_read_path']).read_bytes()).hexdigest() == row['current_sha256']
        entry['sources'][row['path']] = row['current_sha256']
    proof['source_transition'] = {'path': str(transition_path), 'sha256': a.source_transition_sha256}
    proof['historical_template'] = transition['historical_template']
for path,digest in entry['sources'].items():assert hashlib.sha256((Path('uc-library')/path).read_bytes()).hexdigest()==digest
for path,digest in entry['repository_sources'].items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest
proof.update(producer_revision=template.get('producer_revision'),supplements=template.get('supplements',[]),provider_provenance=template.get('provider_provenance'),proposed_readiness=template['proposed_readiness'],canonical_binding_pending=True,integration_sha256=hashlib.sha256(Path(a.integration).read_bytes()).hexdigest())
Path(a.out).write_text(json.dumps(proof,indent=2))
