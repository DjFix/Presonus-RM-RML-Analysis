"""Generate this closed batch's exact counter, checkpoint and bounded notes."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

assert sys.platform.startswith("linux")
repo=Path.cwd().resolve();lib=repo/"uc-library";phase=repo/"evidence/recovery/2026-10-27/receiver-transfer-root"
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
target=repo/"uc-library/tools/recovery/count_receiver_transfer_unique.py"
assert not target.exists()
source=repo/"uc-library/tools/recovery/count_current_unique.py"
target.write_text(source.read_text().replace("file-transfer-panel-root/unique-current.json","receiver-transfer-root/unique-current.json"))
subprocess.run([sys.executable,str(target)],check=True)
counter=json.loads((phase/"unique-current.json").read_text())
assert (counter["remaining_unique"],counter["complete_all_roles"],counter["ready_any_role"],counter["per_elf_ready"],counter["per_elf_pending"])==(9839,334,334,622,358)
tracker=lib/"validation/embedded-efm/SYMBOLS.md"
old=tracker.read_text();assert "## Receiver/transfer/Switch archive refresh" not in old
tracker.write_text(old+f'''
## Receiver/transfer/Switch archive refresh — 2026-10-27

All eight unchanged raw suites freshly passed against current role archives:
115,933 cases including88 independent guards. Current proof is
`evidence/recovery/2026-10-27/receiver-transfer-root/raw-active-01/validation.json`,
SHA `{sha(phase/'raw-active-01/validation.json')}`. Root integration passed121
CTest suites and installed83 application headers. No raw namespace, source or
original semantic domain changed; hardware and ARM ABI remain unverified.
''')
subprocess.run([sys.executable,str(lib/"tools/generate_checkpoint.py"),"--library",str(lib),"--repository",str(repo),"--phase","receiver-transfer","--baseline",str(repo/"temp/recovery-work/checkpoints/2026-10-27-spi-avb-helpers.json"),"--output",str(repo/"temp/recovery-work/checkpoints/2026-10-27-receiver-transfer.md")],check=True)
(phase/"README.md").write_text(f'''# Receiver, transfer manager and Switch lifecycle checkpoint

Linux canonical integration: **121/121 CTest**,100 production CPPs compiled once:
67 common,25 CS18,8 RM;83 application headers installed. Fourteen changed C++
files passed strict clang-format23.1.3 without edits.

**622 per-ELF ready /334 unique ready names /358 declaration-pending**.
All old ready/pending identities preserved, no stale removals or status changes.
Unique remaining **9,839** of10,173: **{counter['manual_remaining']} outside Core**
and **{counter['core_source_route_remaining']} through CCL**. All334 ready names
cover their applicable selected roles. See `unique-current.json`.

New readiness is bounded: two NOAA receiver constructors and ten Switch
lifecycle identities (five variants per ELF role). Ordinary receiver/Switch
returns remain pending. The eleven manager methods add22 ordinary pending
records, not a manager lifecycle/gateway readiness claim. Actual Core comes
from pinned CCL; no original Core binary bodies execute.

Fresh active proofs include receiver4,214cases+13 retained dependency runs,
manager6,016cases+11,052 old FileTransfer cases and actual cleanup/providers,
Switch13,256cases+actual lifecycle cleanup, SPI8,450 operation/lifecycle/old
dependency cases, and all eight raw suites115,933cases. Unknown Switch receiver
identity and remaining four dispatch methods are separate candidate work.
Manager concrete network services/lifecycle and full application startup remain
unresolved; no hardware or original ARM object ABI compatibility claim.

All31 previously ready and22 pending source-affected records were refreshed.
Full original source closures, byte ranges, mangles, CCL and role object/archive
checks are preserved. CMake and FileTransfer friend/abstract receiver header
adaptations are explicit. The first root test attempt failed only because the
copied Switch fixture lacked its mandatory sidecar; C++ stayed unchanged.
Failed logs remain in `linux/`; successful full replay is
`linux/fixture-metadata-01/`, with `fixture-packaging-fix-01/` receipts.

Canonical symbol table: `uc-library/SYMBOLS.md`. Local mirror hashes, role/header
audit and timing receipts accompany this README after completion sync.
''')
print(json.dumps(dict(remaining_unique=counter["remaining_unique"],manual_remaining=counter["manual_remaining"],partial_role_ready=counter["manual_buckets"]["partial_role_ready"])))
