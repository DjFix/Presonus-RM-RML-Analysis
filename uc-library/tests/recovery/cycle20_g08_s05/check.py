"""Replay the sealed UI capability fixture against the compiled C++ method."""

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

TASK = Path(__file__).resolve().parent.name
TEST = Path("uc-library/tests/recovery") / TASK
HEADER = Path("uc-library/include/presonus/panel/AlertBook.hpp")
SOURCE = Path("uc-library/src/Presonus/Panel/AlertBook.cpp")
SCRATCH = Path("temp/recovery-work/cycle20_g08-alertbook") / TASK
FORMATTER = "uc-library/.venv/bin/clang-format"
FORMAT = [FORMATTER, "--style=file", "--fallback-style=LLVM", "--dry-run", "--Werror",
          HEADER, SOURCE, TEST / "Replay.cpp"]
DOMAIN = (
    "Four independent original ELF executions entered at the exact AlertBook vtable slot target, "
    "with varied synthetic receiver and external byte regions and traced stack-only accesses. "
    "Four actual portable AlertBook scenarios preserve mode, page and selection identity, timer, "
    "CCL text/numeric values, observer and selection write counts, and clock reads. "
    "Cases include null page/selection, populated registration, repeated observer registration, "
    "absent text parameters and a numeric parameter under a text tag."
)
LIMITATIONS = [
    "Portable void models the observed state-preserving leaf. Native r0 preservation does not "
    "resolve the original C++ return declaration.",
    "Original layout, inheritance, original caller context, ARM ABI and hardware behavior remain unresolved.",
    "Native receiver and external byte windows are synthetic. Portable validation uses real pinned "
    "CCL providers and a test clock wrapper, with no hardware operations.",
]
CORE = Path("third_party/ccl-framework/core")
PROVIDER_SOURCES = [CORE / relative for relative in (
    "portable/corecomponent.h", "portable/corecomponent.cpp",
    "portable/coreparams.h", "portable/coreparams.cpp", "public/corevector.h",
    "system/coretime.h", "platform/shared/posix/coretime.posix.h",
    "system/coredebug.h", "system/coredebug.cpp",
)]
BUILD = Path("/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01")
ARCHIVES = [BUILD / relative for relative in (
    "libpresonus_uc.a", "upstream-core/sdk/lib/libcorelib.a",
    "upstream-core/sdk/lib/libpresonus_core_allocator.a",
    "private-glibc29-provider/libpresonus_private_glibc29.a",
)]

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("format", "compile", "symbols", "replay"))
    parser.add_argument("--exe", type=Path, default=SCRATCH / "Replay")
    parser.add_argument("--object", type=Path, default=SCRATCH / "AlertBook.cpp.o")
    parser.add_argument("--fixtures", type=Path, default=TEST / "fixtures.json")
    parser.add_argument("--integration", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    commands = []

    def run(argv, stdin=None):
        argv = list(map(str, argv))
        start_utc = dt.datetime.now(dt.timezone.utc).isoformat()
        start = time.monotonic()
        result = subprocess.run(argv, input=stdin, text=True, capture_output=True, check=False)
        item = dict(argv=argv, start_utc=start_utc, seconds=time.monotonic() - start,
                    returncode=result.returncode, stdout=result.stdout, stderr=result.stderr)
        commands.append(item)
        print(json.dumps(item), flush=True)
        result.check_returncode()
        return result.stdout

    if args.mode == "format":
        run([FORMATTER, "--version"])
        run(FORMAT)
        return
    if args.mode == "compile":
        SCRATCH.mkdir(parents=True, exist_ok=True)
        flags = ["/usr/bin/c++", "-std=c++17", "-O3", "-DNDEBUG", "-Wno-multichar",
                 "-ffunction-sections", "-fdata-sections", "-pthread", "-Ulinux",
                 "-Iuc-library/include", "-Ithird_party/ccl-framework"]
        replay_object = SCRATCH / "Replay.cpp.o"
        run(flags + ["-c", SOURCE, "-o", args.object])
        run(flags + ["-fno-rtti", "-c", TEST / "Replay.cpp", "-o", replay_object])
        run(["/usr/bin/c++", replay_object, args.object, "-Wl,--start-group", *ARCHIVES,
             "-Wl,--end-group", "-Wl,--gc-sections", "-Wl,--wrap=clock_gettime",
             "-pthread", "-ldl", "-lm", "-o", args.exe])
        (SCRATCH / "compilation.json").write_text(json.dumps(commands, indent=2) + "\n")
        return
    fixture = json.loads(args.fixtures.read_text())
    original = fixture["original_range"]
    mangled = original["mangled"]
    symbols = run(["nm", "--defined-only", args.object])
    if not any(line.split()[-2:] == ["T", mangled] for line in symbols.splitlines()):
        raise SystemExit(f"Expected exact defined original mangling: {mangled}")
    if args.mode == "symbols":
        return
    if args.out is None:
        parser.error("replay requires --out")
    run(FORMAT)
    formatter = run([FORMATTER, "--version"]).strip()
    cases = fixture["cases"]
    keys = ("mode", "page", "selection", "duplicate", "nanoseconds", "shape")
    stdin = "".join(" ".join(str(case[key]) for key in keys) + "\n" for case in cases)
    lines = run([args.exe.resolve()], stdin).splitlines()
    if not cases or lines != [str(int(case["observed_unchanged"])) for case in cases]:
        raise SystemExit("Portable state preservation differed from original ELF observations")

    files = [HEADER, SOURCE, TEST / "Replay.cpp", TEST / "native.py", TEST / "check.py",
             args.fixtures]
    bindings = {str(path.relative_to("uc-library")): sha(path) for path in files}
    entry = dict(original_elf_sha256=fixture["elf_sha256"], mangled=mangled,
                 original_address=original["address"], sources=bindings,
                 repository_sources={str(path): sha(path) for path in PROVIDER_SOURCES},
                 domain=DOMAIN, portable_ready=False, cpp_compiled=True,
                 mangling_namespace_checked=True, declaration_uncertainties=LIMITATIONS)
    proof = dict(
        version=1, task_id=TASK, producer_session_id=os.environ.get("CODEX_THREAD_ID"),
        created_utc=dt.datetime.now(dt.timezone.utc).isoformat(), functions=[entry],
        proposed_readiness=dict(ready=[], pending=[entry]),
        compiled_mangled_names_matched=True, cpp_differential_passed=True, cpp_compiled=True,
        portable_ready=False, original_arm_abi_verified=False, hardware_verified=False,
        limitations=LIMITATIONS, case_count=len(cases),
        original_range=original, native_vtable_slot=fixture["slot_offset"],
        vtable_range=fixture["vtable_range"], fixture_sha256=sha(args.fixtures),
        source_bindings=bindings, commands=commands, formatter_version=formatter,
        executable=dict(path=str(args.exe), sha256=sha(args.exe)),
        object=dict(path=str(args.object), sha256=sha(args.object)),
    )
    compile_log = SCRATCH / "compilation.json"
    if args.integration is not None:
        proof["integration"] = dict(path=str(args.integration), sha256=sha(args.integration))
    elif compile_log.exists():
        proof["compilation"] = json.loads(compile_log.read_text())
        proof["local_provider_archives"] = {str(path): sha(path) for path in ARCHIVES}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(proof, indent=2) + "\n")
    print(f"{TASK}: {len(cases)} native/portable differential cases passed")


if __name__ == "__main__":
    main()
