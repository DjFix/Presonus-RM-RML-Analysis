import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import unicorn

TASK = "rolling_c001_969da9b9f82be3d3"
TEST = Path("uc-library/tests/recovery") / TASK
SOURCE = Path("uc-library/src/Presonus/Mixer/MasterSectionComponent.cpp")
HEADER = Path("uc-library/include/presonus/mixer/MasterSectionComponent.hpp")
TIMER = Path("uc-library/src/Presonus/DelayTimer.cpp")
CLOCK = Path("uc-library/src/Presonus/DICE/PacketClockGateway.cpp")
FORMATTER = Path("uc-library/.venv/bin/clang-format")
WORK = Path("temp/recovery-work") / TASK
PACKET = Path("temp/recovery-work/rolling-c001-20261124/packeting/reserve01/packets") / TASK
CANDIDATE = Path("uc-library/candidates") / TASK
ROOT = Path("/home/rs/projects/opencs/ai-line-analysis")
ARCHIVE = ROOT / "temp/core-upstream/root-integration-01/upstream-core/sdk/lib"
ELF = ROOT / "temp/recovery-work/rolling-c001-20261124/packeting/reserve01/snapshot/rootfs/RML16AI_Rack_13731/home/root/mixer"
CCL = [Path("third_party/ccl-framework/core/portable") / name for name in
       ("corecomponent.h", "corecomponent.cpp", "coreparams.h", "coretypeinfo.h")]
DOMAIN = ("Three verified ARM executions and three portable calls covering distinct receiver/event "
          "addresses and data sentinels. ARM restored the stack and frame, preserved argument "
          "registers, and accessed only its stack frame. Portable calls used a constructed and "
          "destroyed CCL-backed receiver and left the event, cache and dirty flag unchanged.")
LIMITS = ["The portable declaration is a direct non-static, nonvirtual void member. "
          "Native return type and original declaration details remain unresolved. "
          "The vtable word and adjusting thunk are recorded without verifying dispatch or layout. "
          "The replay event is an opaque token. Original lifecycle, ARM ABI and hardware are unverified."]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("format", "compile", "symbols", "replay", "all"))
    parser.add_argument("--exe", type=Path, default=WORK / "replay")
    parser.add_argument("--object", type=Path, default=WORK / "production.o")
    parser.add_argument("--fixtures", required=True, type=Path)
    parser.add_argument("--integration", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    start = datetime.now(timezone.utc).isoformat()
    checks = []

    def run(argv):
        argv = [str(value) for value in argv]
        begin = time.monotonic()
        result = subprocess.run(argv, text=True, capture_output=True, env={**os.environ, "TMPDIR": str(WORK.resolve())})
        checks.append(dict(argv=argv, returncode=result.returncode, stdout=result.stdout,
                           stderr=result.stderr, seconds=time.monotonic() - begin))
        if result.returncode:
            raise RuntimeError(checks[-1])
        return result.stdout

    if args.mode in ("format", "all"):
        run([FORMATTER, "--style=file", "--fallback-style=LLVM", "--dry-run", "--Werror",
             SOURCE, HEADER, TEST / "Replay.cpp"])
    archives = [ARCHIVE / name for name in ("libcorelib.a", "libpresonus_core_allocator.a")]
    if args.mode in ("compile", "all"):
        WORK.mkdir(parents=True, exist_ok=True)
        flags = ["c++", "-std=c++17", "-O2", "-fno-rtti", "-ffunction-sections", "-fdata-sections",
                 "-Iuc-library/include", "-Ithird_party/ccl-framework", "-Ulinux", "-Wno-multichar"]
        run([*flags, "-c", SOURCE, "-o", args.object])
        run([*flags, TEST / "Replay.cpp", TIMER, CLOCK, args.object, "-Wl,--gc-sections",
             "-Wl,--start-group", *archives, "-Wl,--end-group", "-lpthread", "-ldl", "-o", args.exe])
    fixture = json.loads(args.fixtures.read_text())
    identity = fixture["range"]
    if args.mode in ("symbols", "replay", "all"):
        symbols = [line.split()[-1] for line in run(["nm", "--defined-only", args.object]).splitlines()]
        assert symbols.count(identity["mangled"]) == 1
    if args.mode in ("replay", "all"):
        native = [sys.executable, "-B", TEST / "native.py", "--elf", ELF, "--fixtures", args.fixtures]
        run(native)
        result = run([args.exe]).splitlines()
        assert result == [str(int(case["state_changed"])) for case in fixture["cases"]]
        sources = {str(path.relative_to("uc-library")): digest(path) for path in
                   [SOURCE, HEADER, TIMER, CLOCK, TEST / "Replay.cpp", TEST / "native.py",
                    TEST / "check.py", args.fixtures]}
        ccl = {str(path): digest(path) for path in CCL}
        row = dict(original_elf_sha256=identity["elf_sha256"], mangled=identity["mangled"],
                   sources=sources, repository_sources=ccl, domain=DOMAIN, portable_ready=False,
                   cpp_compiled=True, mangling_namespace_checked=True, declaration_uncertainties=LIMITS)
        proof = dict(verified=True, validation_domain=DOMAIN, original=identity,
                     native_cases=len(fixture["cases"]), portable_cases=len(result),
                     proposed_readiness=dict(ready=[], pending=[row]),
                     formatter=run([FORMATTER, "--version"]).strip(),
                     compiler=run(["c++", "--version"]).splitlines()[0],
                     unicorn=unicorn.__version__, checks=checks,
                     sources=sources, provider_archives={str(path): digest(path) for path in archives},
                     object_sha256=digest(args.object), executable_sha256=digest(args.exe),
                     integration_sha256=digest(args.integration) if args.integration else None,
                     workspaces=dict(expected=str(ROOT / "temp/recovery-work/production-20261112/agent-repos/rack01"),
                                     actual=run(["git", "rev-parse", "--show-toplevel"]).strip()),
                     start_utc=start, end_utc=datetime.now(timezone.utc).isoformat())
        (args.out or CANDIDATE / "worker-proof.json").write_text(json.dumps(proof, indent=2) + "\n")
        print(DOMAIN)


if __name__ == "__main__":
    main()
