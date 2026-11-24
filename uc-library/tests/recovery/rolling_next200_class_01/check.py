"""Build and verify the portable talker state handler against fresh ARM observations."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess

import elftools
import unicorn

import native

ROOT = Path(__file__).resolve().parents[4]
TEST = Path(__file__).resolve().parent.relative_to(ROOT)
TASK = TEST.name
SCRATCH = ROOT / "temp/recovery-work" / TASK
SOURCE = Path("uc-library/src/Presonus/AVB/AvbComponent.cpp")
HEADER = Path("uc-library/include/presonus/avb/AvbComponent.hpp")
FORMAT = "uc-library/.venv/bin/clang-format"
COMPILER = "/usr/bin/c++"
LOCAL_SOURCES = [
    SOURCE,
    TEST / "Replay.cpp",
    Path("uc-library/src/Presonus/AVB/AvbComponentRouting.cpp"),
    Path("uc-library/src/Presonus/DICE/PacketClockGateway.cpp"),
    Path("uc-library/src/Presonus/UC/ServerComponent.cpp"),
]
APP_DEPENDENCIES = [
    HEADER,
    *LOCAL_SOURCES,
    Path("uc-library/include/presonus/avb/ComponentResource.hpp"),
    Path("uc-library/include/presonus/dice/packet_services.hpp"),
    Path("uc-library/include/presonus/uc/ServerComponent.hpp"),
]
CORE_DEPENDENCIES = [
    "third_party/ccl-framework/core/portable/corecomponent.cpp",
    "third_party/ccl-framework/core/portable/coreparams.cpp",
    "third_party/ccl-framework/core/system/coredebug.h",
    "third_party/ccl-framework/core/system/coretime.h",
    "third_party/ccl-framework/core/platform/shared/posix/coretime.posix.h",
]
SDK = Path(
    "/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/"
    "root-integration-01/upstream-core/sdk/lib"
)
ARCHIVES = {
    SDK / "libcorelib.a": "5a2c8bbb20d8d194ff4f5047118696afa918a046b01739c4257416044e83f5f3",
    SDK / "libpresonus_core_allocator.a": "69892fbcec9a50a140462982073c686a67ca4763dfb5dfa190534d022b78a40d",
}
DOMAIN = (
    "Twelve exact ARM function entries with six receiver/talker memory patterns "
    "and null/mapped arguments. Full receiver/talker pages unchanged, R0/R1/SP/FP/LR "
    "preserved, return to LR, only four local stack word writes, no calls. Portable "
    "replay uses live AvbComponent receivers with matched varied listener state, null "
    "and non-null opaque aligned talker address tokens, and fail-on-use service boundaries."
)
LIMITATIONS = [
    "Original return declaration remains unresolved. The C++ void signature is a source-port choice.",
    "The source-port method does not change the existing portable class vtable. Native slot and thunk evidence do not establish source declaration, slot, receiver adjustment or original layout.",
    "Scope is the exact direct entry body. No original thunk, dispatch, C++ lifetime, ARM ABI or hardware verification.",
    "Portable non-null arguments are aligned opaque storage addresses; the existing AvbTalker object is not constructed or dereferenced. The body never searches or reads the argument.",
]
COMMANDS = []


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(*argv, input=None):
    command = list(map(str, argv))
    print(json.dumps(command), flush=True)
    COMMANDS.append(command)
    environment = dict(os.environ)
    if SCRATCH.is_dir():
        environment["TMPDIR"] = str(SCRATCH)
    return subprocess.run(
        command, input=input, text=True, stdout=subprocess.PIPE, check=True,
        cwd=ROOT, env=environment
    ).stdout


def formatting():
    run(FORMAT, "--style=file", "--fallback-style=LLVM", "--dry-run", "--Werror",
        HEADER, SOURCE, TEST / "Replay.cpp")


def compile_local(executable, object_file):
    SCRATCH.mkdir(parents=True, exist_ok=True)
    for archive, digest in ARCHIVES.items():
        assert sha(archive) == digest, f"Local pinned Core archive changed: {archive}"
    objects = []
    for index, source in enumerate(LOCAL_SOURCES):
        output = object_file if index == 0 else SCRATCH / f"part{index}.o"
        run(COMPILER, "-std=c++17", "-O0", "-fno-rtti", "-Wno-multichar",
            "-ffunction-sections", "-fdata-sections", "-Iuc-library/include",
            "-Ithird_party/ccl-framework", "-c", source, "-o", output)
        objects.append(output)
    run(COMPILER, *objects, "-Wl,--gc-sections", *ARCHIVES,
        "-lz", "-lpthread", "-ldl", "-lm", "-o", executable)
    (SCRATCH / "local-compile.json").write_text(json.dumps({
        "argv": COMMANDS, "returncode": 0, "completed_utc": utc(),
        "object_sha256": sha(object_file), "executable_sha256": sha(executable),
    }, indent=2) + "\n")


def symbols(object_file):
    inventory = run("nm", "--defined-only", object_file)
    assert [line.split()[-1] for line in inventory.splitlines() if line.split()].count(native.NAME) == 1
    return inventory


def utc():
    return datetime.now(timezone.utc).isoformat()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["format", "compile", "symbols", "proof"])
    parser.add_argument("--exe", type=Path)
    parser.add_argument("--object", type=Path)
    parser.add_argument("--fixtures", type=Path, default=TEST / "fixtures.json")
    parser.add_argument("--integration", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.integration == Path("-"):
        args.integration = None
    executable = args.exe or SCRATCH / "replay"
    object_file = args.object or SCRATCH / "production.o"
    if args.mode == "compile":
        compile_local(executable, object_file)
        return
    if args.mode == "symbols":
        symbols(object_file)
        return
    formatting()
    if args.mode == "format":
        return
    if args.out is None:
        parser.error("proof requires --out")

    replay_started = utc()
    original = native.generate()
    assert json.loads(args.fixtures.read_text()) == original, "Fresh original replay differs"
    cases = original["cases"]
    results = run(executable.resolve(), input="".join(
        f"{case['seed']} {case['present']}\n" for case in cases
    )).splitlines()
    expected = [
        f"{int(case['receiver_unchanged'])} {int(case['talker_unchanged'])}"
        for case in cases
    ]
    assert results == expected, (expected, results)
    inventory = symbols(object_file)
    print(f"{len(cases)} fresh ARM and portable cases passed")
    app_hashes = {
        str(path.relative_to("uc-library")): sha(path) for path in APP_DEPENDENCIES
    }
    core_hashes = {path: sha(path) for path in CORE_DEPENDENCIES}
    fixture_artifacts = {
        str(path): sha(path) for path in (TEST / "native.py", TEST / "check.py", args.fixtures)
    }
    pending = dict(
        original_elf_sha256=native.SHA, mangled=native.NAME, sources=app_hashes,
        repository_sources=core_hashes, domain=DOMAIN, cpp_compiled=True,
        mangling_namespace_checked=True, portable_ready=False,
        declaration_uncertainties=LIMITATIONS, canonical_binding_pending=args.integration is None,
    )
    formatter = run(FORMAT, "--version").strip()
    compiler = run(COMPILER, "--version").splitlines()[0]
    implementation = {}
    for name in ("implementation-start", "implementation-end"):
        stamp = SCRATCH / (name + ".utc")
        if stamp.is_file():
            implementation[name] = stamp.read_text().strip()
    local_compile = None
    if args.exe is None:
        local_compile = json.loads((SCRATCH / "local-compile.json").read_text())
        assert local_compile["object_sha256"] == sha(object_file)
        assert local_compile["executable_sha256"] == sha(executable)
    proof = dict(
        version=1, task_id=TASK, domain=DOMAIN, limitations=LIMITATIONS,
        compiled=True, cpp_compiled=True, mangling_namespace_checked=True,
        compiled_mangled_names_matched=True, formatting_verified=True,
        cpp_differential_passed=True, native_behavior_verified=True,
        fresh_native_execution=True, original_declaration_verified=False,
        original_arm_abi_verified=False, hardware_verified=False, portable_ready=False,
        canonical_binding_pending=args.integration is None,
        case_count=len(cases), ranges=[original["range"]],
        native_observations=original, portable_observations=results,
        source_sha256={**{f"uc-library/{path}": digest for path, digest in app_hashes.items()},
                       **core_hashes, **fixture_artifacts},
        checks_executed=COMMANDS, local_compile=local_compile, compiler_version=compiler,
        formatter_version=formatter, unicorn_version=unicorn.__version__,
        pyelftools_version=elftools.__version__, compiled_symbols=inventory,
        object=dict(path=str(object_file), sha256=sha(object_file)),
        executable=dict(path=str(executable), sha256=sha(executable)),
        local_archives={str(path): sha(path) for path in ARCHIVES} if args.exe is None else {},
        integration=(dict(path=str(args.integration), sha256=sha(args.integration))
                     if args.integration else None),
        phase_timestamps={**implementation, "replay_started": replay_started, "replay_finished": utc()},
        proposed_readiness=dict(ready=[], pending=[pending]),
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(proof, indent=2) + "\n")


if __name__ == "__main__":
    main()
