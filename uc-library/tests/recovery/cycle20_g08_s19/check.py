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
HEADER = Path("uc-library/include/presonus/panel/PresetComponent.hpp")
SOURCE = Path("uc-library/src/Presonus/Panel/PresetComponent.cpp")
SCRATCH = Path("temp/recovery-work/cycle20_g08-rack-preset") / TASK
FORMATTER = "uc-library/.venv/bin/clang-format"
FORMAT = [FORMATTER, "--style=file", "--fallback-style=LLVM", "--dry-run", "--Werror",
          HEADER, SOURCE, TEST / "Replay.cpp"]
DOMAIN = 'Three direct, three primary vtable and three 132-byte native adjustor executions. Six portable calls preserve accepted PresetNameCache entries and observer state and real CCL parameters. Existing four-argument callback exercised on both matching and nonmatching slots without preset I/O.'
LIMITATIONS = [
    "Portable void models the effect-free leaf. Original return declaration and host layout remain unresolved.",
    "The original ARM secondary adjustor is evidence-only. No portable secondary ABI is claimed.",
    "The native vtable dispatch harness uses exact table bytes and synthetic receiver/cache windows.",
    "The live CCL exercise uses caller-safe UI fixtures and no hardware or directory access.",
]
CACHE_SOURCE = Path("uc-library/src/Presonus/Panel/PresetNameCache.cpp")
CACHE_HEADER = Path("uc-library/include/presonus/panel/PresetNameCache.hpp")
CORE = Path("third_party/ccl-framework/core")
PROVIDER_SOURCES = [CORE / relative for relative in (
    "portable/corecomponent.h", "portable/corecomponent.cpp",
    "portable/corefile.h", "portable/corefilename.h",
    "portable/coreparams.cpp", "portable/coreparams.h", "public/corevector.h",
    "public/corestringbuffer.h",
)]
ARCHIVE_DIR = Path("temp/recovery-work/cycle20_g08-rack-preset/providers")
ARCHIVES = [ARCHIVE_DIR / name for name in (
    "libpresonus_rm_components.a", "libpresonus_uc.a", "libcorelib.a", "libpresonus_core_allocator.a",
    "libpresonus_private_glibc29.a",
)]


def zlib_input():
    input_record = json.loads((ARCHIVE_DIR / "ZLIB-LINK-INPUT.json").read_text())
    path = Path(input_record["resolved"])
    if sha(path) != input_record["sha256"]:
        raise SystemExit("Transitive zlib provider input changed")
    return path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("format", "compile", "symbols", "replay"))
    parser.add_argument("--exe", type=Path, default=SCRATCH / "Replay")
    parser.add_argument("--object", type=Path, default=SCRATCH / "PresetComponent.cpp.o")
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
                 '-I/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/control10x20-after-4fed70d11/workspaces/actual05-batch02-cycle20_g08/provider-overlay/uc-library/include', "-Iuc-library/include", "-Ithird_party/ccl-framework"]
        replay_object = SCRATCH / "Replay.cpp.o"
        cache_object = SCRATCH / "PresetNameCache.cpp.o"
        for source, output in ((SOURCE, args.object), (CACHE_SOURCE, cache_object),
                               (TEST / "Replay.cpp", replay_object)):
            run(flags + ["-fno-rtti", "-MMD", "-MF", str(output) + ".d",
                         "-c", source, "-o", output])
        run(["/usr/bin/c++", replay_object, args.object, cache_object,
             "-Wl,--start-group", *ARCHIVES, "-Wl,--end-group", "-Wl,--gc-sections",
             "-pthread", "-ldl", "-lm", zlib_input(), "-o", args.exe])
        zlib_input()
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
    native_cases = fixture["cases"]
    cases = [case for case in native_cases if case["mode"] != "native-adjustor"]
    stdin = "".join(f"{int(case['mode'] == 'primary-vtable')} {case['seed']}\n" for case in cases)
    lines = run([args.exe.resolve()], stdin).splitlines()
    if not cases or lines != [str(int(case["observed_unchanged"])) for case in cases]:
        raise SystemExit("Portable FX observer behavior differed from original ELF observations")
    domain = DOMAIN

    files = [HEADER, SOURCE, TEST / "Replay.cpp", TEST / "native.py", TEST / "check.py",
             args.fixtures]
    bindings = {str(path.relative_to("uc-library")): sha(path) for path in files}
    entry = dict(original_elf_sha256=fixture["elf_sha256"], mangled=mangled,
                 original_address=original["address"], sources=bindings,
                 repository_sources={str(path): sha(path) for path in PROVIDER_SOURCES},
                 domain=domain, portable_ready=False, cpp_compiled=True,
                 mangling_namespace_checked=True, declaration_uncertainties=LIMITATIONS)
    proof = dict(
        version=1, task_id=TASK, producer_session_id=os.environ.get("CODEX_THREAD_ID"),
        created_utc=dt.datetime.now(dt.timezone.utc).isoformat(), functions=[entry],
        proposed_readiness=dict(ready=[], pending=[entry]),
        compiled_mangled_names_matched=True, cpp_differential_passed=True, cpp_compiled=True,
        portable_ready=False, original_arm_abi_verified=False, hardware_verified=False,
        limitations=LIMITATIONS, case_count=len(cases),
        original_range=original, native_vtable_slot=fixture["slot_offset"],
        native_case_count=len(native_cases), native_adjustor=fixture["secondary_adjustor"],
        vtable_range=fixture["vtable_range"], fixture_sha256=sha(args.fixtures),
        inspected_source_dependencies={str(path): sha(path) for path in (CACHE_HEADER, CACHE_SOURCE)},
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
