"""Apply the frozen shared FileCleanup candidate; do not admit readiness."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

repo = Path('/home/rs/projects/opencs/ai-line-analysis')
library = repo / 'uc-library'
candidate = library / 'candidates/application-runtime/file-cleanup'
sealed = candidate / 'validation/seals/file-cleanup-validation-01'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
control = sealed / 'controlled-apply.json'
assert sha(control) == 'f1ce6743261de8676b05785cc9135c00a8e0cd890ab40a8741a11609b6767261'
proof = sealed / 'lifecycle-ready-validation.json'
assert sha(proof) == '60c6935ee50612b88205ef29eaa89d1a644ef66594980f6a450d2a7b9234cc80'
assert sha(sealed / 'ordinary-pending-validation.json') == '6d445a8558470c6facbaa3ef647babd574d5ac94123de53055cdb29653795af9'
products = json.loads(control.read_text())['products']
assert len(products) == len({r['destination'] for r in products}) == 6
copies = []
for record in products:
    assert record['required_destination'] == 'absent'
    copies.append((candidate / record['source'], record['destination'], record['sha256']))
fixture = sealed / 'fixtures.json'
copies.append((fixture, 'validation/application-file-cleanup/fixtures.json',
               json.loads(proof.read_text())['retained_fixture']['sha256']))
for source, target, digest in copies:
    assert sha(source) == digest, str(source)
    assert not (library / target).exists(), target
stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
evidence = repo / 'evidence/recovery/2026-10-27/file-cleanup-application' / stamp
evidence.mkdir(parents=True, exist_ok=False)
for source, target, _ in copies:
    destination = library / target
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
shutil.copyfile(control, evidence / 'controlled-apply.json')
(evidence / 'application.json').write_text(json.dumps(dict(
    products={target: sha(library / target) for _, target, _ in copies},
    planned_ready_delta=6, planned_pending_delta=6,
    scope='Shared original namespace, real CCL filesystem/vectors; ordinary return declarations pending.'), indent=2) + '\n')
paths = [r['destination'] for r in products]
(library / 'validation/format-file-cleanup-paths.json').write_text(json.dumps(
    [p for p in paths if p.endswith(('.cpp', '.hpp', '.h'))], indent=2) + '\n')
(library / 'validation/integration-file-cleanup-additions.json').write_text(json.dumps(
    paths + ['validation/application-file-cleanup/fixtures.json', 'CMakeLists.txt',
             'cmake/ProductionSourceGroups.cmake'], indent=2) + '\n')
print(json.dumps(dict(applied=6, fixtures=1, evidence=str(evidence.relative_to(repo)))))
