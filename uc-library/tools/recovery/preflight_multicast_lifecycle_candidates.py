"""Read-only candidate preflight using unchanged readiness merger."""
from pathlib import Path
import hashlib,json,subprocess,sys
repo=Path.cwd().resolve();lib=repo/'uc-library';out=repo/'evidence/recovery/2026-10-28/multicast-lifecycle-batch/candidate-preflight-01';out.mkdir()
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
paths=[lib/'validation'/n for n in ('ready-functions.json','compiled-functions.json','formatting.json','integration.json')]
paths += [p for p in (lib/'validation/history').rglob('*') if p.is_file()]
state=lambda:{str(p.relative_to(lib)):sha(p) for p in paths}
before=state();base='candidates/dsp-formatter-option-lifecycle/validation/candidate-seal-01/'
inputs={'--fragment':[base+'ready.fragment.json'],'--pending':[base+'pending.fragment.json','candidates/uc-network-multicast-sockets/validation/seal-01/pending-fragment.json']}
cmd=[sys.executable,str(lib/'tools/merge_readiness.py'),'--library',str(lib)]
for flag,names in inputs.items():
    for name in names:cmd.extend([flag,name])
r=subprocess.run(cmd+['--dry-run'],capture_output=True,text=True,cwd=repo)
(out/'stdout.log').write_text(r.stdout);(out/'stderr.log').write_text(r.stderr);assert r.returncode==0,r.stderr[-5000:]
d=json.loads(r.stdout);assert (d['portable_ready_entries'],d['unique_mangled_methods'],d['compiled_declaration_pending_entries'])==(675,363,622),d
assert not any(d[n] for n in ('stale_previous_entries','demoted_entries','promoted_pending_entries')) and state()==before
(out/'validation.json').write_text(json.dumps(dict(passed=True,result=d,command=cmd,unchanged_state=before,inputs={n:sha(lib/n) for names in inputs.values() for n in names},tool_sha256=sha(Path(__file__))),indent=2)+'\n')
print(json.dumps(dict(passed=True,ready=675,names=363,pending=622)))
