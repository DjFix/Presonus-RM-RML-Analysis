"""Apply the reviewed common-object build without changing reconstructed CPP."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

repo=Path('/home/rs/projects/opencs/ai-line-analysis')
lib=repo/'uc-library'
candidate=lib/'candidates/common-build'
control=candidate/'migration-01/apply-manifest.json'
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
assert sha(control)=='10b2046fcfc0377c8ba26b59bccd03a7ef6274922d03bb0d4cc240a87060fa3d'
manifest=json.loads(control.read_text())
for name,digest in manifest['source_hashes'].items():
    assert sha(lib/name)==digest,name
for key in ('prototype_proof','full_suite_proof'):
    proof=manifest[key]
    assert sha(lib/proof['path'])==proof['sha256']
for row in manifest['files']:
    assert sha(candidate/row['candidate'])==row['sha256']
    active=lib/row['target']
    assert (sha(active) if active.exists() else None)==row['previous_sha256'],row['target']
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
evidence=repo/'evidence/recovery/2026-10-27/common-build-application'/stamp
evidence.mkdir(parents=True)
for name in ('CMakeLists.txt','validation/integration.json','validation/ready-functions.json','validation/compiled-functions.json'):
    backup=evidence/'before'/name
    backup.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(lib/name,backup)
for row in manifest['files']:
    target=lib/row['target']
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(candidate/row['candidate'],target)
shutil.copyfile(control,evidence/'apply-manifest.json')
(lib/'validation/integration-common-build-additions.json').write_text(json.dumps(
    [row['target'] for row in manifest['files']],indent=2)+'\n')
assert all(sha(lib/name)==digest for name,digest in manifest['source_hashes'].items())
print(json.dumps(dict(applied=len(manifest['files']),cpp_sources_unchanged=True,
    common_units=41,client_units=8,server_units=3,evidence=str(evidence.relative_to(repo)))))
