"""Preserve the completed device/four-EQ batch checkpoint and evidence."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
repo=Path.cwd().resolve();lib=repo/'uc-library';out=repo/'evidence/recovery/2026-10-28/device-eq-batch'
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
counts=read(out/'unique-current.json');assert counts['manual_buckets']['no_current_admitted_compiled_reconstruction']==7002
assert read(out/'admission-01/validation.json')['passed']
role=read(out/'role-audit.log');assert role['passed'] and role['units']==126 and sha(lib/role['proof'])==role['sha256']
raw=out/'raw-active-01/validation.json';assert read(raw)['passed']
tracker=lib/'validation/embedded-efm/SYMBOLS.md';marker='## Device/EQ archive refresh — 2026-10-28 UTC'
assert marker not in tracker.read_text()
with tracker.open('a') as stream:
    stream.write(f'\n{marker}\n\nEight retained suites passed 115,933 cases, including 88 independent guards.\nProof: `evidence/recovery/2026-10-28/device-eq-batch/raw-active-01/validation.json`.\nSHA-256: `{sha(raw)}`. Raw source and domain unchanged.\nLinux CTest: 149/149; 126 production CPPs compiled once; 92 public headers.\n')
note=out/'COMPLETED.md';assert not note.exists()
note.write_text('''# Device and EQ batch admitted

Dice3Programmer open/close now use explicit required device services with a real Linux provider and existing Presonus::Panel::OutputPin setup/set bodies. Independent RAII adapts pin lifetimes; original Panel constructor/destructor bodies remain uncompiled. All physical effects were intercepted. Tests preserve early-mode-ioctl descriptor leakage, close not resetting the descriptor, GPIO cleanup order and JEDEC decisions. The fortified __open_2 instrumentation failure is retained; native and root bridges now wrap open, __open_2, close and ioctl.

Four RM-only EQ conversions retain original Presonus::Dsp scopes, const/virtual membership and the proven EQ8-to-EQController relationship. Tagged independent construction avoids invented original constructors. The missing Controller base, complete original vtable/layout/lifecycle, enum category/underlying type and return declarations remain unresolved. Signed upper inverse indices return the observed value 6; negative unchecked indices are outside the supported domain. The prior two-method packet is preserved under before-inverse evidence.

Device validation passed 1,280 new cases plus 1,904 page, 4,352 transaction and 14,160 lifecycle cases in Release/San and actual production replay. Fifteen programmer and four GPIO dependency ranges were checked. EQ passed 8,943 new and 56,714 retained cases per mode and in production, with fourteen function and six data/RTTI ranges verified. Both actual active producers passed first attempt.

The guarded application completed before an append-only helper found missing new-batch path lists. The failed producer version, applied hashes and metadata-only repair are retained in path-list-initialization-fix.json. Sources were not reapplied or relaxed.

Canonical totals are 639 ready records / 343 unique ready names and 491 pending records / 287 unique pending names. No promotions, demotions or prior identity removals. Six names were added in this batch; 46 since resume. There are 7,002 non-Core names without an admitted implementation, 2,541 Core source-route names and 9,830 names remaining to readiness.

Linux passed 149/149 CTest, formatter 23.1.3, all 126 production CPPs compiled once (82 common / 33 CS18 / 11 RM), 92 public headers and all installed-role consumers. The source/proof audit checked 1,199 hashes. Retained raw MCU coverage remains 115,933 cases, separately counted.

The unchanged combined merger preflight/admission is recorded in combined-preflight-01/validation.json and admission-01/validation.json. Canonical tracker: uc-library/SYMBOLS.md. Generated checkpoint: temp/recovery-work/checkpoints/2026-10-28-device-eq.md.

Work continues with server metadata, offline programmer update helpers and the next mixer/surface selection. No pause, physical device programming, Mac synchronization, commit or push.
''')
with (out/'queue-events.jsonl').open('a') as stream:
    for event,path in [('batch-admitted',out/'admission-01/validation.json'),('role-audit-finished',lib/role['proof'])]:
        stream.write(json.dumps(dict(event=event,artifact=str(path.relative_to(repo)),artifact_sha256=sha(path),artifact_write_time=datetime.fromtimestamp(path.stat().st_mtime,timezone.utc).isoformat(),recorded_at=datetime.now(timezone.utc).isoformat()))+'\n')
nextfile=repo/'temp/recovery-work/NEXT.md';(out/'next-before-close.md').write_bytes(nextfile.read_bytes())
nextfile.write_text('Device/four-EQ batch admitted; no pause. Read device-eq COMPLETED.md and checkpoint. Next: server metadata, offline programmer update, next mixer/surface selection. Root owns integration.\n')
print(json.dumps(dict(batch_complete=True,ready=639,pending=491,remaining_unique=9830,uncompiled_non_core=7002,continuing=True)))
