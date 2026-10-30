"""Guarded paired header migrations: FirmwareBundle streams and Dice lifetime."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

repo = Path('/home/rs/projects/opencs/ai-line-analysis')
lib = repo / 'uc-library'
life = lib / 'candidates/dice-uart-lifetime'
stream = lib / 'candidates/application-runtime/resource-library/stream-candidate'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
lcpath = life / 'CONTROLLED-APPLY.json'
scpath = stream / 'comment-v2/controlled-apply.json'
assert sha(lcpath) == '63392ee75405c28dc3afa4dc47f430234c3c1a49e924e48c195b965f562ed27b'
assert sha(scpath) == '3ede2a3f5fd007ca5329cc681e89494e2ec42504c2194dc86742a22758e0cb4b'
lc = json.loads(lcpath.read_text())
sc = json.loads(scpath.read_text())
assert sha(lib / lc['final_proof']) == lc['final_proof_sha256']
assert sha(stream / 'comment-v2/active_reseal.py') == 'cc2db5c9f16ac6aaa4444348516e13ba09852cfd4e16da816a2e291b3e7883cc'
review = json.loads((repo / 'evidence/recovery/2026-10-27/streams-lifetime-root/dependency-review.json').read_text())
for name, counts in [('include/presonus/application/ResourceLibrary.hpp',(8,8)),
                     ('include/presonus/dice/uart_assembly.hpp',(0,10))]:
    recorded = review['headers'][name]
    assert sha(lib / name) == recorded['preimage_sha256']
    assert tuple(len(recorded['affected'][k]) for k in ('ready','pending')) == counts
copies = []
for name, row in lc['copies'].items():
    copies.append((life / name, row['target'], row['sha256'], row['active_sha256']))
for row in sc['products']:
    previous = row.get('required_preimage_sha256')
    if previous is None:
        assert row['required_destination'] == 'absent'
    copies.append((stream / row['source'], row['destination'], row['sha256'], previous))
assert len(copies) == len({target for _,target,_,_ in copies}) == 9
for source, target, digest, previous in copies:
    assert sha(source) == digest, str(source)
    assert (sha(lib / target) == previous) if previous is not None else not (lib / target).exists()
lp = json.loads((life / 'validation/lifetime-01/validation.json').read_text())
fixture_hashes = {'fixtures.txt':lp['fixture_sha256'],'arm-output.txt':lp['arm_output_sha256']}
fixtures = [(life/source,target,fixture_hashes[Path(source).name]) for source,target in lc['fixture_copies'].items()]
fixtures.append((stream / 'validation/seals/firmware-bundle-streams-validation-01/fixtures.json',
                 'validation/application-firmware-stream/fixtures.json',
                 'e2ef52262b7209f981ecbba7b08745a5b46a9056f583f9bf90f1fd4369189da8'))
for source,target,digest in fixtures:
    assert sha(source) == digest and not (lib/target).exists(), target
stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
evidence = repo / 'evidence/recovery/2026-10-27/streams-lifetime-application' / stamp
evidence.mkdir(parents=True,exist_ok=False)
for _,target,_,previous in copies:
    if previous is not None:
        backup = evidence/'before'/target
        backup.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(lib/target,backup)
for source,target,_,_ in copies:
    destination = lib/target
    destination.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(source,destination)
for source,target,_ in fixtures:
    destination = lib/target
    destination.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(source,destination)
shutil.copyfile(lcpath,evidence/'lifetime-controlled-apply.json')
shutil.copyfile(scpath,evidence/'streams-controlled-apply.json')
(evidence/'application.json').write_text(json.dumps(dict(
    products={target:sha(lib/target) for _,target,_,_ in copies},
    fixtures={target:sha(lib/target) for _,target,_ in fixtures},
    planned_new_ready=5,planned_new_pending=6,refreshed_ready=8,refreshed_pending=18,
    scope='Modern CCL/zlib source port; original ARM thunks remain unready; preserve all prior identities.'),indent=2)+'\n')
paths = [target for _,target,_,_ in copies]
(lib/'validation/format-streams-lifetime-paths.json').write_text(json.dumps(
    [p for p in paths if p.endswith(('.cpp','.hpp','.h'))],indent=2)+'\n')
(lib/'validation/integration-streams-lifetime-additions.json').write_text(json.dumps(
    paths+[target for _,target,_ in fixtures]+['CMakeLists.txt','cmake/ProductionSourceGroups.cmake'],indent=2)+'\n')
print(json.dumps(dict(applied=9,replaced=2,fixtures=3,evidence=str(evidence.relative_to(repo)))))
