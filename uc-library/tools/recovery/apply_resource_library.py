"""Apply frozen shared ResourceLibrary registration products only."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

repo = Path('/home/rs/projects/opencs/ai-line-analysis')
lib = repo / 'uc-library'
candidate = lib / 'candidates/application-runtime/resource-library'
seal = candidate / 'validation/seals/resource-library-validation-03'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(seal / 'controlled-apply.json') == '8ca66f716e287c5432bcb88c77914fa1f5a8bce27d7d1d843469620498db64f4'
assert sha(seal / 'lifecycle-ready-validation.json') == '0d368b7635f4089956681737bf6d24645ac5f584fb97893983a42f8e6a9a3c5a'
assert sha(seal / 'ordinary-pending-validation.json') == 'e50d831ca62b2b992061befffc5e602860e61738deaf59cf8e0cc7d62f5bdf97'
products = json.loads((seal / 'controlled-apply.json').read_text())['products']
assert len(products) == len({r['destination'] for r in products}) == 4
copies = []
for row in products:
    assert row['required_destination'] == 'absent'
    copies.append((candidate / row['source'], row['destination'], row['sha256']))
copies.append((seal / 'fixtures.json', 'validation/application-resource/fixtures.json',
               '9dad259e17274bdd7ea337f8d1d70c05fcaffc4d584fdc7edf01973d818ce14c'))
for source, target, digest in copies:
    assert sha(source) == digest, str(source)
    assert not (lib / target).exists(), target
stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
evidence = repo / 'evidence/recovery/2026-10-27/resource-library-application' / stamp
evidence.mkdir(parents=True, exist_ok=False)
for source, target, _ in copies:
    destination = lib / target
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
shutil.copyfile(seal / 'controlled-apply.json', evidence / 'controlled-apply.json')
(evidence / 'application.json').write_text(json.dumps(dict(
    products={target: sha(lib / target) for _, target, _ in copies},
    planned_ready_delta=8, planned_pending_delta=8,
    scope='Shared registration/lookup/ownership only; bundle stream methods remain unreconstructed.'), indent=2) + '\n')
paths = [r['destination'] for r in products]
(lib / 'validation/format-resource-library-paths.json').write_text(json.dumps(
    [p for p in paths if p.endswith(('.cpp', '.hpp'))], indent=2) + '\n')
(lib / 'validation/integration-resource-library-additions.json').write_text(json.dumps(
    paths + ['validation/application-resource/fixtures.json', 'CMakeLists.txt', 'cmake/ProductionSourceGroups.cmake'], indent=2) + '\n')
print(json.dumps(dict(applied=4, fixtures=1, evidence=str(evidence.relative_to(repo)))))
