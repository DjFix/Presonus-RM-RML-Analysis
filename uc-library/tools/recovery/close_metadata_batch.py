"""Preserve completed server-metadata recovery evidence and counts."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
repo=Path.cwd().resolve();lib=repo/'uc-library';out=repo/'evidence/recovery/2026-10-28/metadata-batch'
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
counts=read(out/'unique-current.json');assert counts['manual_buckets']['no_current_admitted_compiled_reconstruction']==6994
assert read(out/'admission-01/validation.json')['passed']
role=read(out/'role-audit.log');assert role['passed'] and role['units']==127 and sha(lib/role['proof'])==role['sha256']
raw=out/'raw-active-01/validation.json';assert read(raw)['passed']
tracker=lib/'validation/embedded-efm/SYMBOLS.md';marker='## Server metadata archive refresh — 2026-10-28 UTC'
assert marker not in tracker.read_text()
with tracker.open('a') as stream:
    stream.write(f'\n{marker}\n\nEight retained suites passed 115,933 cases, including 88 independent guards.\nProof: `evidence/recovery/2026-10-28/metadata-batch/raw-active-01/validation.json`.\nSHA-256: `{sha(raw)}`. Raw source and domain unchanged.\nLinux CTest: 150/150; 127 production CPPs compiled once; 93 public headers.\n')
note=out/'COMPLETED.md';assert not note.exists()
note.write_text('''# Server metadata batch admitted

Eight shared Server/LocalServer/RemoteServer metadata and type/cast methods add sixteen per-ELF declaration-pending identities. No existing public header changed. Actual CCL CStringBuffer<64>/<256> supplies storage and ordinary assignment; its source and license are unchanged.

Original ARM app code plus the matching firmware libc-2.9 strlen/strncpy bodies passed 2,884 new witnesses, including self/cross/interior aliases and full-buffer sentries. An unchanged CCL interior-overlap probe passed Release but failed ASan's strncpy overlap check; both results and pre-adaptation source are retained. An explicit app-only interior-pointer helper uses defined memmove after clearing the first byte, matching original witnesses and preserving self-alias clearing and untouched tails. No Core binary body was executed.

Server getInfo preserves the caller's descriptor word zero. Local getDescription writes only observed pointers/flags/word9; remote setDescription preserves its identifier. Descriptor field composition and borrowed state are source-port choices. Proven Server-to-Local/Remote inheritance and virtual getType are retained. The native partial getType-only table differs from original D1/D0/getType; tagged construction and protected nonvirtual trivial lifetime avoid fabricated original lifecycle definitions, whose exact names are absent from selected native objects. Original lifecycle, complete layout, ownership and return declarations remain unresolved.

Validation passed 2,884 new and 18,614 retained cases per Release/San, the actual production bridge, exact linked member/object/dependency closure and original range checks. Canonical totals: 639 ready records / 343 unique names; 507 pending records / 295 unique names. No demotions, promotions or prior identity removals. Eight names were added here, 54 since resume. There are 6,994 non-Core names without admitted implementations, 2,541 Core source-route names and 9,830 names remaining to readiness.

Linux passed 150/150 CTest, formatter 23.1.3, all 127 production CPPs compiled once (83 common / 33 CS18 / 11 RM), 93 public headers and relocated role consumers. The source/proof audit checked 1,230 hashes. Retained raw MCU coverage is separately counted at 115,933 cases.

The unchanged combined merger proof/admission is in combined-preflight-01/validation.json and admission-01/validation.json. Canonical tracker: uc-library/SYMBOLS.md. Generated checkpoint: temp/recovery-work/checkpoints/2026-10-28-metadata.md.

Work continues with offline programmer erase/update, nine mixer interpolator methods and the next Network selection. No pause, physical device operation, Mac synchronization, commit or push.
''')
with (out/'queue-events.jsonl').open('a') as stream:
    for event,path in [('batch-admitted',out/'admission-01/validation.json'),('role-audit-finished',lib/role['proof'])]:
        stream.write(json.dumps(dict(event=event,artifact=str(path.relative_to(repo)),artifact_sha256=sha(path),artifact_write_time=datetime.fromtimestamp(path.stat().st_mtime,timezone.utc).isoformat(),recorded_at=datetime.now(timezone.utc).isoformat()))+'\n')
nextfile=repo/'temp/recovery-work/NEXT.md';(out/'next-before-close.md').write_bytes(nextfile.read_bytes())
nextfile.write_text('Server metadata batch admitted; no pause. Read metadata COMPLETED.md and checkpoint. Next: offline programmer update, nine interpolators and next Network selection. Root owns integration.\n')
print(json.dumps(dict(batch_complete=True,ready=639,pending=507,remaining_unique=9830,uncompiled_non_core=6994,continuing=True)))
