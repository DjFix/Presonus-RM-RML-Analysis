"""Create the SPI/AVB checkpoint, exact unique counter and raw refresh note."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

assert sys.platform.startswith("linux")
repo=Path.cwd().resolve();lib=repo/"uc-library";phase=repo/"evidence/recovery/2026-10-27/spi-avb-helpers-root"
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
target=repo/"uc-library/tools/recovery/count_spi_avb_helpers_unique.py"
assert not target.exists()
source=repo/"uc-library/tools/recovery/count_current_unique.py"
target.write_text(source.read_text().replace("file-transfer-panel-root/unique-current.json","spi-avb-helpers-root/unique-current.json"))
subprocess.run([sys.executable,str(target)],check=True)
counter=json.loads((phase/"unique-current.json").read_text())
assert (counter["remaining_unique"],counter["complete_all_roles"],counter["ready_any_role"],counter["per_elf_ready"],counter["per_elf_pending"])==(9846,327,327,610,326)
tracker=lib/"validation/embedded-efm/SYMBOLS.md"
old=tracker.read_text();assert "## SPI/AVB archive refresh" not in old
tracker.write_text(old+f'''
## SPI/AVB archive refresh — 2026-10-27

The same eight raw suites freshly passed against the current root archives:
115,933 bounded cases, including88 independent portable guards. The new seal is
`evidence/recovery/2026-10-27/spi-avb-helpers-root/raw-active-01/validation.json`,
SHA `{sha(phase/'raw-active-01/validation.json')}`. Root integration now passes
116 CTest suites and installs81 application headers. The raw CPP/header sources,
namespaces and original semantic limitations are unchanged; no original oracle
was regenerated and no hardware or host-ready identity is claimed for raw MCU.
''')
subprocess.run([sys.executable,str(lib/"tools/generate_checkpoint.py"),"--library",str(lib),"--repository",str(repo),"--phase","spi-avb-helpers","--baseline",str(repo/"temp/recovery-work/checkpoints/2026-10-27-led-server-control.json"),"--output",str(repo/"temp/recovery-work/checkpoints/2026-10-27-spi-avb-helpers.md")],check=True)
(phase/"README.md").write_text(f'''# SPI service and shared RM AVB helper checkpoint

Canonical Linux integration: **116/116 CTest**.96 production CPPs compile once:
64 common,25 CS18,7 RM;81 application public headers installed. Six changed C++
files passed strict clang-format23.1.3 with zero changes.

**610 per-ELF ready**, **327 distinct names**, **326 declaration-pending**.
All327 ready names are now complete across applicable selected ELF roles.
**9,846 unique names remain**, including **{counter['manual_remaining']} outside
Core** and **{counter['core_source_route_remaining']} through pinned CCL source**.
The original ABI-adjusting SPI thunk remains unready (ARM-4 vs native-8).
Six new ordinary SPI methods retain unresolved original return declarations.

Five newly ready SPI lifecycle identities use real CCL and admitted InputPin;
their native Release/ASan/UBSan replay covers1,565 operation and516 lifecycle
cases, plus6,369 retained dependency cases. Provider vptr instrumentation is
excluded because the actual source-built provider lacks matching RTTI.
Actual D1/D0 cleanup/deallocation and C1/C2,D1/D2 aliases are tracked separately.
The old-five NOAA source closure is preserved; only the SPI header and two root
CMake hashes were intentionally rebound and current root objects/archive checked.

Two previously client-only AVB names now also have fresh RM ARM observations:
6,146 reverseEndian and2,440 unpackAvbSpiMsg cases, full RAM comparisons and
current native fixture replay. Both roles share the same CPP/object partition;
no duplicate code or new convenience identity substitutes original mangles.

All eight raw MCU suites freshly replayed115,933 cases against current archives.
See `raw-active-01/`, `spi-root-closure-01/`, `avb-active-01/`,
`combined-preflight-01/`, `admission-01/` and full logs alongside this file.
Core binary recovery, physical IO, full application startup and ARM ABI
compatibility remain outside these validated portable domains.
''')
print(json.dumps(dict(remaining_unique=counter["remaining_unique"],manual_remaining=counter["manual_remaining"],partial_roles=counter["manual_buckets"]["partial_role_ready"])))
