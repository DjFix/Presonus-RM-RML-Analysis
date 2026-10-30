"""Adopt the three verified shared ControlGroup source products with guards."""
import datetime
import hashlib
import json
from pathlib import Path
import shutil

repo=Path('/home/rs/projects/opencs/ai-line-analysis')
lib=repo/'uc-library'
candidate=lib/'candidates/panel-control-group'
manifest=json.loads((candidate/'active-apply.json').read_text())
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
assert sha(candidate/'validation/validation.json')==manifest['source_validation_sha256']
for entry in manifest['products']:
    assert sha(candidate/entry['source'])==entry['sha256']
    assert not (lib/entry['destination']).exists(),entry['destination']
stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
evidence=repo/'evidence/recovery/2026-10-27/panel-control-group-application'/stamp
evidence.mkdir(parents=True)
paths=[]
for entry in manifest['products']:
    target=lib/entry['destination']
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(candidate/entry['source'],target)
    paths.append(entry['destination'])
(evidence/'apply-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
(lib/'validation/format-panel-control-group-paths.json').write_text(json.dumps(paths,indent=2)+'\n')
(lib/'validation/integration-panel-control-group-additions.json').write_text(json.dumps(
    paths+['CMakeLists.txt','candidates/panel-control-group/validation/arm-vectors.txt'],indent=2)+'\n')
print(json.dumps({'applied':len(paths),'evidence':str(evidence.relative_to(repo))}))
