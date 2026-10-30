"""Adopt one shared dispatcher implementation for both original applications."""
import datetime
import hashlib
import json
from pathlib import Path
import shutil

repo=Path('/home/rs/projects/opencs/ai-line-analysis')
lib=repo/'uc-library'
candidate=lib/'candidates/uc-event-dispatcher'
control=candidate/'CONTROLLED-APPLY.json'
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
assert sha(control)=='f34989ec9a6cf7f963cf64e96b6813515383de7ec7978846a6eb84f7b906f1d0'
assert sha(candidate/'validation/validation.json')=='64d90b20ba8b24e130e4163588cd899baea7281b7c3781903aeace6ab78d1bda'
mapping=json.loads(control.read_text())['copies']
proof=json.loads((candidate/'validation/validation.json').read_text())
fixture=candidate/'validation/arm-vectors.bin'
assert sha(fixture)==proof['vectors_sha256']
for name,entry in mapping.items():
    assert sha(candidate/name)==entry['sha256'],name
    assert not (lib/entry['target']).exists(),entry['target']
stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
evidence=repo/'evidence/recovery/2026-10-27/uc-dispatcher-application'/stamp
evidence.mkdir(parents=True)
paths=[]
for name,entry in mapping.items():
    target=lib/entry['target']
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(candidate/name,target)
    paths.append(entry['target'])
shutil.copyfile(control,evidence/'CONTROLLED-APPLY.json')
active_fixture=lib/'validation/uc-event-dispatcher/arm-vectors.bin'
active_fixture.parent.mkdir(parents=True,exist_ok=True)
if active_fixture.exists():
    assert sha(active_fixture)==sha(fixture)
else:
    shutil.copyfile(fixture,active_fixture)
(lib/'validation/format-uc-dispatcher-paths.json').write_text(json.dumps(paths,indent=2)+'\n')
(lib/'validation/integration-uc-dispatcher-additions.json').write_text(json.dumps(
    paths+['CMakeLists.txt','validation/uc-event-dispatcher/arm-vectors.bin'],indent=2)+'\n')
print(json.dumps({'applied':len(paths),'evidence':str(evidence.relative_to(repo))}))
