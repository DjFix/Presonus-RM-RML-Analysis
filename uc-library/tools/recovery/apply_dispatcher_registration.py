"""Apply shared registration methods and their reviewed dispatcher header."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import shutil

repo=Path('/home/rs/projects/opencs/ai-line-analysis')
lib=repo/'uc-library'
candidate=lib/'candidates/uc-dispatcher-registration'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
control=candidate/'CONTROLLED-APPLY.json'
assert sha(control)=='b115d2b7b08ece951fed762e38d3fa3d220f6af29ee061d7a45a86b7cae500c1'
proof=candidate/'validation/validation.json'
assert sha(proof)=='312c4ac3fa343277b821c960c32632890bec8b9c8ee10129c2364c8491e5f67c'
mapping=json.loads(control.read_text())['copies']
for name,entry in mapping.items():
    assert sha(candidate/name)==entry['sha256'],name
    target=lib/entry['target']
    assert (sha(target) if target.exists() else None)==entry['active_sha256'],entry['target']
fixture=candidate/'validation/arm-vectors.bin'
digest=json.loads(proof.read_text())['vectors_sha256']
assert sha(fixture)==digest
active_fixture=lib/'validation/uc-dispatcher-registration/arm-vectors.bin'
if active_fixture.exists():assert sha(active_fixture)==digest
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
evidence=repo/'evidence/recovery/2026-10-27/dispatcher-registration-application'/stamp
evidence.mkdir(parents=True)
paths=[]
for name,entry in mapping.items():
    target=lib/entry['target']
    if target.exists():
        backup=evidence/'before'/entry['target'];backup.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(target,backup)
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(candidate/name,target);paths.append(entry['target'])
target=active_fixture
target.parent.mkdir(parents=True,exist_ok=True)
if target.exists():assert sha(target)==digest
else:shutil.copyfile(fixture,target)
shutil.copyfile(control,evidence/'CONTROLLED-APPLY.json')
(lib/'validation/format-dispatcher-registration-paths.json').write_text(json.dumps(paths,indent=2)+'\n')
extra=['CMakeLists.txt','cmake/ProductionSourceGroups.cmake','validation/uc-dispatcher-registration/arm-vectors.bin']
(lib/'validation/integration-dispatcher-registration-additions.json').write_text(json.dumps(paths+extra,indent=2)+'\n')
print(json.dumps(dict(applied=len(paths),evidence=str(evidence.relative_to(repo)))))
