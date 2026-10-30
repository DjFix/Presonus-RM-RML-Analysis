"""Apply reviewed original manager wrappers and one shared startup engine."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

repo = Path('/home/rs/projects/opencs/ai-line-analysis')
library = repo / 'uc-library'
candidate = library / 'candidates/application-managers'
sealed = candidate / 'validation/seals/verify-03'
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
control_file = sealed / 'controlled-apply.json'
assert sha(control_file) == '8bca6f5cbb276259d182b3ede0a32cb9bd6527db11b73f48d040b8f5c056562d'
control = json.loads(control_file.read_text())
proof = sealed / 'validation.json'
assert sha(proof) == control['source_proof_sha256']
assert sha(proof) == '4c1aa0301e4134ed4ec893f3cf786728c3fd73e53e4ed4a7b3aa2309846ea8d2'
for record in control['products']:
    assert sha(candidate / record['source']) == record['sha256'], record['source']
    assert record['required_destination'] == 'absent'
    assert not (library / record['destination']).exists(), record['destination']
fixtures = {}
arm_path = sealed / 'original/arm-proof.json'
source_proof = json.loads(proof.read_text())
assert sha(arm_path) == source_proof['original_arm_proof']['sha256']
arm = json.loads(arm_path.read_text())
for role in ('client', 'server'):
    name = role + '-vectors.txt'
    source = sealed / name
    # Independently check the text fixture against SHA-bound original JSON.
    original = sealed / 'original' / (role + '-vectors.json')
    assert sha(original) == arm[role]['fixture_sha256']
    lines = []
    for row in json.loads(original.read_text()):
        c, e = row['input'], row['expected']
        values = [c[k] for k in ('op', 'argc', 'app', 'mode', 'result', 'mask', 'release_mask', 'mutargc', 'singleton')]
        values.extend((int(c['home'] is not None), int(c['name'] is not None), json.dumps(c['home'] or ''), json.dumps(c['name'] or '')))
        values.extend(e[k] for k in ('result', 'argc', 'argv', 'app', 'singleton'))
        values.append(json.dumps('|'.join(e['events'])))
        lines.append(' '.join(str(int(x)) if isinstance(x, bool) else str(x) for x in values))
    assert source.read_bytes() == ('\n'.join(lines) + '\n').encode(), name
    target = library / 'validation/application-managers' / name
    assert not target.exists(), target
    fixtures[source] = target
stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
evidence = repo / 'evidence/recovery/2026-10-27/application-managers-application' / stamp
evidence.mkdir(parents=True)
paths = []
for record in control['products']:
    target = library / record['destination']
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(candidate / record['source'], target)
    paths.append(record['destination'])
for source, target in fixtures.items():
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
shutil.copyfile(control_file, evidence / 'controlled-apply.json')
(evidence / 'application.json').write_text(json.dumps({
    'source_proof_sha256': sha(proof), 'products': {p: sha(library / p) for p in paths},
    'fixtures': {str(p.relative_to(library)): sha(p) for p in fixtures.values()},
    'planned_pending_delta': 22, 'ready_delta': 0,
    'remaining_dependencies': 'SimpleReader and concrete app construction/lifecycle/release endpoints; complete application and original ARM ABI unverified',
}, indent=2) + '\n')
(library / 'validation/format-application-managers-paths.json').write_text(json.dumps(paths, indent=2) + '\n')
extra = ['CMakeLists.txt', 'cmake/ProductionSourceGroups.cmake',
         *[str(p.relative_to(library)) for p in fixtures.values()]]
(library / 'validation/integration-application-managers-additions.json').write_text(
    json.dumps(paths + extra, indent=2) + '\n')
print(json.dumps({'applied': len(paths), 'evidence': str(evidence.relative_to(repo))}))
