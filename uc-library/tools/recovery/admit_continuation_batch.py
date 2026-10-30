"""Fixed continuation batch guards around the unchanged readiness merger."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path

p=argparse.ArgumentParser();p.add_argument('--dice-ready',required=True);p.add_argument('--dice-pending',required=True);p.add_argument('--apply',action='store_true');a=p.parse_args()
repo=Path.cwd().resolve();lib=repo/'uc-library';out=repo/'evidence/recovery/2026-10-28/continuation-batch'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();read=lambda p:json.loads(p.read_text())
keys=lambda rows:{(r['original_elf_sha256'],r['mangled']) for r in rows}
def state():
    files=[lib/'validation/ready-functions.json',lib/'validation/compiled-functions.json',*sorted((lib/'validation/history').rglob('*'))]
    return {str(p.relative_to(lib)):sha(p) for p in files if p.is_file()}
biquad='candidates/dsp-biquad-incremental/validation/active-01/'
network='candidates/uc-network-continuation/validation/active-seal-01/'
manager='candidates/dice-next-services/validation/continuation-manager-01/'
spi='validation/noaa-spi-service-continuation/root-closure-01/'
assert read(lib/biquad/'audit.json')['actual_production_source_gate_passed']
assert read(lib/'candidates/uc-network-continuation/validation/active-01/validation.json')['active_source_replay_passed']
assert read(lib/network/'pending-validation.json')['active_source_replay_passed']
assert read(lib/manager/'audit.json')['active_source_replay_passed']
raw=read(out/'raw-active-01/validation.json');assert raw['passed'] and raw['canonical_ctest_count']==139
headers=read(out/'public-headers.log');assert headers['headers']==89 and headers['returncode']==0
assert read(lib/'validation/integration.json')['test_suites']==139
inputs={'--fragment':[a.dice_ready,biquad+'constructor-ready.fragment.json',spi+'ready-functions.fragment.json'],
        '--pending':[a.dice_pending,network+'pending-fragment.json',manager+'pending.fragment.json',biquad+'pending.fragment.json',spi+'pending-functions.fragment.json']}
command=[sys.executable,str(lib/'tools/merge_readiness.py'),'--library',str(lib)]
for flag,paths in inputs.items():
    for name in paths:
        path=(lib/name).resolve();assert path.is_relative_to(lib) and path.is_file()
        command.extend([flag,name])
preflight=out/'combined-preflight-01'
if not a.apply:
    preflight.mkdir();before=state();result=subprocess.run(command+['--dry-run'],capture_output=True,text=True)
    (preflight/'stdout.log').write_text(result.stdout);(preflight/'stderr.log').write_text(result.stderr)
    assert result.returncode==0,result.stderr[-5000:]
    d=json.loads(result.stdout)
    assert (d['portable_ready_entries'],d['unique_mangled_methods'],d['compiled_declaration_pending_entries'])==(639,343,440),d
    assert not d['stale_previous_entries'] and not d['demoted_entries'] and not d['promoted_pending_entries']
    assert before==state()
    proof=dict(passed=True,result=d,unchanged_state=before,command=command,inputs={n:sha(lib/n) for paths in inputs.values() for n in paths},tool_sha256=sha(Path(__file__)),historical_manager_demotion_manifest_deliberately_not_applied=True)
    (preflight/'validation.json').write_text(json.dumps(proof,indent=2)+'\n')
    print(json.dumps(dict(preflight_passed=True,ready=639,names=343,pending=440,no_stale_or_demotion=True)));raise SystemExit(0)
proof=read(preflight/'validation.json')
assert proof['passed'] and proof['tool_sha256']==sha(Path(__file__)) and proof['unchanged_state']==state() and proof['command']==command
for name,digest in proof['inputs'].items():assert sha(lib/name)==digest,name
oldready=read(lib/'validation/ready-functions.json')['functions'];oldpending=read(lib/'validation/compiled-functions.json')['functions']
assert (len(oldready),len(oldpending))==(637,422)
admission=out/'admission-01';admission.mkdir();result=subprocess.run(command,capture_output=True,text=True)
(admission/'stdout.log').write_text(result.stdout);(admission/'stderr.log').write_text(result.stderr)
assert result.returncode==0,result.stderr[-5000:]
ready=read(lib/'validation/ready-functions.json')['functions'];pending=read(lib/'validation/compiled-functions.json')['functions']
assert (len(ready),len({r['mangled'] for r in ready}),len(pending))==(639,343,440)
assert keys(oldready)<=keys(ready) and keys(oldpending)<=keys(pending) and not keys(ready)&keys(pending)
added_ready=keys(ready)-keys(oldready);added_pending=keys(pending)-keys(oldpending)
assert {name for _,name in added_ready}=={'_ZN8Presonus4DICE13SysexReceiverC1Ev','_ZN8Presonus4DICE13SysexReceiverC2Ev'}
assert len(added_ready)==2 and len(added_pending)==18 and len({name for _,name in added_pending})==12
report=dict(passed=True,ready=639,ready_unique_names=343,pending=440,new_ready=2,new_pending_records=18,new_pending_unique_names=12,no_silent_removals=True,demotions=0,preflight_sha256=sha(preflight/'validation.json'),tool_sha256=sha(Path(__file__)))
(admission/'validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
