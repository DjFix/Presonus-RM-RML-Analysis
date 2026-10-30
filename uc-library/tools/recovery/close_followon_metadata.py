"""Record completed follow-on batch without changing admitted C++ proofs."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
repo=Path.cwd().resolve();lib=repo/'uc-library';out=repo/'evidence/recovery/2026-10-28/followon-batch'
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
counts=read(out/'unique-current.json');assert counts['manual_buckets']['no_current_admitted_compiled_reconstruction']==7027
assert read(out/'admission-01/validation.json')['passed']
role=read(out/'role-audit.log');assert role['passed'] and role['units']==120
assert sha(lib/role['proof'])==role['sha256']
raw=out/'raw-active-01/validation.json';assert read(raw)['passed']
tracker=lib/'validation/embedded-efm/SYMBOLS.md';marker='## Follow-on archive refresh — 2026-10-28 UTC'
assert marker not in tracker.read_text()
with tracker.open('a') as stream:
    stream.write(f'\n{marker}\n\nEight retained suites passed115,933cases including88independentguards.\nProof `evidence/recovery/2026-10-28/followon-batch/raw-active-01/validation.json`,\nSHA-256 `{sha(raw)}`. Raw source/domain unchanged.\nLinux142/142CTest;120production CPPs compiled once;90public application headers.\n')
note=out/'COMPLETED.md';assert not note.exists()
note.write_text('''# Follow-on batch admitted

- NetworkManager setPortNumber, setNetworkPriority and isSendingFromExternalConnection:3shared names/6new per-ELF pending identities.3992new+8268retained cases eachRelease/San and actualproduction replay. Adapter fields are independent stored values; no downstream discovery claim. Actual unstarted CCLThread priority/readback only; no running scheduler change.
- Dice3Programmer performTransaction(mp25Transaction),writeEnable,busyWait,readJedecId:4client names/4new pending identities.4352new+14160retained cases eachRelease/San; actualproduction/provider replay. Nested by-value aggregate identity preserved, native pointer/count fields independent; no original aggregate layout/ARMABI claim. Real CCL nanosecond clock/sleep/Buffer and LinuxSPI translation tested with ioctl intercepted. RXcapacity must cover command-inclusive txLength+rxLength; initialized TXprefix equivalence only, inactive TXtail/padding deliberately zeroed. No device operation executed.
- Canonical639ready records/343unique ready names;450pending records/262unique pending names. No demotions, promotions or prior identity removals. Seven additional original names implemented. Non-Core names without admitted implementation7027; Core source-route2541;9830names remain to readiness.
- Linux142/142CTest, formatter23.1.3,120production CPPs compiled once(80common/30CS18/10RM),90public headers. All installed/relocated role consumers pass.1096source/proofhash checks pass.115933raw MCU cases separate fromhost counts.
- Combined unchanged merger preflight/admission at combined-preflight-01/validation.json and admission-01/validation.json. Managed candidate evidence remains in sibling dice-programmer-transactions and uc-network-configuration trees.
- Retained failures: programmer fixture metadata lookup and missing legacy original_address field; Network nonexistent corethread.cpp metadata path. No failed proof overwritten; no code behavior relaxed to bypass a failed test.
- DWARF survey found only26runtime compiler/glibc compilation units and zero pending application linkage matches per ELF. It does not resolve original application returns.
- Canonical tracker uc-library/SYMBOLS.md; generated checkpoint temp/recovery-work/checkpoints/2026-10-28-followon.md.
- Next authorized candidates: dice-programmer-pages and uc-network-handler-queries. No pause; no hardware/LAN/flash/erase tests, Mac sync, commit or push.
''')
events=out/'queue-events.jsonl'
with events.open('a') as stream:
    for event,path in [('batch-admitted',out/'admission-01/validation.json'),('role-audit-finished',lib/role['proof'])]:
        stream.write(json.dumps(dict(event=event,artifact=str(path.relative_to(repo)),artifact_sha256=sha(path),artifact_write_time=datetime.fromtimestamp(path.stat().st_mtime,timezone.utc).isoformat(),recorded_at=datetime.now(timezone.utc).isoformat()))+'\n')
nextfile=repo/'temp/recovery-work/NEXT.md';(out/'next-before-close.md').write_bytes(nextfile.read_bytes())
nextfile.write_text('Follow-on batch admitted; no pause. Read evidence/recovery/2026-10-28/followon-batch/COMPLETED.md and followon checkpoint. Next candidates: dice-programmer-pages and uc-network-handler-queries; root owns integration.\n')
print(json.dumps(dict(batch_complete=True,ready=639,pending=450,remaining_unique=9830,uncompiled_non_core=7027,continuing=True)))
