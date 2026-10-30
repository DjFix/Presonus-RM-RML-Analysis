"""Preserve one excluded historical Core port outside production src/."""
import hashlib
import json
from pathlib import Path
import shutil

repo=Path('/home/rs/projects/opencs/ai-line-analysis')
lib=repo/'uc-library'
if not lib.is_dir():lib=repo/'uc-library'
name='src/Core/interpolator.cpp'
expected='6af66e7676b56d31a6a46beb6d3f4e5575cf49e47d5d7189edf0057c74c2cca4'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
for ledger in ('validation/ready-functions.json','validation/compiled-functions.json'):
    assert all(name not in row['sources'] for row in json.loads((lib/ledger).read_text())['functions'])
assert name not in json.loads((lib/'validation/integration.json').read_text())['files']
source=lib/name
relative='validation/core-upstream/history/manual-source/interpolator.cpp.txt'
target=lib/relative
if source.exists():
    assert sha(source)==expected
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():
        assert sha(target)==expected
        source.unlink()
    else:
        shutil.move(str(source),str(target))
    if not any(source.parent.iterdir()):source.parent.rmdir()
elif not target.exists():
    print(json.dumps({'no_local_legacy_source':True}))
    raise SystemExit(0)
assert sha(target)==expected
report=dict(previous=name,preserved=relative,sha256=expected,active_references=0,
    reason='Historical excluded manual Core port; actual Core is supplied by pinned CCL source.',
    new_core_binary_reconstruction=False,bytes_unchanged=True)
(target.parent/'DISPOSITION.json').write_text(json.dumps(report,indent=2)+'\n')
evidence=repo/'evidence/recovery/2026-10-27/legacy-core-source-disposition'
evidence.mkdir(parents=True,exist_ok=True)
(evidence/'disposition.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
