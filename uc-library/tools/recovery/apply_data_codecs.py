"""Apply reviewed common UC data codecs; coordinator owns readiness metadata."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

repo = Path('/home/rs/projects/opencs/ai-line-analysis')
library = repo / 'uc-library'
candidate = library / 'candidates/uc-data-codecs'
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
control_path = candidate / 'CONTROLLED-APPLY.json'
assert sha(control_path) == 'badb6f084de4481c093ecb8ca24f0378ace7455b600b7ca1cd7b7f5a6c0bc595'
control = json.loads(control_path.read_text())
proof = candidate / 'validation/validation.json'
assert sha(proof) == '2395f96314dfae53c87d56d3f5eab376049a039007fb0f8879307fdf616fb3f2'
for name, record in control['copies'].items():
    assert sha(candidate / name) == record['sha256'], name
    target = library / record['target']
    assert (sha(target) if target.exists() else None) == record['active_sha256'], record['target']
fixture = candidate / 'validation/arm-vectors.bin'
assert sha(fixture) == '193ed0d1239d416b21311dca0fa4cce9832d16f882fc97f3829a6e685d6f8bd0'
target_fixture = library / 'validation/uc-data-codecs/arm-vectors.bin'
assert not target_fixture.exists()
stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
evidence = repo / 'evidence/recovery/2026-10-27/data-codecs-application' / stamp
evidence.mkdir(parents=True)
paths = []
for name, record in control['copies'].items():
    target = library / record['target']
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(candidate / name, target)
    paths.append(record['target'])
target_fixture.parent.mkdir(parents=True, exist_ok=True)
shutil.copyfile(fixture, target_fixture)
shutil.copyfile(control_path, evidence / 'CONTROLLED-APPLY.json')
(evidence / 'application.json').write_text(json.dumps({
    'candidate_proof_sha256': sha(proof), 'copied_sources': {p: sha(library / p) for p in paths},
    'fixture_sha256': sha(target_fixture), 'planned_numeric_ready_delta': 16,
    'planned_pointer_declaration_pending_delta': 2,
    'declaration_note': 'Candidate18-ready metadata is historical; active producer must split2 create pointer-return entries pending.',
}, indent=2) + '\n')
(library / 'validation/format-data-codecs-paths.json').write_text(json.dumps(paths, indent=2) + '\n')
extras = ['CMakeLists.txt', 'cmake/ProductionSourceGroups.cmake',
          'validation/uc-data-codecs/arm-vectors.bin']
(library / 'validation/integration-data-codecs-additions.json').write_text(
    json.dumps(paths + extras, indent=2) + '\n')
print(json.dumps({'applied': len(paths), 'evidence': str(evidence.relative_to(repo))}))
