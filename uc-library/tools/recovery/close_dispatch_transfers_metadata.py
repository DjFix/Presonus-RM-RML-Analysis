"""Create the current fixed-batch checkpoint and distinguish body from declaration progress."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

assert sys.platform.startswith("linux")
repo=Path.cwd().resolve();lib=repo/"uc-library";phase=repo/"evidence/recovery/2026-10-27/dispatch-transfers-root"
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=repo/"uc-library/tools/recovery/count_current_unique.py";target=repo/"uc-library/tools/recovery/count_dispatch_transfers_unique.py"
assert not target.exists();target.write_text(source.read_text().replace("file-transfer-panel-root/unique-current.json","dispatch-transfers-root/unique-current.json"))
subprocess.run([sys.executable,str(target)],check=True)
counter=json.loads((phase/"unique-current.json").read_text())
assert (counter["remaining_unique"],counter["complete_all_roles"],counter["per_elf_ready"],counter["per_elf_pending"])==(9839,334,622,378)
tracker=lib/"validation/embedded-efm/SYMBOLS.md";old=tracker.read_text();assert "## Dispatch/transfer archive refresh" not in old
tracker.write_text(old+f'''
## Dispatch/transfer archive refresh — 2026-10-27

The same eight raw suites freshly pass against current role archives:
115,933 cases, including88 independent guards. Proof
`evidence/recovery/2026-10-27/dispatch-transfers-root/raw-active-01/validation.json`,
SHA `{sha(phase/'raw-active-01/validation.json')}`. No raw code or domain changed;
124 total Linux CTest,103 production CPPs compiled once,83 app headers installed.
''')
subprocess.run([sys.executable,str(lib/"tools/generate_checkpoint.py"),"--library",str(lib),"--repository",str(repo),"--phase","dispatch-transfers","--baseline",str(repo/"temp/recovery-work/checkpoints/2026-10-27-receiver-transfer.json"),"--output",str(repo/"temp/recovery-work/checkpoints/2026-10-27-dispatch-transfers.md")],check=True)
(phase/"README.md").write_text(f'''# Switch dispatch and transfer method checkpoint

Canonical Linux integration **124/124 CTest**,103 production CPPs compiled once:
70 common,25 CS18,8 RM.83 installed application headers. Strict clang-format23.1.3
checked8 changed C++ paths with zero edits.

Readiness remains **622 per-ELF ready /334 distinct names**. Compiled declaration-
pending records grow **358→378**: ten newly reconstructed unique ordinary
methods,20 per-ELF identities. No readiness is inferred from unencoded returns.
All existing identities and source closures are preserved. Unique remaining
**9,839**, including **{counter['manual_remaining']} outside Core** and
**{counter['core_source_route_remaining']} via CCL. Manual buckets:
`{json.dumps(counter['manual_buckets'],sort_keys=True)}`.

Four Switch methods preserve actual CCL parameter operations, callback order,
timer membership and held-release behavior. Unknown receiver callbacks remain
explicitly bounded; no original interface identity/hardware/ABI claim.
Six transfer methods compose real CCL storage/clock and retain old17methods.
CS18 incoming-rate cap16,384 and RM cap4,096 are verified from both raw images
and60 differing cases, represented by an independent seeded image-role profile
in one common implementation. Actual default manager constructor/network wiring
remains unresolved; no success stubs or application readiness claim.

Fresh active Switch44,512+13,256 cases and transfers26,418 cases pass, along with
full retained dependencies/providers; SPI6ready/10pending CMake bindings and all
eight raw suites115,933 cases freshly refreshed. Original Core bodies never
execute: actual Core provider is pinned CCL source.

Initial SPI refresh stopped BEFORE replay because its output guard detected a
retained previous-phase path. It changed no prior proof. Failed attempt/log and
corrected -02 operator are preserved. The -02 selector then stopped before
replay because it selected unchanged header dependents beyond the measured
CMake source closure. The -03 operator selected the exact affected CMake-bound
6 ready/10 pending records and passed all native/range/source gates.
See `spi-output-path-fix.json`, `spi-selector-fix.json` and all three refresh logs.

Source table `uc-library/SYMBOLS.md`; compact checkpoint in projecttemp,
full Linux/source/header/role/mirror/timing receipts retained alongside this file.
''')
print(json.dumps(dict(remaining_unique=counter["remaining_unique"],manual_buckets=counter["manual_buckets"],new_compiled_unique=10,new_ready=0)))
