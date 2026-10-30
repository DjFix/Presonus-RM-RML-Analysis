"""Guarded NOAA packet/SPI application; readiness admission stays separate."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

repo = Path('/home/rs/projects/opencs/ai-line-analysis')
lib = repo/'uc-library'
candidate = lib/'candidates/noaa-spi-packets'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
control = candidate/'CONTROLLED-APPLY.json'
assert sha(control) == '32cce9d2448a812e7872f9995c25959d52cc195ef6d0e74d55f585ec836410aa'
data = json.loads(control.read_text())
handoff = candidate/'HANDOFF.json'
assert sha(handoff) == '7079a1c370d41cbda04b039455152ee3fa2275f70f28e328f66b82eeb2c5395b'
handoff_data = json.loads(handoff.read_text())
for path, digest in {**handoff_data['active_tools'], **handoff_data['frozen_original_tools']}.items():
    assert sha(lib/path) == digest, path
assert data['production_partition'] == 'RM'
assert (data['new_ready_entries'], data['new_pending_entries'],
        data['affected_ready_entries'], data['affected_pending_entries']) == (1, 4, 5, 10)
assert len(data['copies']) == len({r['target'] for r in data['copies'].values()}) == 9
assert len(data['fixture_copies']) == 6
assert sha(lib/data['final_proof']) == data['final_proof_sha256'] == '981f9bec90e8f2aac461101852fd3e10c9f500f11069d22bb3d6e04bc926e68f'
receipt = repo/'evidence/recovery/2026-10-27/noaa-spi-candidate-preflight/candidate-01/validation.json'
assert sha(receipt) == 'fd9f09929a7858f0e66a741bc5d18da336fa1161f5c339a6b4b632f9c112000a'
proof = json.loads((lib/data['final_proof']).read_text())
for path, digest in proof['sources'].items():
    assert sha(lib/path) == digest, path
for path, digest in proof.get('repository_sources', {}).items():
    assert sha(repo/path) == digest, path
review = json.loads((repo/'evidence/recovery/2026-10-27/noaa-spi-root/dependency-review.json').read_text())
assert (len(review['affected']['ready']), len(review['affected']['pending'])) == (5, 10)
assert sha(lib/review['header']) == review['preimage_sha256'] == data['header_preimage_sha256']
for name, row in data['copies'].items():
    assert sha(candidate/name) == row['sha256'], name
    if row['active_sha256'] is None:
        assert not (lib/row['target']).exists(), row['target']
    else:
        assert row['target'] == review['header'] and sha(lib/row['target']) == row['active_sha256']
parents = {
    'constructor': 'bac23332e14c8f6a63ec5bc3cccc526cdec6c446fe4d0fd6eb7ec4e5fec7576f',
    'registration': '88d53535a4be1c02999577a9a5be15db593b29328bfd661a83de571e2b5615fe',
    'assembly': 'f737251d16001f8bead1795f45cd44d5ac44d7aecefcdf283fe9fdcc5306c768',
}
fixture_digests = {}
for name, target in data['fixture_copies'].items():
    source = candidate/name
    parent = source.parent/'validation.json'
    assert sha(parent) == parents[Path(name).parts[1]]
    observed = json.loads(parent.read_text())
    digest = observed['fixture_sha256' if source.name == 'stdin.txt' else 'arm_output_sha256']
    assert sha(source) == digest and not (lib/target).exists(), name
    fixture_digests[target] = digest
stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
evidence = repo/'evidence/recovery/2026-10-27/noaa-spi-application'/stamp
backup = evidence/'before'/review['header']
backup.parent.mkdir(parents=True, exist_ok=False)
shutil.copyfile(lib/review['header'], backup)
for name, row in data['copies'].items():
    target = lib/row['target']; target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(candidate/name, target)
for name, target in data['fixture_copies'].items():
    destination = lib/target; destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(candidate/name, destination)
shutil.copyfile(control, evidence/'controlled-apply.json')
shutil.copyfile(handoff, evidence/'handoff.json')
shutil.copyfile(receipt, evidence/'candidate-preflight.json')
targets = [r['target'] for r in data['copies'].values()]
(evidence/'application.json').write_text(json.dumps(dict(
    products={p:sha(lib/p) for p in targets}, fixtures=fixture_digests,
    new_ready=1, new_pending=4, refreshed_ready=5, refreshed_pending=10,
    admission_performed=False), indent=2)+'\n')
(lib/'validation/format-noaa-spi-paths.json').write_text(json.dumps(targets, indent=2)+'\n')
(lib/'validation/integration-noaa-spi-additions.json').write_text(json.dumps(
    sorted(set(targets) | set(fixture_digests) | {'CMakeLists.txt',
        'cmake/ProductionSourceGroups.cmake', 'tools/dice_uart_assembly_replay.py'}), indent=2)+'\n')
print(json.dumps(dict(applied=9, replaced=1, fixtures=6,
    evidence=str(evidence.relative_to(repo)))))
