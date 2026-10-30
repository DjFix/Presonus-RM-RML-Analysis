"""Apply reviewed UART registration, preserving its previous header evidence."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

repo = Path('/home/rs/projects/opencs/ai-line-analysis')
library = repo / 'uc-library'
candidate = library / 'candidates/dice-packet-log-registration'
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
control = json.loads((candidate / 'CONTROLLED-APPLY.json').read_text())
proof = candidate / 'validation/candidate-01/validation.json'
assert sha(proof) == 'e7e00e056f57ed983ae892c7179a0280bbea305762ebc9427a60efff7508ae33'
base = control['header_base']['sources']
for source, record in control['copies'].items():
    assert sha(candidate / source) == record['sha256'], source
    target = library / record['target']
    assert (sha(target) if target.exists() else None) == base.get(record['target']), str(target)
fixtures = {}
for name in ('registration-fixtures.txt', 'registration-arm-output.txt'):
    source = candidate / 'validation/candidate-01' / name
    assert source.is_file(), source
    target = library / 'validation/dice-uart-registration' / name
    assert not target.exists(), target
    fixtures[source] = target
stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
evidence = repo / 'evidence/recovery/2026-10-27/uart-registration-application' / stamp
evidence.mkdir(parents=True)
paths = []
for source, record in control['copies'].items():
    target = library / record['target']
    if target.exists():
        saved = evidence / 'before' / record['target']
        saved.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(target, saved)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(candidate / source, target)
    paths.append(record['target'])
for source, target in fixtures.items():
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
shutil.copyfile(candidate / 'CONTROLLED-APPLY.json', evidence / 'CONTROLLED-APPLY.json')
(evidence / 'application.json').write_text(json.dumps({
    'candidate_proof_sha256': sha(proof), 'sources': {p: sha(library / p) for p in paths},
    'fixtures': {str(p.relative_to(library)): sha(p) for p in fixtures.values()},
    'ready_delta': 0, 'new_pending': 2, 'old_pending_reseal_required': 1,
}, indent=2) + '\n')
(library / 'validation/format-uart-registration-paths.json').write_text(json.dumps(paths, indent=2) + '\n')
extra = ['CMakeLists.txt', 'cmake/ProductionSourceGroups.cmake',
         *[str(p.relative_to(library)) for p in fixtures.values()]]
(library / 'validation/integration-uart-registration-additions.json').write_text(
    json.dumps(paths + extra, indent=2) + '\n')
print(json.dumps({'applied': len(paths), 'evidence': str(evidence.relative_to(repo))}))
