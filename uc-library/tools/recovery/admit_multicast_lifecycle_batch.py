"""Fixed disjoint hierarchy/lifecycle guards around the unchanged merger."""
from pathlib import Path
import argparse,hashlib,json,subprocess,sys
p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');a=p.parse_args()
repo=Path.cwd().resolve();lib=repo/'uc-library';out=repo/'evidence/recovery/2026-10-28/multicast-lifecycle-batch'
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
keys=lambda rows:{(r['original_elf_sha256'],r['mangled']) for r in rows}
fmt='candidates/dsp-formatter-option-lifecycle/validation/active-01/'
mc='candidates/uc-network-multicast-sockets/validation/active-seal-01/'
spi='validation/noaa-spi-service-multicast-lifecycle/root-closure-01/'
assert read(lib/fmt/'ready-validation.json')['passed']
assert read(lib/mc/'pending-validation.json')['passed'] and read(lib/mc/'pending-validation.json')['active_source_replay_passed']
assert read(out/'raw-active-01/validation.json')['passed'] and read(out/'raw-active-01/validation.json')['canonical_ctest_count']==165
assert read(out/'public-headers.log')['headers']==103 and read(out/'public-headers.log')['returncode']==0
assert read(out/'role-audit.log')['passed'] and read(out/'role-audit.log')['units']==144
assert read(lib/'validation/integration.json')['test_suites']==165
inputs={'--fragment':[fmt+'ready.fragment.json',spi+'ready-functions.fragment.json'],'--pending':[fmt+'pending.fragment.json',mc+'pending-fragment.json',spi+'pending-functions.fragment.json']}
incoming={flag:[r for name in paths for r in read(lib/name)['functions']] for flag,paths in inputs.items()}
assert (len(incoming['--fragment']),len(incoming['--pending']))==(38,46)
assert all(len(rows)==len(keys(rows)) for rows in incoming.values()),'duplicate fragment ownership'
assert not keys(incoming['--fragment'])&keys(incoming['--pending'])
def state():
    paths=[lib/'validation'/n for n in ('ready-functions.json','compiled-functions.json','formatting.json','integration.json')]
    paths += [p for p in (lib/'validation/history').rglob('*') if p.is_file()]
    return {str(p.relative_to(lib)):sha(p) for p in paths}
command=[sys.executable,str(lib/'tools/merge_readiness.py'),'--library',str(lib)]
for flag,paths in inputs.items():
    for name in paths:command.extend([flag,name])
pre=out/'combined-preflight-01'
if not a.apply:
    pre.mkdir();before=state();r=subprocess.run(command+['--dry-run'],capture_output=True,text=True,cwd=repo)
    (pre/'stdout.log').write_text(r.stdout);(pre/'stderr.log').write_text(r.stderr);assert r.returncode==0,r.stderr[-5000:]
    d=json.loads(r.stdout);assert (d['portable_ready_entries'],d['unique_mangled_methods'],d['compiled_declaration_pending_entries'])==(675,363,622),d
    assert not any(d[n] for n in ('stale_previous_entries','demoted_entries','promoted_pending_entries'))
    assert state()==before
    proof=dict(passed=True,result=d,unchanged_state=before,command=command,inputs={n:sha(lib/n) for paths in inputs.values() for n in paths},tool_sha256=sha(Path(__file__)))
    (pre/'validation.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(dict(preflight_passed=True,ready=675,names=363,pending=622)));raise SystemExit(0)
proof=read(pre/'validation.json');assert proof['passed'] and proof['tool_sha256']==sha(Path(__file__)) and proof['command']==command and proof['unchanged_state']==state()
for name,digest in proof['inputs'].items():assert sha(lib/name)==digest,name
oldready=read(lib/'validation/ready-functions.json')['functions'];oldpending=read(lib/'validation/compiled-functions.json')['functions'];assert (len(oldready),len(oldpending))==(659,606)
admit=out/'admission-01';admit.mkdir();r=subprocess.run(command,capture_output=True,text=True,cwd=repo)
(admit/'stdout.log').write_text(r.stdout);(admit/'stderr.log').write_text(r.stderr);assert r.returncode==0,r.stderr[-5000:]
ready=read(lib/'validation/ready-functions.json')['functions'];pending=read(lib/'validation/compiled-functions.json')['functions']
assert (len(ready),len({r['mangled'] for r in ready}),len(pending))==(675,363,622)
assert keys(oldready)<=keys(ready) and keys(oldpending)<=keys(pending) and not keys(ready)&keys(pending)
added_ready=keys(ready)-keys(oldready);added_pending=keys(pending)-keys(oldpending)
assert len(added_ready)==16 and len({n for _,n in added_ready})==8
assert len(added_pending)==16 and len({n for _,n in added_pending})==8
report=dict(passed=True,ready=675,ready_unique_names=363,pending=622,new_ready_records=16,new_ready_unique_names=8,new_pending_records=16,new_pending_unique_names=8,no_silent_removals=True,demotions=0,preflight_sha256=sha(pre/'validation.json'),tool_sha256=sha(Path(__file__)))
(admit/'validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
