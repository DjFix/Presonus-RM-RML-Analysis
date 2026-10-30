"""Apply disjoint sealed AlertManager and actual SimpleReader products."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

repo = Path('/home/rs/projects/opencs/ai-line-analysis')
library = repo / 'uc-library'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
alert = library / 'candidates/panel-alert'
reader = library / 'candidates/application-reader'
alert_control = alert / 'lifecycle/CONTROLLED-APPLY.json'
reader_seal = reader / 'validation/seals/verify-01'
reader_control = reader_seal / 'controlled-apply.json'
assert sha(alert_control) == '322ec5bf462e858cb134706efede3dbf65c52c1d397204f90b6abbcf9268ed07'
assert sha(reader_control) == '6a1ef3cb4ab9e632071b6116bfffece13d884a16c8dcad7504eab46fbbf3d8ab'
assert sha(alert / 'lifecycle/validation/validation.json') == '127646bb36bf836961a3566d233fcefdabf9ae8de05a8647500cf1d2611f2145'
assert sha(reader_seal / 'constructors-ready-validation.json') == 'fb8f3d66a84475ea4f69319daf9cb95b186ba64e4395639379328a668617f21e'
assert sha(reader_seal / 'ordinary-pending-validation.json') == 'be6aaf18adeb65e07d24d71dc55879c02b0a617efe45bcf0775072ee05294174'
copies = []
for source, record in json.loads(alert_control.read_text())['copies'].items():
    copies.append((alert / source, record['target'], record['sha256']))
for record in json.loads(reader_control.read_text())['products']:
    assert record['required_destination'] == 'absent'
    copies.append((reader / record['source'], record['destination'], record['sha256']))
assert len({target for _, target, _ in copies}) == 9
for source, target, digest in copies:
    assert sha(source) == digest, str(source)
    assert not (library / target).exists(), target
fixture = alert / 'validation/arm-vectors.bin'
assert sha(fixture) == '3aff5548a7de6ec742eb469f6989aac1556d29a36cc1a2a8c6646a9196bc7666'
fixtures = [(fixture, 'validation/panel-alert-manager/arm-vectors.bin')]
handoff = json.loads((repo / 'evidence/recovery/2026-10-27/application-reader/verify-01/handoff.json').read_text())
for role in ('client', 'server'):
    source = reader_seal / (role + '-vectors.txt')
    assert sha(source) == handoff['files'][source.name]
    fixtures.append((source, 'validation/application-reader/' + source.name))
for source, target in fixtures:
    assert not (library / target).exists(), target
stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
evidence = repo / 'evidence/recovery/2026-10-27/alert-reader-application' / stamp
evidence.mkdir(parents=True)
for source, target, _ in copies:
    path = library / target
    path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, path)
for source, target in fixtures:
    path = library / target
    path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, path)
shutil.copyfile(alert_control, evidence / 'alert-controlled-apply.json')
shutil.copyfile(reader_control, evidence / 'reader-controlled-apply.json')
(evidence / 'application.json').write_text(json.dumps(dict(
    products={target: sha(library / target) for _, target, _ in copies},
    fixtures={target: sha(library / target) for _, target in fixtures},
    planned_ready_delta=12, planned_pending_delta=21,
    scope='Actual CCL services; opaque delegate slots and ordinary return declarations remain explicit pending domains'), indent=2) + '\n')
paths = [target for _, target, _ in copies]
(library / 'validation/format-alert-reader-paths.json').write_text(json.dumps(paths, indent=2) + '\n')
extra = ['CMakeLists.txt', 'cmake/ProductionSourceGroups.cmake', *[target for _, target in fixtures]]
(library / 'validation/integration-alert-reader-additions.json').write_text(json.dumps(paths + extra, indent=2) + '\n')
print(json.dumps(dict(applied=len(copies), fixtures=len(fixtures), evidence=str(evidence.relative_to(repo)))))
