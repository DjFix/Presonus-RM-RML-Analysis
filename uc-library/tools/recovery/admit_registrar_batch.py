"""Fixed registrar-only guards around the unchanged readiness merger."""
from pathlib import Path
import argparse,hashlib,json,subprocess,sys
p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');a=p.parse_args()
repo=Path.cwd().resolve();lib=repo/'uc-library';out=repo/'evidence/recovery/2026-10-28/registrar-batch'
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
keys=lambda rows:{(r['original_elf_sha256'],r['mangled']) for r in rows}
def state():
    return {str(p.relative_to(lib)):sha(p) for p in [lib/'validation/ready-functions.json',lib/'validation/compiled-functions.json',*sorted((lib/'validation/history').rglob('*'))] if p.is_file()}
network='candidates/uc-network-registrar-services/validation/active-seal-01/'
spi='validation/noaa-spi-service-registrar/root-closure-01/'
assert read(lib/'candidates/uc-network-registrar-services/validation/active-01/validation.json')['active_source_replay_passed']
assert read(lib/network/'pending-validation.json')['active_source_replay_passed']
raw=read(out/'raw-active-01/validation.json');assert raw['passed'] and raw['canonical_ctest_count']==146
headers=read(out/'public-headers.log');assert headers['headers']==91 and headers['returncode']==0
assert read(lib/'validation/integration.json')['test_suites']==146
inputs={'--fragment':[spi+'ready-functions.fragment.json'],'--pending':[network+'pending-fragment.json',spi+'pending-functions.fragment.json']}
command=[sys.executable,str(lib/'tools/merge_readiness.py'),'--library',str(lib)]
for flag,names in inputs.items():
    for name in names:
        path=(lib/name).resolve();assert path.is_relative_to(lib) and path.is_file();command.extend([flag,name])
preflight=out/'combined-preflight-01'
if not a.apply:
    preflight.mkdir();before=state();r=subprocess.run(command+['--dry-run'],capture_output=True,text=True)
    (preflight/'stdout.log').write_text(r.stdout);(preflight/'stderr.log').write_text(r.stderr);assert r.returncode==0,r.stderr[-5000:]
    d=json.loads(r.stdout);assert (d['portable_ready_entries'],d['unique_mangled_methods'],d['compiled_declaration_pending_entries'])==(639,343,485),d
    assert not d['stale_previous_entries'] and not d['demoted_entries'] and not d['promoted_pending_entries']
    assert before==state()
    proof=dict(passed=True,result=d,unchanged_state=before,command=command,inputs={name:sha(lib/name) for paths in inputs.values() for name in paths},tool_sha256=sha(Path(__file__)))
    (preflight/'validation.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(dict(preflight_passed=True,ready=639,names=343,pending=485)));raise SystemExit(0)
proof=read(preflight/'validation.json');assert proof['passed'] and proof['tool_sha256']==sha(Path(__file__)) and proof['unchanged_state']==state() and proof['command']==command
for name,digest in proof['inputs'].items():assert sha(lib/name)==digest,name
oldready=read(lib/'validation/ready-functions.json')['functions'];oldpending=read(lib/'validation/compiled-functions.json')['functions'];assert (len(oldready),len(oldpending))==(639,467)
admission=out/'admission-01';admission.mkdir();r=subprocess.run(command,capture_output=True,text=True)
(admission/'stdout.log').write_text(r.stdout);(admission/'stderr.log').write_text(r.stderr);assert r.returncode==0,r.stderr[-5000:]
ready=read(lib/'validation/ready-functions.json')['functions'];pending=read(lib/'validation/compiled-functions.json')['functions']
assert (len(ready),len({r['mangled'] for r in ready}),len(pending))==(639,343,485)
assert keys(ready)==keys(oldready) and keys(oldpending)<=keys(pending) and not keys(ready)&keys(pending)
added=keys(pending)-keys(oldpending);assert len(added)==18 and len({name for _,name in added})==9
report=dict(passed=True,ready=639,ready_unique_names=343,pending=485,new_ready=0,new_pending_records=18,new_pending_unique_names=9,no_silent_removals=True,demotions=0,preflight_sha256=sha(preflight/'validation.json'),tool_sha256=sha(Path(__file__)))
(admission/'validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
