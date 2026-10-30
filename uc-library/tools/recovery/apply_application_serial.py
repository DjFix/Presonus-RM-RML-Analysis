"""Guarded serial-method addition to the disjoint SimulateComm batch."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

repo = Path('/home/rs/projects/opencs/ai-line-analysis')
library = repo / 'uc-library'
candidate = library / 'candidates/application-runtime/application-initialize'
sealed = candidate / 'validation/seals/application-serial-validation-02'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(sealed / 'controlled-apply.json') == '25b61a3adccec049cfc3f4a5ca7114a73c56c2a6a10cb672cfbc0d0644884a4f'
assert sha(sealed / 'pending-validation.json') == '104bf8e2de405619a0084120cf00e6e9035f44e64187298a3b91b58d41a9ed6b'
records = json.loads((sealed / 'controlled-apply.json').read_text())['products']
assert len(records) == len({r['destination'] for r in records}) == 4
copies = []
for row in records:
    assert row['required_destination'] == 'absent'
    copies.append((candidate / row['source'], row['destination'], row['sha256']))
copies.append((sealed / 'fixtures.json', 'validation/application-serial/fixtures.json',
               '2e4167668411e5744635643ce54e4f7de9385ed58f95af0d54b21a6d8d703935'))
for source, target, digest in copies:
    assert sha(source) == digest, str(source)
    assert not (library / target).exists(), target
stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
evidence = repo / 'evidence/recovery/2026-10-27/application-serial-application' / stamp
evidence.mkdir(parents=True, exist_ok=False)
for source, target, _ in copies:
    destination = library / target
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
shutil.copyfile(sealed / 'controlled-apply.json', evidence / 'controlled-apply.json')
(evidence / 'application.json').write_text(json.dumps(dict(
    products={target: sha(library / target) for _, target, _ in copies},
    planned_ready_delta=0, planned_pending_delta=1,
    scope='One client serial method only; partial application declaration and libc scanner limits explicit.'), indent=2) + '\n')
formatting = library / 'validation/format-simulate-comm-paths.json'
format_paths = json.loads(formatting.read_text())
format_paths += [r['destination'] for r in records if r['destination'].endswith(('.cpp', '.hpp'))]
assert len(format_paths) == len(set(format_paths)) == 7
formatting.write_text(json.dumps(format_paths, indent=2) + '\n')
inputs = library / 'validation/integration-simulate-comm-additions.json'
paths = json.loads(inputs.read_text()) + [target for _, target, _ in copies]
assert len(paths) == len(set(paths))
inputs.write_text(json.dumps(paths, indent=2) + '\n')
print(json.dumps(dict(applied=4, fixtures=1, batch_candidates=2, evidence=str(evidence.relative_to(repo)))))
