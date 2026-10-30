"""Guarded Dice transport header replacement plus disjoint shared DelayTimer."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

repo = Path('/home/rs/projects/opencs/ai-line-analysis')
library = repo / 'uc-library'
dice = library / 'candidates/dice-uart-next'
timer = library / 'candidates/panel-delay-timer'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(dice / 'CONTROLLED-APPLY.json') == 'a6acee3a7c8158709a9a4d363c9c7e40a91d89752e6ce052d564d0ab40e3a872'
assert sha(timer / 'CONTROLLED-APPLY.json') == '216e3e8e958cfde6b9541271e6630bdf3b803a8538db448e65d7fabbbbb8ab76'
dc = json.loads((dice / 'CONTROLLED-APPLY.json').read_text())
tc = json.loads((timer / 'CONTROLLED-APPLY.json').read_text())
assert sha(library / dc['final_proof']) == dc['final_proof_sha256']
for name, digest in tc['frozen_proofs'].items():
    assert sha(timer / name) == digest, name
for name, digest in tc['base_product_bindings'].items():
    assert sha(library / name) == digest, name
assert sha(timer / 'reseal_active.py') == tc['active_reseal_sha256']
ready = json.loads((library / 'validation/ready-functions.json').read_text())['functions']
pending = json.loads((library / 'validation/compiled-functions.json').read_text())['functions']
assert len(ready) == 497 and len(pending) == 150
review = json.loads((repo / 'evidence/recovery/2026-10-27/dice-transport-root/dependency-review.json').read_text())
assert not review['affected']['ready']
key = lambda row: (row['original_elf_sha256'], row['mangled'])
affected = {key(row) for row in dc['affected_old_entries']}
assert len(affected) == 6 and affected == {key(row) for row in review['affected']['pending']}
assert affected <= {key(row) for row in pending}
for row in dc['affected_old_entries']:
    assert sha(library / row['validation']) == row['validation_sha256']
copies = []
for directory, control in ((dice, dc), (timer, tc)):
    for source, record in control['copies'].items():
        target = library / record['target']
        assert sha(directory / source) == record['sha256'], source
        previous = record['active_sha256']
        assert (sha(target) == previous) if previous is not None else not target.exists()
        copies.append((directory / source, record['target'], record['sha256'], previous))
assert len(copies) == len({target for _, target, _, _ in copies}) == 8
fixtures = []
fixture_hashes = {'fixtures.txt': '0de87992f067b7534a2f6a14cd3d799c4000064439a190a7e132cbd5d63296c7',
                 'arm-output.txt': 'f63a8363a8e1abdeddad309dff07d382e8f262d2f1677ddc8de9f545921e90a0'}
for source, target in dc['fixture_copies'].items():
    fixtures.append((dice / source, target, fixture_hashes[Path(source).name]))
for source, target in tc['fixture_copies'].items():
    fixtures.append((timer / source, target, tc['fixture_sha256']))
for source, target, digest in fixtures:
    assert sha(source) == digest and not (library / target).exists(), target
stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
evidence = repo / 'evidence/recovery/2026-10-27/dice-timer-application' / stamp
evidence.mkdir(parents=True, exist_ok=False)
for source, target, _, previous in copies:
    if previous is not None:
        backup = evidence / 'before' / target
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(library / target, backup)
for source, target, _, _ in copies:
    destination = library / target
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
for source, target, _ in fixtures:
    destination = library / target
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
for label, directory in (('dice', dice), ('timer', timer)):
    shutil.copyfile(directory / 'CONTROLLED-APPLY.json', evidence / (label + '-controlled-apply.json'))
(evidence / 'application.json').write_text(json.dumps(dict(
    products={target: sha(library / target) for _, target, _, _ in copies},
    fixtures={target: sha(library / target) for _, target, _ in fixtures},
    planned_ready_delta=8, planned_pending_delta=20, old_pending_refreshes=6,
    scope='Shared clock-backed timer, CS18 transport; ordinary declarations and bounded adaptations explicit.'), indent=2) + '\n')
paths = [target for _, target, _, _ in copies]
(library / 'validation/format-dice-timer-paths.json').write_text(json.dumps(paths, indent=2) + '\n')
(library / 'validation/integration-dice-timer-additions.json').write_text(json.dumps(
    paths + [target for _, target, _ in fixtures] + ['CMakeLists.txt', 'cmake/ProductionSourceGroups.cmake'], indent=2) + '\n')
print(json.dumps(dict(applied=8, replaced=1, fixtures=3, old_pending_refreshes=6, evidence=str(evidence.relative_to(repo)))))
