"""Apply the reviewed UC candidate with exact old/new hash guards and backups."""
import datetime
import hashlib
import json
from pathlib import Path
import shutil

repo = Path('/home/rs/projects/opencs/ai-line-analysis')
lib = repo / 'uc-library'
candidate = lib / 'candidates/uc-ccl-bindings'
control = candidate / 'CONTROLLED-APPLY.json'
assert hashlib.sha256(control.read_bytes()).hexdigest() == '40e3eddeb0211697f3cb8d2fc702403be943daa38da7b01881cdb8a1f7981adc'
copies = json.loads(control.read_text())['copies']
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
for name, entry in copies.items():
    assert sha(candidate / name) == entry['candidate_sha256'], name
    target = lib / entry['target']
    assert (sha(target) if target.exists() else None) == entry['active_sha256'], name
stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
evidence = repo / 'evidence/recovery/2026-10-27/uc-ccl-application' / stamp
evidence.mkdir(parents=True)
for name in ['validation/ready-functions.json', 'validation/compiled-functions.json',
             'validation/integration.json', 'CMakeLists.txt']:
    target = evidence / 'before' / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(lib / name, target)
for name, entry in copies.items():
    target = lib / entry['target']
    if target.exists():
        backup = evidence / 'before' / entry['target']
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target, backup)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(candidate / name, target)
(evidence / 'controlled-apply.json').write_bytes(control.read_bytes())
paths = sorted(e['target'] for e in copies.values())
(lib / 'validation/format-uc-ccl-paths.json').write_text(json.dumps(paths, indent=2) + '\n')
(lib / 'validation/integration-uc-ccl-additions.json').write_text(json.dumps(
    paths + ['CMakeLists.txt'], indent=2) + '\n')
print(json.dumps({'applied': len(paths), 'evidence': str(evidence.relative_to(repo))}))
