"""Apply three frozen ParamEditHandler products without admitting readiness."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

repo=Path('/home/rs/projects/opencs/ai-line-analysis')
lib=repo/'uc-library'
candidate=lib/'candidates/panel-param-edit-handler'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
control=candidate/'CONTROLLED-APPLY.json'
assert sha(control)=='f271a3685e5c53afd03a630a74d8ac66904b67858f311b2d730fb7d51fadda6b'
data=json.loads(control.read_text())
assert (data['new_ready_entries'],data['new_pending_entries'],data['new_ready_mangles'])==(6,8,3)
assert data['production_partition']=='common'
assert len(data['copies'])==3
for path,digest in data['frozen_proofs'].items():
    assert sha(candidate/path)==digest
for path,digest in data['base_product_bindings'].items():
    assert sha(lib/path)==digest
for path,row in data['copies'].items():
    assert sha(candidate/path)==row['sha256']
    assert row['active_sha256'] is None and not (lib/row['target']).exists()
assert len(data['fixture_copies'])==1
for path,target in data['fixture_copies'].items():
    assert sha(candidate/path)==data['fixture_sha256'] and not (lib/target).exists()
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
evidence=repo/'evidence/recovery/2026-10-27/param-edit-application'/stamp
evidence.mkdir(parents=True,exist_ok=False)
paths=[]
for path,row in data['copies'].items():
    destination=lib/row['target'];destination.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(candidate/path,destination);paths.append(row['target'])
for path,target in data['fixture_copies'].items():
    destination=lib/target;destination.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(candidate/path,destination);paths.append(target)
shutil.copyfile(control,evidence/'controlled-apply.json')
(evidence/'application.json').write_text(json.dumps(dict(products={p:sha(lib/p) for p in paths},new_ready=6,new_pending=8,admission_performed=False),indent=2)+'\n')
for filename,extra in [('format-panel-identity-paths.json',[p for p in paths if Path(p).suffix in ('.cpp','.hpp','.h')]),('integration-panel-identity-additions.json',paths)]:
    target=lib/'validation'/filename
    target.write_text(json.dumps(sorted(set(json.loads(target.read_text()))|set(extra)),indent=2)+'\n')
print(json.dumps(dict(applied=3,fixtures=1,evidence=str(evidence.relative_to(repo)))))
