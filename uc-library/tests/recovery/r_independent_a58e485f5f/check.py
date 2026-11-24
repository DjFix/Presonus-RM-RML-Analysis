"""Compile the scoped port and compare its respective ARM observations."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

from native import execute

ROOT = Path(__file__).resolve().parents[4]
TESTS = Path(__file__).resolve().parent.relative_to(ROOT)
TASK = TESTS.name
LOCAL = TASK != "rolling_client_notify"
SCRATCH = Path("temp/recovery-work/rolling-uc-local-client") / TASK
BASE = Path("/home/rs/projects/opencs/ai-line-analysis")
WAVE = Path("temp/recovery-work/rolling-c001-20261124")
SNAPSHOT = BASE / WAVE / "packeting/next-independent/snapshot"
SDK = BASE / "temp/core-upstream/root-integration-01/upstream-core/sdk/lib"
CXX = ["/usr/bin/c++", "-std=c++20", "-fno-rtti", "-Wall", "-Wextra",
       "-Wno-multichar", "-Ulinux", "-DCORE_USE_OPENSSL=1", "-pthread",
       "-Iuc-library/include", "-isystem", "third_party/ccl-framework"]
SUPPORT = [
    "uc-library/src/Presonus/UC/ServerLifetime.cpp",
    "uc-library/src/Presonus/UC/ServerMetadata.cpp",
] if LOCAL else ["uc-library/src/Presonus/UC/MessageAttributes.cpp"]
NAME = "LocalServer" if LOCAL else "ClientComponent"
SOURCE = Path("uc-library/src/Presonus/UC") / (NAME + ".cpp")
HEADER = Path("uc-library/include/presonus/uc") / ("server.hpp" if LOCAL else NAME + ".hpp")
PROVIDERS = [
    "uc-library/include/presonus/uc/server_registrar.hpp",
    "uc-library/include/presonus/uc/event_dispatcher.hpp",
] if LOCAL else ["uc-library/include/presonus/uc/message_attributes.hpp"]
CORE = [f"third_party/ccl-framework/core/{name}" for name in (
    ("public/corestringbuffer.h", "public/corevector.h") if LOCAL else
    ("portable/corecomponent.h", "portable/corecomponent.cpp",
     "portable/coreattributes.h", "portable/coreattributes.cpp")
)]
EVIDENCE = WAVE / (
    f"selection/r-stream/independent-owners/{TASK.removeprefix('r_independent_')}-local-server.json"
    if LOCAL else "selection/c001-owner-recovery/ELF_CLASS_EVIDENCE.json")
REPLAY = TESTS / "Replay.cpp"
FORMAT = ["uc-library/.venv/bin/clang-format", "--style=file", "--fallback-style=LLVM",
          "--dry-run", "--Werror", SOURCE, HEADER, REPLAY]
DOMAIN = (
    "Both exact role ELF constructor bodies with zero, one, high-bit and all-bits IDs and null or borrowed handler. "
    "ARM captures direct provider order and arguments, vptr and the identifier, handler and registration writes. "
    "Portable replay links actual Server construction and metadata providers and checks initialized owning state, "
    "typed handler identity, copied metadata including bounded strings, retained descriptor endpoints, and both host mangles."
    if LOCAL else
    "Seven independent ARM receiver and payload patterns per exact ELF, corresponding +48 vtable slots, "
    "stack-only accesses and unchanged input/receiver bytes. Seven actual CCL-backed component instances and "
    "const MessageAttributes inputs exercise the portable notify without changing selected payload or component state.")
LIMITATIONS = (
    ["Native provider bodies are stubbed at verified application entry addresses in this replay; the actual portable "
     "Server, CCL storage and setInfo implementations are exercised separately. Native lifecycle equivalence, private "
     "field declarations, ARM ABI and hardware behavior are outside the validated domain."]
    if LOCAL else
    ["Portable void return is a source choice. Original return declaration, private layout, full vtable, lifecycle "
     "equivalence, ARM ABI and hardware behavior remain unresolved. ARM receiver and payload memory are initialized "
     "stand-ins; the real portable CCL base and payload provide the separate typed execution."])


def utc():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(args):
    command = list(map(str, args))
    print(json.dumps(command), flush=True)
    return subprocess.run(command, cwd=ROOT, check=True, text=True,
                          stdout=subprocess.PIPE).stdout


def verify_symbols(obj, names):
    defined = run(["/usr/bin/nm", "--defined-only", obj]).splitlines()
    definitions = []
    for name in names:
        match = [line for line in defined if line.split()[-1:] == [name]]
        assert len(match) == 1 and match[0].split()[-2] == "T", (name, defined)
        definitions.append(match[0])
    return definitions


def compile_local(exe, obj):
    SCRATCH.mkdir(parents=True, exist_ok=True)
    os.environ["TMPDIR"] = str(ROOT / SCRATCH)
    core = [SDK / file for file in ("libcorelib.a", "libpresonus_core_allocator.a",
                                    "libpresonus_png.a", "libpresonus_zlib.a")]
    commands = [[*CXX, "-c", SOURCE, "-o", obj],
                [*CXX, REPLAY, *SUPPORT, obj, *core,
                 "-ldl", "-lssl", "-lcrypto", "-lm", "-o", exe]]
    for argv in commands:
        run(argv)


def observations():
    evidence = json.loads(EVIDENCE.read_text())
    rows = evidence["originals"] if LOCAL else [
        row for row in evidence if "ClientComponent6notify" in row["original"]["mangled"]]
    assert len(rows) == 2
    return [execute(row, SNAPSHOT) for row in rows]


def main():
    assert Path.cwd().resolve() == ROOT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", nargs="?", default="proof", choices=["format", "compile", "symbols", "native", "proof"])
    parser.add_argument("--exe", type=Path, default=SCRATCH / "replay")
    parser.add_argument("--object", type=Path, default=SCRATCH / "production.o")
    parser.add_argument("--fixture", type=Path, default=TESTS / "fixtures.json")
    parser.add_argument("--integration", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.mode == "format":
        run(FORMAT)
        return
    if args.mode == "compile":
        compile_local(args.exe, args.object)
        return
    fixture = json.loads(args.fixture.read_text())
    names = [fixture["originals"][0]["target"]["mangled"]]
    if LOCAL:
        name = names[0]
        names = [name.replace("LocalServerC2E", "LocalServerC1E"),
                 name.replace("LocalServerC1E", "LocalServerC2E")]
    if args.mode == "symbols":
        print(*verify_symbols(args.object, names), sep="\n")
        return
    start = utc()
    observed = observations()
    assert observed == fixture["originals"]
    print("Fresh original ARM executions:", sum(len(row["cases"]) for row in observed))
    if args.mode == "native":
        return
    assert args.out is not None
    run(FORMAT)
    match = verify_symbols(args.object, names)
    lines = run([args.exe.resolve()]).splitlines()
    for row in observed:
        assert lines == [case["output"] for case in row["cases"]], (lines, row)
    print("Portable executable comparisons:", len(lines) * len(observed))
    sources = {str(Path(path).relative_to("uc-library")): digest(path)
               for path in (SOURCE, HEADER, *SUPPORT, *PROVIDERS)}
    providers = {path: digest(path) for path in CORE}
    ready, pending = [], []
    for observation in observed:
        target = observation["target"]
        row = dict(original_elf_sha256=target["original_elf_sha256"], mangled=target["mangled"],
                   original_address=target["address"], cpp_compiled=True,
                   mangling_namespace_checked=True, portable_ready=LOCAL,
                   domain=DOMAIN, sources=sources, repository_sources=providers)
        if LOCAL:
            ready.append(row)
        else:
            row["declaration_uncertainties"] = LIMITATIONS
            pending.append(row)
    proof = dict(
        version=1, task_id=TASK, cpp_compiled=True, mangling_namespace_checked=True,
        cpp_differential_passed=True, formatting_verified=True, compiled=True,
        compiled_mangled_names_matched=True, fresh_native_execution=True,
        native_behavior_verified=True, domain=DOMAIN, limitations=LIMITATIONS,
        original_declaration_verified=LOCAL, original_arm_abi_verified=False,
        hardware_verified=False, portable_ready=LOCAL, canonical_binding_pending=True,
        phase_timestamps=dict(replay_started_utc=start, replay_ended_utc=utc()),
        command=[sys.executable, "-B", *sys.argv],
        formatter_version=run([FORMAT[0], "--version"]).strip(),
        compilation_version=run([CXX[0], "--version"]).splitlines()[0],
        unicorn_version=fixture["engine"],
        source_sha256={str(path): digest(path) for path in (SOURCE, HEADER, REPLAY, *SUPPORT, *PROVIDERS, *CORE)},
        sources=sources, repository_sources=providers, ranges=observed,
        oracle=dict(producer_sha256=digest(TESTS / "native.py"), evidence_sha256=digest(EVIDENCE),
                    frozen_elf_root=str(SNAPSHOT)),
        producer_sha256=digest(__file__),
        fixture=dict(path=str(args.fixture), sha256=digest(args.fixture), cases=len(lines) * len(observed)),
        compiled_symbols=match, object=dict(path=str(args.object), sha256=digest(args.object)),
        executable=dict(path=str(args.exe), sha256=digest(args.exe)),
        integration=(dict(path=str(args.integration), sha256=digest(args.integration)) if args.integration else None),
        functions=ready + pending, mangled_names=[row["mangled"] for row in ready + pending],
        proposed_readiness=dict(ready=ready, pending=pending),
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(proof, indent=2) + "\n")


if __name__ == "__main__":
    main()
