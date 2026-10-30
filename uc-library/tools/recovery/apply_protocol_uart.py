"""Guarded application of frozen Protocol/base codecs and UART products."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

repo = Path('/home/rs/projects/opencs/ai-line-analysis')
library = repo / 'uc-library'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
base = library / 'candidates/panel-protocol-comm'
uart = library / 'candidates/panel-uart-comm'
assert sha(base / 'CONTROLLED-APPLY.json') == '5617fc326413aafcf9312532de2f999f880a1b46bd14385009199386871e630b'
assert sha(base / 'validation/combined/validation.json') == '617bfa899be3597721be7f60136a61bea97616ae47a7542d5adbd3b2fe02d10a'
assert sha(uart / 'CONTROLLED-APPLY.json') == '4e6dbaee96e900c564ef84179e4a77827751aa46489fe6e42c3f35e056191387'
assert sha(uart / 'validation/seals/candidate-01/validation.json') == 'bcffccad2597fe7500496f19950bd736152c57588f47e2c2520c9e67295a036b'
base_control = json.loads((base / 'CONTROLLED-APPLY.json').read_text())
uart_control = json.loads((uart / 'CONTROLLED-APPLY.json').read_text())
copies = []
for directory, control in ((base, base_control), (uart, uart_control)):
    for source, record in control['copies'].items():
        copies.append((directory / source, record['target'], record['sha256']))
assert len(copies) == len({target for _, target, _ in copies}) == 10
fixtures = []
for source, target in base_control['fixture_copies'].items():
    path = base / source
    oracle = json.loads((path.parent / 'oracle.json').read_text())
    assert sha(path) == oracle['vectors_sha256']
    fixtures.append((path, target, sha(path)))
uart_proof = json.loads((uart / 'validation/seals/candidate-01/validation.json').read_text())
for name in ('fixtures.txt', 'client-arm-output.txt', 'server-arm-output.txt'):
    source = uart / 'validation/compare-01' / name
    digest = uart_proof['sources'][str(source.relative_to(library))]
    fixtures.append((source, 'validation/panel-uart-comm/' + name, digest))
for source, target, digest in copies + fixtures:
    assert sha(source) == digest, str(source)
    assert not (library / target).exists(), target
stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
evidence = repo / 'evidence/recovery/2026-10-27/panel-protocol-uart-application' / stamp
evidence.mkdir(parents=True, exist_ok=False)
for source, target, _ in copies + fixtures:
    destination = library / target
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
for label, directory in (('protocol', base), ('uart', uart)):
    shutil.copyfile(directory / 'CONTROLLED-APPLY.json', evidence / (label + '-controlled-apply.json'))
(evidence / 'application.json').write_text(json.dumps(dict(
    products={target: sha(library / target) for _, target, _ in copies},
    fixtures={target: sha(library / target) for _, target, _ in fixtures},
    planned_ready_delta=16, planned_pending_delta=26,
    scope='Dependency-ordered shared source port, genuine CCL; ordinary declarations remain pending.'), indent=2) + '\n')
paths = [target for _, target, _ in copies]
(library / 'validation/format-protocol-uart-paths.json').write_text(json.dumps(paths, indent=2) + '\n')
extra = ['CMakeLists.txt', 'cmake/ProductionSourceGroups.cmake', 'tools/dice_uart_assembly_replay.py',
         *[target for _, target, _ in fixtures]]
(library / 'validation/integration-protocol-uart-additions.json').write_text(json.dumps(paths + extra, indent=2) + '\n')
print(json.dumps(dict(applied=len(copies), fixtures=len(fixtures), evidence=str(evidence.relative_to(repo)))))
