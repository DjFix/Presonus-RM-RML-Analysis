"""Atomically adopt frozen packet prerequisites, then the reviewed wait merge."""
import datetime
import hashlib
import json
from pathlib import Path
import shutil

repo=Path('/home/rs/projects/opencs/ai-line-analysis')
lib=repo/'uc-library'
packet=lib/'validation/dice-packet-candidate'
wait=lib/'validation/dice-response-candidate'
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
pm=json.loads((packet/'apply-manifest.json').read_text())
wm=json.loads((wait/'apply-manifest.json').read_text())
assert sha(packet/'apply-manifest.json')==wm['packet_prerequisite']['manifest_sha256']
assert sha(lib/pm['candidate_proof'])==pm['candidate_proof_sha256']
assert sha(lib/wm['proof'])==wm['proof_sha256']
assert sha(lib/'include/presonus/dice/sysex.hpp')==pm['base_header_sha256']
for base, rows in ((packet,pm['files']),(wait,wm['files'])):
    for row in rows:
        assert sha(base/row['candidate'])==row['sha256'],row['candidate']
        if row['target']!='include/presonus/dice/sysex.hpp':
            assert not (lib/row['target']).exists(),row['target']
merged=wait/'include/presonus/dice/sysex.hpp'
assert sha(merged)==wm['shared_header_merge']['candidate_header_sha256']
stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
evidence=repo/'evidence/recovery/2026-10-27/dice-packet-response-application'/stamp
evidence.mkdir(parents=True)
for name in ('include/presonus/dice/sysex.hpp','validation/ready-functions.json',
             'validation/compiled-functions.json','validation/integration.json'):
    target=evidence/'before'/name
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(lib/name,target)
paths=[]
for base, rows in ((packet,pm['files']),(wait,wm['files'])):
    if base==wait:
        header=lib/'include/presonus/dice/sysex.hpp'
        assert sha(header)==wm['shared_header_merge']['base_frozen_packet_header_sha256']
        shutil.copyfile(header,evidence/'packet-prerequisite-header.hpp')
        # Full reviewed merge is adopted only after every packet prerequisite.
        # Its frozen diff is retained alongside the before/after identities.
        shutil.copyfile(merged,header)
        shutil.copyfile(wait/'packet-to-waits.patch',evidence/'packet-to-waits.patch')
    for row in rows:
        target=lib/row['target']
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(base/row['candidate'],target)
        paths.append(row['target'])
assert sha(lib/'include/presonus/dice/sysex.hpp')==wm['shared_header_merge']['candidate_header_sha256']
paths.append('tests/dice_packet_clock_tests.cpp')
(evidence/'manifests.json').write_text(json.dumps({'packet':pm,'wait':wm},indent=2)+'\n')
(lib/'validation/format-dice-packet-response-paths.json').write_text(json.dumps(sorted(set(paths)),indent=2)+'\n')
extra=['CMakeLists.txt']
fixtures=packet/'runs/20261026T220418.737889Z'
extra.extend(str((fixtures/name).relative_to(lib)) for name in ('constructors.txt','commands.txt','receivers.txt'))
waitproof=json.loads((lib/wm['proof']).read_text())
replay=lib/waitproof['input_replay']['path']
extra.extend(str((replay.parent/(role+'-response-vectors.txt.gz')).relative_to(lib)) for role in ('client','server'))
(lib/'validation/integration-dice-packet-response-additions.json').write_text(json.dumps(sorted(set(paths+extra)),indent=2)+'\n')
print(json.dumps({'applied_products':len(paths),'evidence':str(evidence.relative_to(repo)), 'wait_fixture_directory':str(replay.parent.relative_to(lib))}))
