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
HEADER = Path("uc-library/include/presonus/ModalPageComponent.hpp")
SOURCE = Path("uc-library/src/Presonus/ModalPageComponent.cpp")
SCRATCH = Path("temp/recovery-work/cycle20_g08") / TASK
FORMATTER = "uc-library/.venv/bin/clang-format"
FORMAT = [FORMATTER, "--style=file", "--fallback-style=LLVM", "--dry-run", "--Werror",
          HEADER, SOURCE, TEST / "Replay.cpp"]
DOMAIN = ("Eight direct original executions with four receiver byte patterns and two scratch r2 values, "
          "using the exact ELF range. Four bounded original caller executions start at the virtual dispatch "
          "sequence or zero-result comparison and stop at close entry or caller return, respectively. "
          "Portable differential uses real ModalPageComponent objects, checks the bool result and "
          "preserves three positive and two negative cast IDs and both adjacent guard values.")
LIMITATIONS = [
    "Portable bool reflects the observed native return value and caller zero test. The exact original "
    "C++ return declaration remains unresolved.",
    "Original virtual layout, inheritance, ARM ABI and hardware behavior are unresolved.",
    "The caller replay starts after parameter conversion. It stops before close execution or external "
    "provider/UI lifecycle behavior. The portable class models the leaf only.",
]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("format", "compile", "symbols", "replay"))
    parser.add_argument("--exe", type=Path, default=SCRATCH / "Replay")
    parser.add_argument("--object", type=Path, default=SCRATCH / "ModalPageComponent.cpp.o")
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
        flags = ["c++", "-std=c++17", "-O3", "-DNDEBUG", "-Wall", "-Wextra", "-Wpedantic",
                 "-pthread", "-Ulinux", "-Iuc-library/include"]
        run(flags + ["-c", SOURCE, "-o", args.object])
        run(flags + [TEST / "Replay.cpp", args.object, "-o", args.exe])
        (SCRATCH / "compilation.json").write_text(json.dumps(commands, indent=2) + "\n")
        return
    fixture = json.loads(args.fixtures.read_text())
    original = fixture["original_range"]
    mangled = original["symbol"]
    symbols = run(["nm", "--defined-only", args.object])
    if not any(line.split()[-2:] == ["T", mangled] for line in symbols.splitlines()):
        raise SystemExit(f"Expected exact defined original mangling: {mangled}")
    if args.mode == "symbols":
        return
    if args.out is None:
        parser.error("replay requires --out")
    run(FORMAT)
    formatter = run([FORMATTER, "--version"]).strip()
    cases = fixture["leaf_cases"]
    lines = run([args.exe.resolve()],
                "".join(f"{case['seed']} {case['unused_r2']}\n" for case in cases)).splitlines()
    if not cases or lines != [str(case["result_r0"]) for case in cases]:
        raise SystemExit("Portable replay output differed from original ELF observations")

    files = [HEADER, SOURCE, TEST / "Replay.cpp", TEST / "native.py", TEST / "check.py",
             args.fixtures]
    bindings = {str(path.relative_to("uc-library")): sha(path) for path in files}
    entry = dict(original_elf_sha256=fixture["elf_sha256"], mangled=mangled,
                 original_address=original["address"], sources=bindings, repository_sources={},
                 domain=DOMAIN, portable_ready=False, cpp_compiled=True,
                 mangling_namespace_checked=True, declaration_uncertainties=LIMITATIONS)
    proof = dict(
        version=1, task_id=TASK, producer_session_id=os.environ.get("CODEX_THREAD_ID"),
        created_utc=dt.datetime.now(dt.timezone.utc).isoformat(), functions=[entry],
        proposed_readiness=dict(ready=[], pending=[entry]),
        compiled_mangled_names_matched=True, cpp_differential_passed=True, cpp_compiled=True,
        portable_ready=False, original_arm_abi_verified=False, hardware_verified=False,
        limitations=LIMITATIONS, case_count=len(cases),
        native_caller_cases=len(fixture["caller_cases"]),
        original_range=original, caller_range=fixture["caller_range"],
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
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(proof, indent=2) + "\n")
    print(f"{TASK}: {len(cases)} native/portable differential cases passed")


if __name__ == "__main__":
    main()
