"""Read-only final hash audit for this cohort's zero-row typed prerequisite."""
import hashlib
import json
from pathlib import Path

repo = Path.cwd().resolve()
lib = repo / 'uc-library'
out = repo / 'evidence/recovery/2026-10-28/handler-events-batch'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text())
manifest_path = out / 'FINAL-FRAGMENTS.json'
manifest = read(manifest_path)
checked = {}

def check(path, digest):
    assert path.resolve().is_relative_to(repo)
    assert sha(path) == digest, str(path)
    checked[str(path.relative_to(repo))] = digest

for name, digest in {**manifest['prerequisite_hashes'], **manifest['source_hashes']}.items():
    check(lib / name, digest)
for name in manifest['prerequisite_hashes']:
    proof = read(lib / name)
    assert proof['passed'] and proof['active_source_replay_passed']
    assert proof['new_original_function_rows'] == proof['ready_rows'] == proof['pending_rows'] == 0
    for source, digest in proof['repository_sources'].items():
        check(repo / source, digest)
    if 'native_proof' in proof:
        check(lib / proof['native_proof'], proof['native_proof_sha256'])
report = dict(passed=True, independent_prerequisite=True, original_rows=0,
              checked_files=len(checked), files=checked,
              manifest_sha256=sha(manifest_path), tool_sha256=sha(Path(__file__)),
              scope='Current source/proof hashes for installed typed views and builders; no original class declaration/layout/ABI or hardware claim.')
(out / 'prerequisite-checkpoint-audit.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({k: v for k, v in report.items() if k != 'files'}))
