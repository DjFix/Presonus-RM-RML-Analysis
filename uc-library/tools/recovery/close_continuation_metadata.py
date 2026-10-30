"""Preserve admitted batch completion, timings and retained MCU tracker entry."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib,json

repo=Path.cwd().resolve();lib=repo/'uc-library';out=repo/'evidence/recovery/2026-10-28/continuation-batch'
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
counts=read(out/'unique-current.json');assert counts['remaining_unique']==9830
admission=out/'admission-01/validation.json';assert read(admission)['passed']
role=read(out/'role-audit.log');assert role['passed'] and role['units']==117
roleproof=lib/role['proof'];assert sha(roleproof)==role['sha256']
raw=out/'raw-active-01/validation.json';assert read(raw)['passed']
tracker=lib/'validation/embedded-efm/SYMBOLS.md';marker='## Continuation archive refresh — 2026-10-28 UTC'
assert marker not in tracker.read_text()
with tracker.open('a') as stream:
    stream.write(f'\n{marker}\n\nEight retained suites passed: 115,933 cases with 88 independent guards.\nProof: `evidence/recovery/2026-10-28/continuation-batch/raw-active-01/validation.json`\nSHA-256 `{sha(raw)}`. Raw source/domain unchanged.\nLinux CTest139/139;117 production CPPs compiled once;89 public application headers.\nRead-only raw evidence hash audit passed209files.\n')
note=out/'COMPLETED.md';assert not note.exists()
note.write_text('''# Continuation batch admitted

- All five remaining BiquadCalc methods implemented in original DSP scopes. Complete ELF inventory: nine ordinary names and one C1; original C2/float constructor/Option=true symbols absent. Ordinary original return declarations remain pending.
- Source-pinned Sun fdlibm sine adaptation fixes the observed 8kHz discrepancy; original notices retained, existing expf provider unchanged. 3,147 expanded incremental cases,532 retained cases,180 direct flush edges and3 constructor cases passed in Release, sanitizers and actual production replay. Finite corpus only, no universal math/ARM ABI claim.
- DICE receiver C1/C2 and post added;5120cases. Original constructors distinct44byte ranges; native aliases recorded. post virtual declaration corrected from existing vtable evidence before admission, actual indirect dispatch checked. Portable two-slot receiver remains different from original abstract three-slot hierarchy; full hierarchy/layout/ABI excluded.
- Network six shared listener/registrar methods added;2640new+5628retained cases per native mode and actual production replay. Borrowed state, partial callback interface and required discovery-provider boundary explicit; startup/discovery implementation/OOM/mutation/concurrency unverified.
- Canonical ledger639ready records/343unique names;440pending records/255unique names. Delta:2ready constructor variants and18pending records representing12ordinary names. No demotions or old identity removals.
- Remaining readiness9830names:7034non-Core without admitted implementation,255declaration-pending,2541Core source-route.14new original names acquired implementations; constructor variants are not independent algorithm throughput.
- Linux139/139tests;formatter23.1.3;89public headers;117production CPPs compiled once(79common/28CS18/10RM). All relocated installed-role consumers pass.1056source/proofhash checks pass.115933raw MCU cases remain separate.
- First integration link failure, DICE missing snapshot key/lifecycle metadata TypeError, virtual-declaration correction and Biquad math/mode-order failures retained with their attempts. No failed run overwritten.
- Combined unchanged merger preflight and actual admission: combined-preflight-01/validation.json and admission-01/validation.json. Historical manager demotion proposal deliberately not reapplied.
- Canonical tracker: uc-library/SYMBOLS.md. Generated checkpoint: temp/recovery-work/checkpoints/2026-10-28-continuation.md.
- Next work authorized: uc-network-configuration and dice-programmer-transactions candidates. Existing proofs/sources frozen. No hardware, LAN, device-update/erase/flash, Mac synchronization, commit or push.
''')
with (out/'queue-events.jsonl').open('a') as stream:
    for event,path in [('batch-admitted',admission),('role-audit-finished',roleproof)]:
        stream.write(json.dumps(dict(event=event,artifact=str(path.relative_to(repo)),artifact_sha256=sha(path),artifact_write_time=datetime.fromtimestamp(path.stat().st_mtime,timezone.utc).isoformat(),recorded_at=datetime.now(timezone.utc).isoformat()))+'\n')
nextfile=repo/'temp/recovery-work/NEXT.md'
(out/'next-before-close.md').write_bytes(nextfile.read_bytes())
nextfile.write_text('Continuation batch admitted; no pause. Read evidence/recovery/2026-10-28/continuation-batch/COMPLETED.md and generated continuation checkpoint. Next candidates: uc-network-configuration and dice-programmer-transactions; root owns integration.\n')
print(json.dumps(dict(batch_complete=True,ready=639,pending=440,remaining_unique=9830,continuing=True)))
