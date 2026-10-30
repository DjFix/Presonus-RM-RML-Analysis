"""Coordinator-controlled, hash-guarded application of reviewed AVB files."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

repo=Path('/home/rs/projects/opencs/ai-line-analysis')
lib=repo/('uc-library' if (repo/'uc-library').is_dir() else 'uc-library')
candidate=lib/'validation/avb-receive-candidate'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((candidate/'apply-manifest.json').read_text())
assert sha(lib/manifest['candidate_proof'])==manifest['candidate_proof_sha256']
assert sha(lib/'include/presonus/avb/protocol.hpp')==manifest['base_header_sha256']
tool_root=candidate/'linux-reseal'
tools=json.loads((tool_root/'apply-manifest.json').read_text())
assert sha(lib/'tools/avb_protocol_verify.py')==tools['base_verifier_sha256']
for name,digest in manifest['sealed_dependencies'].items():
    assert sha(lib/name)==digest,name
allowed={'include/presonus/avb/protocol.hpp','include/presonus/avb/receive_services.hpp',
         'src/Presonus/AVB/AvbManagerReceive.cpp','tests/avb_receive_tests.cpp',
         'tools/avb_protocol_reseal.py','tools/avb_protocol_verify.py'}
replace={'include/presonus/avb/protocol.hpp','tools/avb_protocol_verify.py'}
plan=[]
for base,entries in ((candidate,manifest['files']),(tool_root,tools['files'])):
    for entry in entries:
        assert entry['target'] in allowed
        source=(base/entry['candidate']).resolve()
        target=(lib/entry['target']).resolve()
        assert source.is_relative_to(candidate.resolve()) and target.is_relative_to(lib.resolve())
        assert sha(source)==entry['sha256'],source
        if target.exists() and entry['target'] not in replace:
            assert sha(target)==entry['sha256'],'refusing to replace unrelated target'
        plan.append((entry,source,target))
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
out=repo/'evidence/recovery/2026-10-27/avb-receive-application'/stamp
out.mkdir(parents=True,exist_ok=False)
for name in replace:
    backup=out/'before'/name
    backup.parent.mkdir(parents=True,exist_ok=True)
    backup.write_bytes((lib/name).read_bytes())
admissions={}
for name in ('ready-functions.json','compiled-functions.json'):
    data=json.loads((lib/'validation'/name).read_text())
    admissions[name]=[row for row in data['functions'] if row['mangled'].startswith('_ZN8Presonus3AVB14AvbManagerBase')]
assert len(admissions['ready-functions.json'])==3 and len(admissions['compiled-functions.json'])==2
(out/'prior-admissions.json').write_text(json.dumps(admissions,indent=2)+'\n')
for entry,source,target in plan:
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(source.read_bytes())
    assert sha(target)==entry['sha256']
report=dict(applied=True,base_header_sha256=manifest['base_header_sha256'],
            candidate_proof_sha256=manifest['candidate_proof_sha256'],
            files={entry['target']:entry['sha256'] for entry,_,_ in plan},
            readiness_admitted=False,required_reseal_ready=3,required_reseal_pending=2,
            new_receive_status='compiled/declaration-pending after fresh active validation')
(out/'application.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(applied_files=len(plan),evidence=str(out.relative_to(repo)),readiness_admitted=False)))
