"""Preserve admitted page/query batch evidence and terminal job handles."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
repo=Path.cwd().resolve();lib=repo/'uc-library';out=repo/'evidence/recovery/2026-10-28/queries-batch'
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
counts=read(out/'unique-current.json');assert counts['manual_buckets']['no_current_admitted_compiled_reconstruction']==7017
assert read(out/'admission-01/validation.json')['passed']
role=read(out/'role-audit.log');assert role['passed'] and role['units']==122 and sha(lib/role['proof'])==role['sha256']
raw=out/'raw-active-01/validation.json';assert read(raw)['passed']
tracker=lib/'validation/embedded-efm/SYMBOLS.md';marker='## Page/query archive refresh — 2026-10-28 UTC'
assert marker not in tracker.read_text()
with tracker.open('a') as stream:
    stream.write(f'\n{marker}\n\nEight retained suites passed115,933cases including88independentguards.\nProof `evidence/recovery/2026-10-28/queries-batch/raw-active-01/validation.json`,\nSHA-256 `{sha(raw)}`. Raw source/domain unchanged.\nLinux145/145CTest;122production CPPs compiled once;91public application headers.\n')
note=out/'COMPLETED.md';assert not note.exists()
note.write_text('''# Page/query batch admitted

- ConnectionHandler six query methods plus NetworkManager hasOutgoingEvents:7shared original names/14new per-ELF pending records.3296new+12260retained rows per native mode. Exact19-member provider closure, actual production replay and BasicConnection original28byte helper witness checked. Required initialized sidecar domain: eachqueried identity has one live view; common/outgoing pointers and sender bounds valid; multicastOutgoing live when fallback queried; manager handler live. No original Connection inheritance/layout/ownership claim; pointer and ordinary return declarations unresolved.
- Dice3Programmer dumpPage,verifyPage,writePage:3client names/3new pending records.1904new+4352transactions+14160lifecycle perRelease/San. RealCCLbuffer/clock plus6intercepted LinuxSPI translations; no physicaldevice operation. Shared260byte TX/RX source helper preserves old/new aliasing. Signedpage checks,negativecounts,24bitwrap,padding/errors verified. verifyPage length>256 deliberate rejection is outside original equivalence domain; original uncheckedreads unresolved. RXcapacity command-inclusiveTOTAL documented in public API.
- Canonical639ready records/343unique ready names;467pending records/272unique pending names. No demotions/promotions or prior identity removals. Ten new original names implemented. Since resume31names added;7017non-Core names lack admitted implementation;2541Core source-route;9830names remain to readiness.
- Linux145/145CTest;formatter23.1.3;122production CPPs compiled once(81common/31CS18/10RM);91public headers. Installed-role/relocated consumers pass;1141source/proofhash checks pass.115933raw MCU cases remain separate.
- Combined unchanged merger preflight/admission: combined-preflight-01/validation.json and admission-01/validation.json. Candidate/active logs, fixtures, source/runtime hashes retained in respective managed trees. Both active proof producers passed first attempt; initialized-precondition seal02 strengthens domain without changing C++ behavior.
- Canonical tracker uc-library/SYMBOLS.md; generated checkpoint temp/recovery-work/checkpoints/2026-10-28-queries.md.
- Next authorized candidates: uc-network-registrar-services and offline programmer open/close. No pause. PhysicalGPIO/SPI/flash/erase/update testing deferred; no Mac sync,commit or push.
''')
with (out/'queue-events.jsonl').open('a') as stream:
    for event,path in [('batch-admitted',out/'admission-01/validation.json'),('role-audit-finished',lib/role['proof'])]:
        stream.write(json.dumps(dict(event=event,artifact=str(path.relative_to(repo)),artifact_sha256=sha(path),artifact_write_time=datetime.fromtimestamp(path.stat().st_mtime,timezone.utc).isoformat(),recorded_at=datetime.now(timezone.utc).isoformat()))+'\n')
jobs=repo/'temp/recovery-work/active-jobs.json';(out/'active-jobs-before-close.json').write_bytes(jobs.read_bytes())
state=read(jobs)
for job in state['jobs'].values():job.update(status='terminal',exit_code=0)
state.update(phase_state='admitted',canonical_after_admission=dict(ready=639,ready_names=343,pending=467),next_candidates=['uc-network-registrar-services','programmer open/close'])
jobs.write_text(json.dumps(state,indent=2)+'\n')
nextfile=repo/'temp/recovery-work/NEXT.md';(out/'next-before-close.md').write_bytes(nextfile.read_bytes())
nextfile.write_text('Page/query batch admitted; no pause. Read evidence/recovery/2026-10-28/queries-batch/COMPLETED.md and queries checkpoint. All recorded jobs terminal. Next: registrar services and offline programmer open/close; root owns integration.\n')
print(json.dumps(dict(batch_complete=True,ready=639,pending=467,remaining_unique=9830,uncompiled_non_core=7017,continuing=True)))
