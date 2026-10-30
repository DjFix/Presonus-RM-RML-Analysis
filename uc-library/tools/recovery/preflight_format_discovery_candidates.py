"""Read-only unchanged merger preflight for the two frozen candidate packets."""
from pathlib import Path
import hashlib,json,subprocess,sys
repo=Path.cwd().resolve();lib=repo/'uc-library';out=repo/'evidence/recovery/2026-10-28/formatter-discovery-batch/candidate-preflight-01';out.mkdir()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
paths=[lib/'validation'/n for n in ('ready-functions.json','compiled-functions.json','formatting.json','integration.json')]
paths += [p for p in (lib/'validation/history').rglob('*') if p.is_file()]
state=lambda:{str(p.relative_to(lib)):sha(p) for p in paths}
before=state()
fragments=['candidates/dsp-value-formatters/validation/candidate-seal-02/pending.fragment.json','candidates/uc-network-discovery-services/validation/seal-01/pending-fragment.json']
cmd=[sys.executable,str(lib/'tools/merge_readiness.py'),'--library',str(lib)]
for name in fragments:cmd+=['--pending',name]
cmd+=['--dry-run'];r=subprocess.run(cmd,capture_output=True,text=True,cwd=repo)
(out/'stdout.log').write_text(r.stdout);(out/'stderr.log').write_text(r.stderr)
assert r.returncode==0,r.stderr[-5000:]
d=json.loads(r.stdout)
assert (d['portable_ready_entries'],d['unique_mangled_methods'],d['compiled_declaration_pending_entries'])==(639,343,580),d
assert not any(d[n] for n in ('stale_previous_entries','demoted_entries','promoted_pending_entries'))
assert before==state()
proof=dict(passed=True,result=d,command=cmd,unchanged_state=before,inputs={n:sha(lib/n) for n in fragments},tool_sha256=sha(Path(__file__)))
(out/'validation.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(dict(passed=True,ready=639,pending=580)))
