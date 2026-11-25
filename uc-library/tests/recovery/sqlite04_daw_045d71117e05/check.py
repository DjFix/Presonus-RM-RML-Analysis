"""Build and replay the shared Slot/Folder port, with one proof per exact packet."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import unicorn

from native import observations

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent.relative_to(ROOT)
TASKS = Path("temp/recovery-work/sqlite-issued/packet")
SCRATCH = Path("temp/recovery-work/daw-slot-folder")
CANONICAL = Path("/home/rs/projects/opencs/ai-line-analysis")
SDK = CANONICAL / "temp/core-upstream/root-integration-01/upstream-core/sdk/lib"
SOURCES = [Path(f"uc-library/src/Presonus/DAWDevice{name}.cpp")
           for name in ("Slot", "Folder")]
HEADERS = [Path(f"uc-library/include/presonus/DAWDevice{name}.hpp")
           for name in ("Slot", "Folder")]
CLIENT = Path("uc-library/src/Presonus/UC/ClientComponent.cpp")
REPLAY = HERE / "Replay.cpp"
FORMATTER = "uc-library/.venv/bin/clang-format"
FORMAT = [FORMATTER, "--style=file", "--fallback-style=LLVM", "--dry-run",
          "--Werror", *SOURCES, *HEADERS, REPLAY]
CXX = ["/usr/bin/c++", "-std=c++20", "-fno-rtti", "-fno-sized-deallocation",
       "-Wall", "-Wextra", "-Wno-multichar", "-Ulinux",
       "-DCORE_USE_OPENSSL=1", "-pthread",
       "-Iuc-library/include", "-isystem", "third_party/ccl-framework"]
LIBRARIES = [SDK / part for part in ("libcorelib.a", "libpresonus_core_allocator.a",
                                    "libpresonus_png.a", "libpresonus_zlib.a")]
WRAP = "-Wl,--wrap=_ZdlPv,--wrap=_ZdlPvm"
EXE = SCRATCH / "replay"
OBJECTS = [SCRATCH / f"{source.stem}.o" for source in SOURCES]
LIMITATIONS = (
    "Portable source behavior only. Native object and virtual-table layouts, ARM ABI, "
    "exception paths, original unselected methods and hardware remain outside this domain.",
    "ARM replays map exact ELF PT_LOADs and use original application and Core routines. "
    "Native vector storage, parameter state and allocator addresses are arranged in emulated "
    "memory. libc strlen/strcmp and deallocation imports are bounded hooks. Deallocation "
    "revokes page access for the actual pointer supplied by the original routine. Linux "
    "runs the pinned Core source with actual heap allocation and wrapped forwarding deletes.",
    "Folder init requires tag zero, as on the native path. The native-only null child "
    "entry exercises the skip guard, using the equivalent non-null public CCL child list "
    "for host projection because Component::addChild requires a non-null child. "
    "Float-to-int replay uses finite values representable as signed int."
)
UNCERTAINTIES = {
    "6castToEi": "The native virtual cast returns receiver identity or null. "
                 "The portable provider prescribes void*; the exact original return spelling is unencoded.",
    "4initEv": "The original init return declaration is unencoded. The port uses void "
               "for its observed effects; the native caller does not consume a result.",
    "9getFolderEv": "Native returns the exact DAWDeviceFolder-type cast pointer. "
                    "The portable typed pointer does not establish the exact original return declaration.",
    "12getUsedCountEv": "Native returns a signed ARM word from float truncation and signed minimum. "
                        "The exact original C++ return type is unencoded; the port uses int.",
}


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


def run(argv):
    args = list(map(str, argv))
    print(json.dumps(args), flush=True)
    return subprocess.run(args, check=True, cwd=ROOT, text=True,
                          stdout=subprocess.PIPE).stdout


def build():
    SCRATCH.mkdir(parents=True, exist_ok=True)
    os.environ["TMPDIR"] = str(ROOT / SCRATCH)
    for src, obj in zip(SOURCES, OBJECTS, strict=True):
        run([*CXX, "-c", src, "-o", obj])
    run([*CXX, CLIENT, REPLAY, *OBJECTS, *LIBRARIES, WRAP,
         "-ldl", "-lssl", "-lcrypto", "-lm", "-o", EXE])


def verify_symbol(name):
    count = []
    for obj in OBJECTS:
        defined = run(["/usr/bin/nm", "--defined-only", obj]).splitlines()
        count += [dict(object=str(obj), line=line) for line in defined
                  if line.split()[-2:] == ["T", name]]
    assert len(count) == 1, (name, count)
    return count


def replay(exe, originals):
    projected_count = 0
    for row in originals:
        for case in row["cases"]:
            output = list(map(int, run([exe.resolve(), row["original"]["mangled"],
                                        *case["args"]]).split()))
            assert output == case["output"], (row["original"]["mangled"], case, output)
            projected_count += 1
    print(f"{projected_count} portable comparisons passed")
    return projected_count


def proof(task, context, fixture, proof_path):
    started = now()
    packet = json.loads(context.read_text())
    observed = observations(packet)
    assert observed == json.loads(fixture.read_text())["originals"]
    name = observed[0]["original"]["mangled"]
    matched = verify_symbol(name)
    run(FORMAT)
    count = replay(EXE, observed)
    declarations = [reason for suffix, reason in UNCERTAINTIES.items()
                    if name.endswith(suffix)]
    providers = {row["path"]: row["sha256"] for row in packet["task"]["review"]["providers"]
                 if row["path"].startswith("third_party/")}
    components = {str(path.relative_to("uc-library")): digest(path) for path in
                  (*SOURCES, *HEADERS, CLIENT, Path("uc-library/include/presonus/uc/ClientComponent.hpp"))}
    domain = packet["task"]["review"]["oracle_plan"]
    functions = []
    for item in observed:
        original = item["original"]
        row = dict(original_elf_sha256=original["elf"], original_address=original["address"],
                   firmware=original["firmware"], role=original["role"], mangled=name,
                   domain=domain, cpp_compiled=True, mangling_namespace_checked=True,
                   portable_ready=not declarations, sources=components, repository_sources=providers)
        if declarations:
            row["declaration_uncertainties"] = declarations
        functions.append(row)
    save(proof_path, dict(
        version=1, task_id=task, cpp_compiled=True, mangling_namespace_checked=True,
        cpp_differential_passed=True, formatting_verified=True, compiled=True,
        compiled_mangled_names_matched=True, fresh_native_execution=True,
        native_behavior_verified=True, original_declaration_verified=not declarations,
        original_arm_abi_verified=False, hardware_verified=False, portable_ready=not declarations,
        canonical_binding_pending=True, domain=domain, limitations=[*LIMITATIONS, *declarations],
        command=[sys.executable, "-B", *sys.argv],
        formatter_version=run([FORMATTER, "--version"]).strip(),
        compilation_version=run([CXX[0], "--version"]).splitlines()[0],
        phase_timestamps=dict(replay_started_utc=started, replay_ended_utc=now()),
        unicorn_version=unicorn.__version__, functions=functions, mangled_names=[name],
        ranges=observed, compiled_symbols=matched,
        proof_inputs={str(path): digest(path) for path in
                      (context, fixture, REPLAY, HERE / "native.py", HERE / "check.py")},
        producer_sha256=digest(__file__), sources=components, repository_sources=providers,
        fixture=dict(path=str(fixture), sha256=digest(fixture), cases=count),
        archives={str(path): digest(path) for path in LIBRARIES},
        executable=dict(path=str(EXE), sha256=digest(EXE)),
        proposed_readiness=dict(ready=functions if not declarations else [],
                                pending=functions if declarations else [])
    ))


def seal(context, fixture, proof_path, handoff_path):
    packet = json.loads(context.read_text())
    task = packet["task"]
    assert all(digest(row["path"]) == row["sha256"] for key in ("providers", "evidence")
               for row in task["review"][key])
    review_equivalence = task["review"]["equivalence"]
    assert digest(review_equivalence["path"]) == review_equivalence["sha256"]
    native = observations(packet)
    save(fixture, dict(version=1, engine=unicorn.__version__, originals=native))
    proof(task["id"], context, fixture, proof_path)
    artifacts = {}

    def bind(path, kind):
        artifacts[str(path)] = dict(path=str(path), sha256=digest(path), kind=kind)

    for path in (*SOURCES, *HEADERS):
        bind(path, "source")
    for key in ("providers", "evidence"):
        for row in task["review"][key]:
            bind(row["path"], key)
    bind(review_equivalence["path"], "evidence")
    bind(REPLAY, "test")
    bind(HERE / "native.py", "oracle")
    bind(HERE / "check.py", "replay")
    bind(fixture, "fixture")
    bind(proof_path, "proof")
    bind(context, "packet")
    name = native[0]["original"]["mangled"]
    originals = []
    for row in native:
        ident = row["original"]
        originals.append(dict(elf_sha256=ident["elf"], firmware=ident["firmware"],
                              role=ident["role"], mangled=ident["mangled"],
                              address=ident["address"], size=ident["size"],
                              section=ident["section"], section_name=ident["section_name"],
                              file_offset=ident["file_offset"], range_sha256=ident["range_sha256"]))
    check = ["uc-library/.venv/bin/python", "-B", str(HERE / "check.py")]
    save(handoff_path, dict(
        version=1, task_id=task["id"], namespace=task["namespace"], packet_manifest=str(context),
        artifacts=list(artifacts.values()), originals=originals,
        checks=[dict(kind=kind, argv=[*check, *args], timeout_seconds=90) for kind, args in (
            ("format", ["format"]), ("compile", ["compile"]), ("symbols", ["symbols", "--name", name]),
            ("replay", ["verify", "--context", str(context), "--fixture", str(fixture)]))],
        validation_domain=task["review"]["oracle_plan"],
        limitations=[*LIMITATIONS, *(reason for suffix, reason in UNCERTAINTIES.items() if name.endswith(suffix))],
        build_integration=dict(production_partition="common", production_sources=list(map(str, SOURCES)),
                               public_headers=list(map(str, HEADERS)),
                               source_compile_options=["-fno-sized-deallocation"],
                               test_executable="daw_device_slot_folder_replay", test_source=str(REPLAY),
                               test_link_options=[WRAP], test_link_dependencies=["common role archive", "pinned CCL"],
                               ctest_argv=[*check, "portable", "--exe", "$<TARGET_FILE:daw_device_slot_folder_replay>",
                                           "--fixture", str(fixture)])
    ))


def main():
    assert Path.cwd().resolve() == ROOT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("format", "compile", "symbols", "verify", "portable", "seal-all"))
    parser.add_argument("--name")
    parser.add_argument("--context", type=Path)
    parser.add_argument("--fixture", type=Path)
    parser.add_argument("--exe", type=Path, default=EXE)
    args = parser.parse_args()
    if args.mode == "format":
        run(FORMAT)
    elif args.mode == "compile":
        build()
    elif args.mode == "symbols":
        print(verify_symbol(args.name))
    elif args.mode == "portable":
        replay(args.exe, json.loads(args.fixture.read_text())["originals"])
    elif args.mode == "verify":
        observed = observations(json.loads(args.context.read_text()))
        assert observed == json.loads(args.fixture.read_text())["originals"]
        replay(args.exe, observed)
    else:
        run(FORMAT)
        build()
        for path in sorted(TASKS.glob("sqlite04_daw_*/CONTEXT.json")):
            name = path.parent.name
            candidate = Path("uc-library/candidates") / name
            fixture = Path("uc-library/tests/recovery") / name / "fixtures.json"
            seal(path, fixture, candidate / "worker-proof.json", candidate / "HANDOFF.json")


if __name__ == "__main__":
    main()
