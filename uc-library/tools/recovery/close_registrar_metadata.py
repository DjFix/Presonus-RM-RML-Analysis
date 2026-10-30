"""Record completed registrar batch; preserve all prior source/proof identities."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
repo=Path.cwd().resolve();lib=repo/'uc-library';out=repo/'evidence/recovery/2026-10-28/registrar-batch'
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
counts=read(out/'unique-current.json');assert counts['manual_buckets']['no_current_admitted_compiled_reconstruction']==7008
assert read(out/'admission-01/validation.json')['passed']
role=read(out/'role-audit.log');assert role['passed'] and role['units']==123 and sha(lib/role['proof'])==role['sha256']
raw=out/'raw-active-01/validation.json';assert read(raw)['passed']
tracker=lib/'validation/embedded-efm/SYMBOLS.md';marker='## Registrar archive refresh — 2026-10-28 UTC'
assert marker not in tracker.read_text()
with tracker.open('a') as stream:
    stream.write(f'\n{marker}\n\nEight retained suites passed 115,933 cases, including 88 independent guards.\nProof: `evidence/recovery/2026-10-28/registrar-batch/raw-active-01/validation.json`.\nSHA-256: `{sha(raw)}`. Raw source and domain unchanged.\nLinux CTest: 146/146; 123 production CPPs compiled once; 91 public headers.\n')
note=out/'COMPLETED.md';assert not note.exists()
note.write_text('''# Registrar batch admitted

Nine shared ServerRegistrar methods now have implementations in their original namespace: four find overloads, hasLocalServers, three notifications and serverRegistered. The batch adds 18 per-ELF declaration-pending identities and refreshes 50 existing Network records. All ordinary return declarations remain unresolved.

The original three-slot pure listener interface is preserved. Two unused overrides in the retained test fixture abort explicitly; production callbacks have no default success implementation. Server/LocalServer identities, endpoint fields and descriptor composition are independent borrowed source-port views. Null endpoint address means an empty string, not a wildcard. Initialized view, pointer, string and listener lifetimes are required; mutation, concurrency, ownership, complete hierarchy and ARM ABI remain unverified.

Validation passed 3,058 new and 15,556 retained cases in Release and ASan/UBSan, plus actual production replay and the exact linked provider closure. The first candidate build's retained-fixture include-path failure is preserved. No device or LAN operation occurred.

Canonical totals: 639 ready records / 343 unique ready names; 485 declaration-pending records / 281 unique names. No demotions, promotions or prior identity removals. Since resume, 40 additional original names have implementations. There are 7,008 non-Core names without an admitted implementation, 2,541 Core source-route names and 9,830 names remaining to readiness.

Linux CTest passed 146/146. Formatter 23.1.3 passed. All 123 production CPPs compiled once (82 common / 31 CS18 / 10 RM); 91 public headers and relocated installed-role consumers passed. The source/proof audit checked 1,151 hashes. The 115,933 retained raw MCU cases remain separate from host symbol counts.

The unchanged combined merger preflight and admission are in combined-preflight-01/validation.json and admission-01/validation.json. Canonical tracker: uc-library/SYMBOLS.md. Generated checkpoint: temp/recovery-work/checkpoints/2026-10-28-registrar.md.

Work continues with offline DICE open/close, two EQ-type conversions and the next Network selection. Original Panel constructor/destructor source remains unresolved; use of its setup/set bodies through an independent lifetime adapter does not promote those symbols. No pause, hardware test, Mac synchronization, commit or push.
''')
with (out/'queue-events.jsonl').open('a') as stream:
    for event,path in [('batch-admitted',out/'admission-01/validation.json'),('role-audit-finished',lib/role['proof'])]:
        stream.write(json.dumps(dict(event=event,artifact=str(path.relative_to(repo)),artifact_sha256=sha(path),artifact_write_time=datetime.fromtimestamp(path.stat().st_mtime,timezone.utc).isoformat(),recorded_at=datetime.now(timezone.utc).isoformat()))+'\n')
nextfile=repo/'temp/recovery-work/NEXT.md';(out/'next-before-close.md').write_bytes(nextfile.read_bytes())
nextfile.write_text('Registrar batch admitted; no pause. Read registrar COMPLETED.md and checkpoint. Next candidates: dice-programmer-open-close, dsp-eq-type-conversions, next Network selection. Root owns integration.\n')
print(json.dumps(dict(batch_complete=True,ready=639,pending=485,remaining_unique=9830,uncompiled_non_core=7008,continuing=True)))
