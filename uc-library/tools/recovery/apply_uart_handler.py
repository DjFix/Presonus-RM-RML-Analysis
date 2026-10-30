"""Apply the frozen shared UARTMessageHandler candidate without admission."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

repo = Path('/home/rs/projects/opencs/ai-line-analysis')
lib = repo / 'uc-library'
candidate = lib / 'candidates/panel-uart-message-handler'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
control = candidate / 'CONTROLLED-APPLY.json'
assert sha(control) == 'cd707ef16bfd0613958292d096c5520624349056451083cd94cb40941404730a'
plan = json.loads(control.read_text())
for name, digest in plan['frozen_proofs'].items():
    assert sha(candidate / name) == digest, name
for name, digest in plan['base_product_bindings'].items():
    assert sha(lib / name) == digest, name
assert sha(candidate / 'reseal_active.py') == plan['active_reseal_sha256']
copies = [(candidate / name, record['target'], record['sha256']) for name, record in plan['copies'].items()]
assert len(copies) == len({target for _, target, _ in copies}) == 4
assert all(record['active_sha256'] is None for record in plan['copies'].values())
fixtures = [(candidate / source, target, plan['fixture_sha256']) for source, target in plan['fixture_copies'].items()]
assert len(fixtures) == 1
for source, target, digest in copies + fixtures:
    assert sha(source) == digest, str(source)
    assert not (lib / target).exists(), target
stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
evidence = repo / 'evidence/recovery/2026-10-27/uart-handler-application' / stamp
evidence.mkdir(parents=True, exist_ok=False)
for source, target, _ in copies + fixtures:
    destination = lib / target
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
shutil.copyfile(control, evidence / 'CONTROLLED-APPLY.json')
(evidence / 'application.json').write_text(json.dumps(dict(
    products={target: sha(lib / target) for _, target, _ in copies + fixtures},
    planned_ready_delta=4, planned_pending_delta=36,
    scope='Shared dispatch with actual CCL TypedObject/CString128; ordinary declarations and static/ARM limits explicit.'), indent=2) + '\n')
paths = [target for _, target, _ in copies]
(lib / 'validation/format-uart-handler-paths.json').write_text(json.dumps(paths, indent=2) + '\n')
(lib / 'validation/integration-uart-handler-additions.json').write_text(json.dumps(
    paths + [target for _, target, _ in fixtures] + ['CMakeLists.txt', 'cmake/ProductionSourceGroups.cmake'], indent=2) + '\n')
print(json.dumps(dict(applied=4, fixtures=1, evidence=str(evidence.relative_to(repo)))))
