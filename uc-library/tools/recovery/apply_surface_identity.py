"""Guarded SurfaceApplication identity application; no readiness admission."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

repo = Path('/home/rs/projects/opencs/ai-line-analysis')
lib = repo / 'uc-library'
candidate = lib / 'candidates/application-runtime/application-identity'
seal = candidate / 'validation/seals/application-identity-validation-02'
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
control = seal / 'controlled-apply.json'
assert sha(control) == '730f699e64b185a1f929fb60b2378b6a0f9db7e84fa47bc1e366bc1055341bfe'
mapping = json.loads(control.read_text())
assert (mapping['new_ready'], mapping['new_pending'], mapping['refreshed_pending']) == (0, 2, 1)
targets = {row['destination'] for row in mapping['products']}
assert targets == {
    'src/application/SurfaceApplicationIdentity.cpp',
    'include/presonus/application/SurfaceApplication.hpp',
    'tests/application_identity_bridge.cpp',
    'tools/application_identity/replay_fixture.py',
}
review = json.loads((repo/'evidence/recovery/2026-10-27/panel-identity-root/dependency-review.json').read_text())
assert len(review['affected']['ready']) == 0 and len(review['affected']['pending']) == 1
assert sha(lib/review['header']) == review['preimage_sha256']
for row in mapping['products']:
    assert sha(candidate/row['source']) == row['sha256']
    destination = lib/row['destination']
    if 'required_preimage_sha256' in row:
        assert sha(destination) == row['required_preimage_sha256'] == review['preimage_sha256']
    else:
        assert row['required_destination'] == 'absent' and not destination.exists()
pending = json.loads((seal/'pending-fragment.json').read_text())
assert len(pending) == 3
assert sha(seal/'pending-fragment.json') == '55083f66c54a25ff51db821720c0a7fbb3b362c5efee8bb16412738b224bd22a'
for row in pending:
    assert sha(lib/row['validation']) == row['validation_sha256']
    for path, digest in row['sources'].items():
        assert sha(lib/path) == digest
    for path, digest in row.get('repository_sources', {}).items():
        assert sha(repo/path) == digest
fixture = seal/'fixtures.json'
fixture_target = lib/'validation/application-identity/fixtures.json'
assert not fixture_target.exists()
fixture_data = json.loads(fixture.read_text())
assert fixture_data['case_count'] == 22602 and not fixture_data['original_core_binary_executed']
stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
evidence = repo/'evidence/recovery/2026-10-27/surface-identity-application'/stamp
backup = evidence/'before'/review['header']
backup.parent.mkdir(parents=True, exist_ok=False)
shutil.copyfile(lib/review['header'], backup)
for row in mapping['products']:
    destination = lib/row['destination']
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(candidate/row['source'], destination)
fixture_target.parent.mkdir(parents=True, exist_ok=True)
shutil.copyfile(fixture, fixture_target)
shutil.copyfile(control, evidence/'controlled-apply.json')
(evidence/'application.json').write_text(json.dumps(dict(
    products={p:sha(lib/p) for p in sorted(targets)},
    fixture_sha256=sha(fixture_target), new_ready=0, new_pending=2,
    refreshed_pending=1, admission_performed=False), indent=2)+'\n')
(lib/'validation/format-panel-identity-paths.json').write_text(json.dumps(
    sorted(p for p in targets if Path(p).suffix in ('.cpp','.hpp','.h')), indent=2)+'\n')
(lib/'validation/integration-panel-identity-additions.json').write_text(json.dumps(
    sorted(targets | {'validation/application-identity/fixtures.json',
                      'CMakeLists.txt', 'cmake/ProductionSourceGroups.cmake'}), indent=2)+'\n')
print(json.dumps(dict(applied=4, replaced=1, fixtures=1,
    evidence=str(evidence.relative_to(repo)))))
