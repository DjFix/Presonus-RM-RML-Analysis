"""Build the current portable lifecycle sources and compare projected native traces."""
import argparse
import datetime
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys

from native import OBJ, CTRL, PROP, generate


LIBRARY = Path("uc-library")
BASE = LIBRARY / "src/Presonus"
HEADERS = LIBRARY / "include/presonus"
SOURCES = (
    BASE / "LinkableComponent.cpp",
    BASE / "DspComponent.cpp",
    BASE / "Mixer/AudioComponent.cpp",
)
SOURCE_HEADERS = (
    HEADERS / "LinkableComponent.hpp",
    HEADERS / "DspComponent.hpp",
    HEADERS / "mixer/AudioComponent.hpp",
)
CONTROLLER_INPUTS = (
    BASE / "Dsp/Controller.cpp",
    HEADERS / "dsp/Controller.hpp",
    HEADERS / "dsp/IController.hpp",
)
PROVIDERS = Path("third_party/ccl-framework/core")
PROVIDER_SOURCES = (
    PROVIDERS / "portable/coreattributes.cpp",
    PROVIDERS / "portable/coreattributes.h",
    PROVIDERS / "portable/corecomponent.cpp",
    PROVIDERS / "portable/corecomponent.h",
    PROVIDERS / "public/coreproperty.h",
    PROVIDERS / "public/corebuffer.h",
)
FORMATTER = LIBRARY / ".venv/bin/clang-format"
CONTROLLER = BASE / "Dsp/Controller.cpp"
HERE = Path("uc-library/tests/recovery/cycle21_g09_s01")
BUILD = Path("temp/recovery-work/cycle21_g09/providers")
ARCHIVES = (
    BUILD / "libpresonus_uc.a",
    BUILD / "libcorelib.a",
    BUILD / "libpresonus_core_allocator.a",
    BUILD / "libpresonus_private_glibc29.a",
)
FLAGS = [
    "c++", "-std=c++20", "-O0", "-g", "-UNDEBUG", "-Wno-multichar",
    "-Iuc-library/include", "-Ithird_party/ccl-framework",
]


def run(argv, **kwargs):
    print(json.dumps([str(v) for v in argv]), flush=True)
    return subprocess.run(argv, check=True, text=True, **kwargs)


def build(out):
    out.mkdir(exist_ok=True, parents=True)
    env = {**os.environ, "TMPDIR": str(out.resolve())}
    objects = []
    for source in (*SOURCES, CONTROLLER, HERE / "Replay.cpp"):
        obj = out / f"{source.stem}.o"
        deallocation = ["-fno-sized-deallocation"] if source in SOURCES[:2] else []
        run([*FLAGS, *deallocation, "-c", source, "-o", obj], env=env)
        objects.append(obj)
    for archive in ARCHIVES:
        print(f"{sha256(archive.read_bytes()).hexdigest()} {archive}")
    run(
        ["c++", *objects, "-Wl,--start-group", *ARCHIVES, "-Wl,--end-group",
         "-ldl", "-lpthread", "-lz", "-lm", "-o", out / "replay"],
        env=env,
    )


def primary_index(slot):
    return 0 if slot <= 3 else 1 if slot <= 6 else 2


def symbols(obj, fixture):

    rows = run(["nm", "--defined-only", obj], capture_output=True).stdout.splitlines()
    matches = [row for row in rows if row.split()[-1] == fixture["original"]["mangled"]]
    if len(matches) != 1:
        raise ValueError(f"Missing or ambiguous compiled symbol in {obj}: {fixture['original']}")
    print(matches[0])
    return matches[0]


def expected_trace(slot, case):
    selected = {
        "attributes", "component", "receiver_delete", "controller_release",
        "controller_delete", "property_release", "property_delete",
    }
    if slot in (7, 8):
        calls = [event for event in case["events"] if event[0] == "set_target"]
        assert len(calls) == 1
        _, _, controller, target, word04, member = calls[0]
        assert controller == CTRL and target == PROP and member == target
        assert case["state"]["receiver"][2:] == [CTRL, PROP]
        assert case["state"]["controller"] == [word04, PROP]
        return [f"set_target {word04} {int(target == PROP)}"]
    for event in case["events"]:
        if event[0] == "linkable_destruct" and slot >= 4:
            assert event[-1] == 0
        if event[0] == "attributes":
            assert event[2] == OBJ + 0x90
        if event[0] == "component":
            assert event[2] == OBJ
    return [event[0] for event in case["events"] if event[0] in selected]


def replay(executable, slot, fixture):
    executable = executable.resolve()
    for case in fixture["cases"]:
        out = run(
            [executable, str(slot), str(int(case["has_controller"])), str(case["id"])],
            capture_output=True,
        ).stdout.splitlines()
        if slot in (7, 8):
            out = out[:out.index("constructed")]
        elif slot in (9, 10):
            out = out[out.index("begin_destructor") + 1:]
        expected = expected_trace(slot, case)
        if out != expected:
            raise ValueError(f"Case {case['id']}: observed {out}, expected {expected}")
        print(out)
    print(f"{len(fixture['cases'])} native/projected portable lifecycle cases matched")


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def row_inputs(slot):
    end = primary_index(slot) + 1
    sources = [*SOURCES[:end], *SOURCE_HEADERS[:end]]
    if slot >= 4:
        sources.extend(CONTROLLER_INPUTS)
    return sources


def proposal(slot, fixture, domain):
    original = fixture["original"]
    owners = (
        "LinkableComponent original complete layout, base interfaces and cleanup exception declaration",
        "DspComponent original complete declaration, inheritance and controller-ownership interface",
        "AudioComponent original complete declaration and constructor/destructor unwind contract",
    )
    return {"ready": [], "pending": [{
        "original_elf_sha256": original["elf"],
        "mangled": original["mangled"],
        "cpp_compiled": True,
        "mangling_namespace_checked": True,
        "cpp_differential_passed": True,
        "portable_ready": False,
        "declaration_uncertainties": [owners[primary_index(slot)]],
        "validation_domain": domain,
        "sources": {str(path.relative_to(LIBRARY)): digest(path) for path in row_inputs(slot)},
        "repository_sources": {str(path): digest(path) for path in PROVIDER_SOURCES},
    }]}


def default_domain(slot):
    if slot <= 3:
        return ("Owned Linkable provider state. Attributes cleanup precedes "
                "Component cleanup; D0 deallocates the receiver. Borrowed host state survives.")
    if slot <= 6:
        return ("Null and present Controller for the selected exact Dsp destructor. "
                "Release and provider cleanup order, receiver deallocation for D0, "
                "and independently checked borrowed host controller.")
    if slot <= 8:
        return ("Four IDs (0, 314159, -7, INT_MIN), distinct live Controller provider "
                "identities, identifier before setTarget, exact target and final binding.")
    return ("Two distinct live Controller provider identities. Property release "
            "and deallocation precede controller release and deallocation and CCL cleanup.")


def check_unsized_delete(obj, name):
    disassembly = run(
        ["objdump", "-dr", f"--disassemble={name}", obj], capture_output=True
    ).stdout
    if not any(line.split()[-1].startswith("_ZdlPv-") for line in disassembly.splitlines()
               if line.split()):
        raise ValueError("Deleting destructor has no unsized operator-delete relocation")
    return disassembly


def native_check(task, fixture):
    if generate(task) != fixture:
        raise ValueError("Exact native replay changed")
    print(f"{len(fixture['cases'])} exact ARM cases matched recorded trace")


def canonical(slot, task, fixture, args):
    if not args.exe or not args.object:
        raise ValueError("Both supplied canonical executable and OBJECT file are required")
    if args.integration == Path("-") and args.out == Path("-"):
        args.integration = args.out = None
    if bool(args.integration) != bool(args.out):
        raise ValueError("Supply both integration and output for a fresh canonical proof")
    files = [*SOURCES, *SOURCE_HEADERS, HERE / "Replay.cpp"]
    run([FORMATTER, "--style=file", "--fallback-style=LLVM", "--dry-run", "--Werror", *files])
    compiled_symbol = symbols(args.object, fixture)
    deletion = check_unsized_delete(args.object, fixture["original"]["mangled"]) if slot in (3, 6) else None
    if args.integration:
        receipt = json.loads(args.integration.read_text())
        if receipt.get("platform") != "linux" or receipt.get("ctest_passed") is not True:
            raise ValueError("Passed canonical Linux integration receipt required")
        for source in (*row_inputs(slot), HERE / "Replay.cpp", HERE / "check.py",
                       HERE / "native.py", args.fixture):
            if receipt["files"].get(str(source.resolve().relative_to(LIBRARY.resolve()))) != digest(source):
                raise ValueError(f"Current input absent from Linux integration: {source}")
        integration_hash = digest(args.integration)
    native_check(task, fixture)
    replay(args.exe, slot, fixture)
    if args.out:
        if digest(args.integration) != integration_hash:
            raise ValueError("Canonical integration receipt changed during replay")
        domain = default_domain(slot)
        binding = lambda path: {"path": str(path.resolve()), "sha256": digest(path)}
        data = {
            "version": 1, "task_id": task, "success": True,
            "cpp_compiled": True, "mangling_namespace_checked": True,
            "cpp_differential_passed": True, "format_check_passed": True,
            "portable_ready": False, "validation_domain": domain,
            "fixture": binding(args.fixture), "native_case_count": len(fixture["cases"]),
            "native_ranges": [{"original": fixture["original"], "section": fixture["section"],
                               "file_offset": fixture["file_offset"], "sha256": fixture["range_sha256"]}],
            "compiled_symbol": compiled_symbol, "d0_object_disassembly": deletion,
            "object": binding(args.object), "executable": binding(args.exe),
            "integration": binding(args.integration),
            "producer": binding(HERE / "check.py"), "native_producer": binding(HERE / "native.py"),
            "formatter": run([FORMATTER, "--version"], capture_output=True).stdout.strip(),
            "format_files": {str(path): digest(path) for path in files},
            "repository_sources": {str(path): digest(path) for path in PROVIDER_SOURCES},
            "proposed_readiness": proposal(slot, fixture, domain),
            "executed_argv": [sys.executable, *sys.argv],
            "proof_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        with args.out.open("x") as stream:
            json.dump(data, stream, indent=2)
            stream.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["compile", "symbols", "native", "replay", "canonical"])
    parser.add_argument("--slot", required=True, type=int, choices=range(1, 11))
    parser.add_argument("--fixture", required=True, type=Path)
    parser.add_argument("--exe", "--executable", dest="exe", type=Path)
    parser.add_argument("--object", type=Path)
    parser.add_argument("--integration", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    task = f"cycle21_g09_s{args.slot:02d}"
    out = Path("temp/recovery-work/cycle21_g09") / task
    fixture = json.loads(args.fixture.read_text())
    if args.action == "compile":
        build(out)
    elif args.action == "symbols":
        obj = out / (SOURCES[primary_index(args.slot)].stem + ".o")
        symbols(obj, fixture)
        if args.slot in (3, 6):
            check_unsized_delete(obj, fixture["original"]["mangled"])
    elif args.action == "native":
        native_check(task, fixture)
    elif args.action == "replay":
        replay(args.exe or out / "replay", args.slot, fixture)
    elif args.action == "canonical":
        canonical(args.slot, task, fixture, args)


if __name__ == "__main__":
    main()
