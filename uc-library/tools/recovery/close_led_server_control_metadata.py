"""Generate this batch's compact checkpoint and bounded raw tracking update."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

assert sys.platform.startswith("linux")
repo=Path.cwd().resolve();lib=repo/"uc-library"
phase=repo/"evidence/recovery/2026-10-27/led-server-control-root"
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
source=repo/"uc-library/tools/recovery/count_current_unique.py"
target=repo/"uc-library/tools/recovery/count_led_server_control_unique.py"
assert not target.exists()
target.write_text(source.read_text().replace("file-transfer-panel-root/unique-current.json","led-server-control-root/unique-current.json"))
subprocess.run([sys.executable,str(target)],check=True)
counter=read(phase/"unique-current.json")
assert (counter["unique_total"],counter["remaining_unique"],counter["per_elf_ready"],counter["per_elf_pending"])==(10173,9853,603,320)
tracker=lib/"validation/embedded-efm/SYMBOLS.md"
old=tracker.read_text()
assert "## Current LED/server/control batch" not in old
raw=phase/"raw-active-01/validation.json"
tracker.write_text(old+f'''
## Current LED/server/control batch — 2026-10-27

The preceding snapshots are historical bounded proofs. The control dispatcher is
now compiled at `src/embedded_efm/efm_control_dispatch.cpp`, with public header
`presonus/embedded_efm/efm_control_dispatch.hpp`, in independent namespace
`presonus::analysis::efm_fader_control_dispatch`.

| Original workload | Current status / bounded evidence |
|---|---|
| Partial dispatch `0x2230`, commands `0x11/0x91`, `0x24/0xa4`, `0x26/0xa6`, defaults and RAM helper `0x24d8` | 34,752 original Thumb/native RAM and callback-event cases; 34 separate portable guards. Original input/range hashes remain in `candidates/efm-fader-control-dispatch/validation/native-01/validation.json`. |
| Reinitialization commands `0x11/0x91` | Mandatory synthetic callback boundaries at `0x16bc` and `0x1fa8`; helper bodies/MMIO are not verified. |
| Persistence/reset flags | RAM flag effects verified; later main-loop persistence/reset and physical peripherals remain unresolved. |

Current all-eight-driver active seal:
`evidence/recovery/2026-10-27/led-server-control-root/raw-active-01/validation.json`,
SHA `{sha(raw)}`. It replays **115,933** cases, including **88** separate
portable guards; verifies seven CS18 production units and their presence in
UC/CS18 archives and absence from RM. The root integration passed **114** CTest
suites and installed **80** application public headers. Raw MCU ports add no
host ELF readiness identities. No bootloader, full firmware, ARM ABI or hardware
completion is claimed.
''')
command=[sys.executable,str(lib/"tools/generate_checkpoint.py"),"--library",str(lib),"--repository",str(repo),"--phase","led-server-control","--baseline",str(repo/"temp/recovery-work/checkpoints/2026-10-27-file-transfer-panel.json"),"--output",str(repo/"temp/recovery-work/checkpoints/2026-10-27-led-server-control.md")]
subprocess.run(command,check=True)
role=read(lib/"validation/role-build-audit/validation.json") if (lib/"validation/role-build-audit/validation.json").exists() else None
(phase/"README.md").write_text(f'''# LED, FileServer and partial raw-control checkpoint

Linux canonical integration: 114/114 CTest. 95 production CPP units: 64 common,
25 CS18 and 6 RM; 80 installed application public headers. Strict clang-format
23.1.3 passed on all 12 changed C++ paths without edits.

The guarded combined preflight and admission preserved all old identities:
**603 per-ELF ready**, **322 names ready in at least one role** and
**320 declaration-pending**. LED lifecycle contributes 8 ready records /4 names;
ordinary LED and FileServer methods retain explicit unresolved declarations.
FileServer uses mandatory independent service boundaries; its original default
constructor and real application manager/network closure remain unresolved.

Unique exact-name workload: **9,853 remaining** of10,173, including
**{counter['manual_remaining']} outside Core** and
**{counter['core_source_route_remaining']} via pinned CCL source**.
All-role complete names: {counter['complete_all_roles']}. See `unique-current.json`.

Evidence: `linux/`, `apply-01/`, `producer-derivatives.json`, `noaa-active.log`,
`led-active.log`, `file-server-active.log`, `raw-active-01/`,
`combined-preflight.log`, `admission-01/`, `public-headers.log`, `role-audit.log`.
The canonical symbol table is `uc-library/SYMBOLS.md`; raw functions are separate
in `uc-library/validation/embedded-efm/SYMBOLS.md`.

No Core binary reconstruction, hardware IO or ARM ABI compatibility is claimed.
''')
print(json.dumps(dict(remaining_unique=counter["remaining_unique"],manual_remaining=counter["manual_remaining"],raw_tracker_sha256=sha(tracker),checkpoint="temp/recovery-work/checkpoints/2026-10-27-led-server-control.md")))
