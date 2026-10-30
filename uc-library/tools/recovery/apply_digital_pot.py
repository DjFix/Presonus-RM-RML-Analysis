"""Apply three shared DigitalPot products with immutable candidate hash guards."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import shutil

repo=Path('/home/rs/projects/opencs/ai-line-analysis')
lib=repo/'uc-library'
candidate=lib/'candidates/panel-digital-pot'
base=candidate/'validation/seals/verify-02'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
assert sha(base/'validation.json')=='a0dcf8ceb4aba9b4b1182e94bd31c9e362facd674f190eefa4e8de8f87782e61'
assert sha(base/'active-apply.json')=='9833d180af38f298fb7db0cfe4d021bfa0d81698325398100f104cf0b77bc7a5'
mapping=json.loads((base/'active-apply.json').read_text())
for row in mapping['products']:
    assert sha(candidate/row['source'])==row['sha256']
    assert not (lib/row['destination']).exists(),row['destination']
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
evidence=repo/'evidence/recovery/2026-10-27/digital-pot-application'/stamp
evidence.mkdir(parents=True)
paths=[]
for row in mapping['products']:
    target=lib/row['destination'];target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(candidate/row['source'],target);paths.append(row['destination'])
shutil.copyfile(base/'active-apply.json',evidence/'active-apply.json')
(lib/'validation/format-digital-pot-paths.json').write_text(json.dumps(paths,indent=2)+'\n')
extra=['CMakeLists.txt','cmake/ProductionSourceGroups.cmake','tools/audit_role_build.py']
extra += ['candidates/panel-digital-pot/validation/'+role+'-vectors.txt' for role in ('client','server')]
(lib/'validation/integration-digital-pot-additions.json').write_text(json.dumps(paths+extra,indent=2)+'\n')
print(json.dumps(dict(applied=len(paths),evidence=str(evidence.relative_to(repo)))))
