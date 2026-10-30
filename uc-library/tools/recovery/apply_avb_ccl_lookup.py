"""Apply the frozen AVB lookup/list binding after checking all source identities."""
import datetime
import hashlib
import json
from pathlib import Path
import shutil

repo = Path('/home/rs/projects/opencs/ai-line-analysis')
lib = repo / 'uc-library'
candidate = lib / 'validation/avb-lookup-candidate'
manifest = json.loads((candidate / 'apply-manifest.json').read_text())
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
assert sha(lib / manifest['proof']) == manifest['proof_sha256']
for row in manifest['files']:
    assert sha(candidate / row['candidate']) == row['sha256']
    active = lib / row['target']
    assert (sha(active) if active.exists() else None) == row['previous_active_sha256'], row['target']
for name, digest in manifest['unchanged_product_sources'].items():
    assert sha(lib / name) == digest, name
stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
evidence = repo / 'evidence/recovery/2026-10-27/avb-ccl-application' / stamp
for row in manifest['files']:
    active = lib / row['target']
    if active.exists():
        backup = evidence / 'before' / row['target']
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(active, backup)
    active.parent.mkdir(parents=True, exist_ok=True)
    # Current mtime is intentional: force source-aware incremental rebuilds.
    shutil.copyfile(candidate / row['candidate'], active)
paths = [row['target'] for row in manifest['files']]
(lib / 'validation/format-avb-ccl-paths.json').write_text(json.dumps(paths, indent=2) + '\n')
fixtures = 'validation/avb-lookup-candidate/runs/20261027T020329.112061Z/'
extra = ['CMakeLists.txt', 'tools/avb_lookup_active_reseal.py',
         'validation/avb-lookup-candidate/tests/lookup_tests.cpp',
         fixtures+'client-lookup-vectors.txt', fixtures+'server-lookup-vectors.txt']
(lib / 'validation/integration-avb-ccl-additions.json').write_text(json.dumps(paths+extra, indent=2) + '\n')
(evidence / 'apply-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
print(json.dumps({'applied': len(paths), 'evidence': str(evidence.relative_to(repo))}))
