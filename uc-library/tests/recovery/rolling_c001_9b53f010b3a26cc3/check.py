"""Format, compile and compare the portable preset hook with fresh ARM runs."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys

import native

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parents[3]
TASK = TESTS.name
SCRATCH = Path("temp/recovery-work") / TASK
FIXTURE = TESTS.relative_to(ROOT) / "fixtures.json"
SOURCE = Path("uc-library/src/mixer_state/MixerState.cpp")
HEADER = Path("uc-library/include/presonus/mixer_state/MixerState.hpp")
REPLAY = TESTS.relative_to(ROOT) / "Replay.cpp"
CORE = [Path("third_party/ccl-framework/core/public") / name for name in
        ("corestringbuffer.h", "corestringtraits.h", "corevector.h")]
CORE += [Path("third_party/ccl-framework/core/portable/corecomponent.h")]
FORMAT = ["uc-library/.venv/bin/clang-format", "--style=file", "--fallback-style=LLVM",
          "--dry-run", "--Werror", SOURCE, HEADER, REPLAY]
CXX = ["/usr/bin/c++", "-std=c++17", "-fno-rtti", "-Wall", "-Wextra",
       "-Wno-multichar", "-Iuc-library/include", "-isystem", "third_party/ccl-framework"]
DOMAIN = 'Seven fresh original ARM executions across two synthetic receiver addresses, known and unnamed enum values and signed index extrema. Native accesses stay in the stack frame and restore registers and control flow. Portable replay constructs two distinct handlers and calls the scoped default hook. Disjoint buffer and name sentinels remain unchanged.'
LIMITATIONS = [
    "The existing portable class uses a nonvirtual instance method returning void. "
    "Original table slots associate the entry with IPresetHandler and two mixer-client "
    "tables. The exact original declaration and runtime dispatch, return type, enum "
    "representation, base relationships and ARM binary layout remain unresolved.",
    "Native executions use synthetic receivers and call-boundary values and do not "
    "exercise firmware construction, derived implementations or hardware.",
]


def utc():
    return datetime.now(timezone.utc).isoformat()


def hash_file(path):
    return native.digest(Path(path).read_bytes())


def run(argv, **options):
    command = list(map(str, argv))
    print(json.dumps(command), flush=True)
    return subprocess.run(command, check=True, cwd=ROOT, stdout=subprocess.PIPE,
                          text=True, **options).stdout


def symbol(object_file):
    output = run(["/usr/bin/nm", "--defined-only", object_file])
    match = [line for line in output.splitlines()
             if line.split() and line.split()[-1] == native.ORIGINAL["mangled"]]
    assert len(match) == 1 and match[0].split()[-2] in ("T", "W"), output
    return match[0]


def compile_local(object_file, exe):
    assert ROOT == Path.cwd().resolve(), "Run from the assigned repository root"
    SCRATCH.mkdir(parents=True, exist_ok=True)
    os.environ["TMPDIR"] = str(ROOT / SCRATCH)
    replay_object = SCRATCH / "replay.o"
    commands = [
        [*CXX, "-c", SOURCE, "-o", object_file],
        [*CXX, "-c", REPLAY, "-o", replay_object],
        [CXX[0], object_file, replay_object, "-o", exe],
    ]
    for command in commands:
        run(command)
    return commands


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", nargs="?", default="proof",
                        choices=("format", "compile", "symbols", "native", "proof"))
    parser.add_argument("--exe", type=Path, default=SCRATCH / "replay")
    parser.add_argument("--object", type=Path, default=SCRATCH / "production.o")
    parser.add_argument("--fixture", type=Path, default=FIXTURE)
    parser.add_argument("--integration", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.mode == "format":
        run(FORMAT)
        return
    if args.mode == "compile":
        compile_local(args.object, args.exe)
        return
    if args.mode == "symbols":
        print(symbol(args.object))
        return

    start = utc()
    observations = native.generate()
    assert observations == json.loads(args.fixture.read_text()), "Fresh native observations changed"
    cases = observations["cases"]
    print(f"{len(cases)} fresh original ARM executions")
    if args.mode == "native":
        return

    assert args.out is not None, "Provide a proof output path"
    run(FORMAT)
    definition = symbol(args.object)
    payload = "".join(" ".join(map(str, row["inputs"])) + "\n" for row in cases)
    output = run([args.exe], input=payload).splitlines()
    expected = [row["buffer_after"] + row["name_after"] for row in cases]
    assert [list(map(int, line.split())) for line in output] == expected
    print(f"{len(cases)} portable buffer and name comparisons passed")
    sources = {str(path.relative_to("uc-library")): hash_file(path) for path in [SOURCE, HEADER]}
    providers = {str(path): hash_file(path) for path in CORE}
    identity = native.ORIGINAL
    row = dict(original_elf_sha256=identity["elf_sha256"], mangled=identity["mangled"],
               original_address=identity["address"], cpp_compiled=True,
               mangling_namespace_checked=True, portable_ready=False, domain=DOMAIN,
               sources=sources, repository_sources=providers,
               declaration_uncertainties=LIMITATIONS)
    proof = dict(
        version=1, task_id=TASK, cpp_compiled=True, mangling_namespace_checked=True,
        cpp_differential_passed=True, formatting_verified=True, compiled=True,
        compiled_mangled_names_matched=True, fresh_native_execution=True,
        native_behavior_verified=True, domain=DOMAIN, limitations=LIMITATIONS,
        original_declaration_verified=False, original_arm_abi_verified=False,
        hardware_verified=False, portable_ready=False, canonical_binding_pending=True,
        phase_timestamps=dict(replay_started_utc=start, replay_ended_utc=utc()),
        command=[sys.executable, "-B", *sys.argv],
        native_check_argv=["uc-library/.venv/bin/python", "-B",
                           str(Path(__file__).relative_to(ROOT)), "native",
                           "--fixture", str(args.fixture)],
        formatter_version=run([FORMAT[0], "--version"]).strip(),
        compiler_version=run([CXX[0], "--version"]).splitlines()[0],
        unicorn_version=__import__("unicorn").__version__,
        source_sha256={str(path): hash_file(path) for path in [SOURCE, HEADER, REPLAY, *CORE]},
        sources=sources, repository_sources=providers,
        oracle=dict(path=str(native.ELF), sha256=identity["elf_sha256"],
                    producer_sha256=hash_file(TESTS / "native.py")),
        producer_sha256=hash_file(__file__),
        ranges=[observations["original_range"]], vtable_words=observations["vtable_words"],
        fixture=dict(path=str(args.fixture), sha256=hash_file(args.fixture), cases=len(cases)),
        compiled_symbols=[definition],
        object=dict(path=str(args.object), sha256=hash_file(args.object)),
        executable=dict(path=str(args.exe), sha256=hash_file(args.exe)),
        integration=(dict(path=str(args.integration), sha256=hash_file(args.integration))
                     if args.integration else None),
        proposed_readiness=dict(ready=[], pending=[row]),
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(proof, indent=2) + "\n")


if __name__ == "__main__":
    main()
