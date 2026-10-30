"""Guarded logger integration; dependency proofs must be freshly resealed."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

repo = Path('/home/rs/projects/opencs/ai-line-analysis')
library = repo / 'uc-library'
candidate = library / 'candidates/dice-packet-log'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
control_file = candidate / 'CONTROLLED-APPLY.json'
control = json.loads(control_file.read_text())
proof = candidate / control['candidate_proof']
assert sha(proof) == control['candidate_proof_sha256'] == '0ee9743d499ab3cbce098d8e2f5803a4689854a0f0902d91e921cdf6984a27d0'
for source, record in control['copies'].items():
    assert sha(candidate / source) == record['sha256'], source
    target = library / record['target']
    assert (sha(target) if target.exists() else None) == control['header_base'].get(record['target']), record['target']
fixtures = sorted(proof.parent.glob('*-fixtures.txt')) + sorted(proof.parent.glob('*-arm-output.txt'))
assert len(fixtures) == 21
for source in fixtures:
    assert not (library / 'validation/dice-packet-log' / source.name).exists()
stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
evidence = repo / 'evidence/recovery/2026-10-27/packet-logging-application' / stamp
evidence.mkdir(parents=True)
paths = []
for source, record in control['copies'].items():
    target = library / record['target']
    if target.exists():
        before = evidence / 'before' / record['target']
        before.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(target, before)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(candidate / source, target)
    paths.append(record['target'])
for source in fixtures:
    target = library / 'validation/dice-packet-log' / source.name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
shutil.copyfile(control_file, evidence / 'CONTROLLED-APPLY.json')
(evidence / 'application.json').write_text(json.dumps({
    'candidate_proof_sha256': sha(proof), 'products': {p: sha(library / p) for p in paths},
    'fixtures': {p.name: sha(p) for p in fixtures}, 'affected_old_records': 20,
    'new_pending': 3, 'explicit_old_getter_demotion_required': True,
}, indent=2) + '\n')
variant = 'candidates/application-managers/lifecycle-variant/variant_tests.cpp'
assert (library / variant).is_file()
(library / 'validation/format-packet-logging-paths.json').write_text(
    json.dumps(paths + [variant], indent=2) + '\n')
extra = ['CMakeLists.txt', 'cmake/ProductionSourceGroups.cmake',
         'tools/packet_logging_replay.py', 'tools/merge_readiness.py',
         'candidates/dice-packet-log/demotions.json', variant,
         *['validation/dice-packet-log/' + p.name for p in fixtures]]
(library / 'validation/integration-packet-logging-additions.json').write_text(
    json.dumps(paths + extra, indent=2) + '\n')
print(json.dumps({'applied': len(paths), 'fixtures': len(fixtures), 'evidence': str(evidence.relative_to(repo))}))
