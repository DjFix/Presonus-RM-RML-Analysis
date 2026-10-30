"""Apply frozen SimulateComm products; active validation/admission stays separate."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

repo = Path('/home/rs/projects/opencs/ai-line-analysis')
library = repo / 'uc-library'
candidate = library / 'candidates/panel-simulate-comm'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
control = candidate / 'CONTROLLED-APPLY.json'
assert sha(control) == '7d0cd42b1c6cc91947a19339831234e09609b06dbe667abb6cad4ae0e54e28a5'
plan = json.loads(control.read_text())
for name, digest in plan['frozen_proofs'].items():
    assert sha(candidate / name) == digest, name
for name, digest in plan['base_product_bindings'].items():
    assert sha(library / name) == digest, name
assert sha(candidate / 'reseal_active.py') == plan['active_reseal_sha256']
copies = []
for source, record in plan['copies'].items():
    assert record['active_sha256'] is None
    copies.append((candidate / source, record['target'], record['sha256']))
assert len(copies) == len({target for _, target, _ in copies}) == 4
fixtures = [(candidate / source, target, plan['fixture_sha256'])
            for source, target in plan['fixture_copies'].items()]
assert len(fixtures) == 1
for source, target, digest in copies + fixtures:
    assert sha(source) == digest, str(source)
    assert not (library / target).exists(), target
stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
evidence = repo / 'evidence/recovery/2026-10-27/simulate-comm-application' / stamp
evidence.mkdir(parents=True, exist_ok=False)
for source, target, _ in copies + fixtures:
    destination = library / target
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
shutil.copyfile(control, evidence / 'CONTROLLED-APPLY.json')
(evidence / 'application.json').write_text(json.dumps(dict(
    products={target: sha(library / target) for _, target, _ in copies + fixtures},
    planned_ready_delta=10, planned_pending_delta=10,
    scope='One shared transport, real CCL locks; declaration/ABI/concurrency limits retained.'), indent=2) + '\n')
paths = [target for _, target, _ in copies]
(library / 'validation/format-simulate-comm-paths.json').write_text(json.dumps(paths, indent=2) + '\n')
(library / 'validation/integration-simulate-comm-additions.json').write_text(json.dumps(
    paths + [target for _, target, _ in fixtures] + ['CMakeLists.txt', 'cmake/ProductionSourceGroups.cmake'], indent=2) + '\n')
print(json.dumps(dict(applied=4, fixtures=1, evidence=str(evidence.relative_to(repo)))))
