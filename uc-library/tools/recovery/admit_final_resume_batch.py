"""One fixed combined admission; the existing merger owns all classification rules."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--network-pending',required=True);p.add_argument('--apply',action='store_true');a=p.parse_args()
repo=Path.cwd().resolve();lib=repo/'uc-library';out=repo/'evidence/recovery/2026-10-28/final-resume-batch'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();read=lambda p:json.loads(p.read_text())
keys=lambda rows:{(r['original_elf_sha256'],r['mangled']) for r in rows}
state=lambda:{str(p.relative_to(lib)):sha(p) for p in [lib/'validation/ready-functions.json',lib/'validation/compiled-functions.json',*sorted((lib/'validation/history').rglob('*'))] if p.is_file()}
network=(lib/a.network_pending).resolve();assert network.is_relative_to(lib)
network_audit=read(network.parent/'ACTIVE-AUDIT.json')
assert network_audit['passed'] and network_audit['source_compilation_and_production_replay_passed']
dice='candidates/dice-next-services/validation/active-01/'
biquad='candidates/dsp-biquad-methods/validation/active-01/'
spi='validation/noaa-spi-service-final-resume/root-closure-01/'
assert read(lib/dice/'audit.json')['active_source_replay_passed']
assert read(lib/biquad/'audit.json')['actual_production_source_gate_passed']
raw=read(out/'raw-active-01/validation.json');assert raw['passed'] and raw['canonical_ctest_count']==136
headers=read(out/'public-headers.log');assert headers['headers']==88 and headers['returncode']==0
inputs={'--fragment':[biquad+'constructor-ready.fragment.json',spi+'ready-functions.fragment.json'],'--pending':[dice+'pending.fragment.json',a.network_pending,biquad+'pending.fragment.json',spi+'pending-functions.fragment.json'],'--demote':[dice+'demote.json']}
demotions=read(lib/dice/'demote.json')['demotions'];assert len(demotions)==2
demoted=keys(demotions)
command=[sys.executable,str(lib/'tools/merge_readiness.py'),'--library',str(lib)]
for flag,paths in inputs.items():
 for name in paths:command.extend([flag,name])
preflight=out/'combined-preflight-01'
if not a.apply:
 preflight.mkdir();before=state();r=subprocess.run(command+['--dry-run'],capture_output=True,text=True)
 (preflight/'stdout.log').write_text(r.stdout);(preflight/'stderr.log').write_text(r.stderr)
 assert r.returncode==0,r.stderr
 d=json.loads(r.stdout);assert (d['portable_ready_entries'],d['unique_mangled_methods'],d['compiled_declaration_pending_entries'])==(637,341,422)
 assert not d['stale_previous_entries'] and not d['promoted_pending_entries'] and len(d['demoted_entries'])==2
 assert before==state()
 proof=dict(passed=True,result=d,unchanged_state=before,command=command,inputs={n:sha(lib/n) for paths in inputs.values() for n in paths},tool_sha256=sha(Path(__file__)))
 (preflight/'validation.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(dict(preflight_passed=True,ready=637,names=341,pending=422,demotions=2)));raise SystemExit(0)
proof=read(preflight/'validation.json');assert proof['passed'] and proof['tool_sha256']==sha(Path(__file__)) and proof['unchanged_state']==state() and proof['command']==command
for n,h in proof['inputs'].items():assert sha(lib/n)==h,n
oldready=read(lib/'validation/ready-functions.json')['functions'];oldpending=read(lib/'validation/compiled-functions.json')['functions']
assert (len(oldready),len(oldpending))==(639,403)
admission=out/'admission-01';admission.mkdir();r=subprocess.run(command,capture_output=True,text=True)
(admission/'stdout.log').write_text(r.stdout);(admission/'stderr.log').write_text(r.stderr);assert r.returncode==0,r.stderr
ready=read(lib/'validation/ready-functions.json')['functions'];pending=read(lib/'validation/compiled-functions.json')['functions']
assert (len(ready),len({r['mangled'] for r in ready}),len(pending))==(637,341,422)
assert keys(ready)==keys(oldready)-demoted and keys(oldpending)<=keys(pending) and demoted<=keys(pending) and not keys(ready)&keys(pending)
result=dict(passed=True,ready=637,names=341,pending=422,explicit_demotions=2,no_silent_removals=True,preflight_sha256=sha(preflight/'validation.json'),tool_sha256=sha(Path(__file__)))
(admission/'validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
