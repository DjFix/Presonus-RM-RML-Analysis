"""Compile local replay or validate a canonical registrar object and executable."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
TASK = HERE.name
GLOBAL = TASK.endswith("global_response")
BUILD = ROOT / "temp/recovery-work/registrar-worker08" / TASK
HEADER = "include/presonus/surface_panel/ControlHelpers.hpp"
COMMANDS = "src/Presonus/Panel/ControlRegistrarCommands.cpp"
HELPERS = "src/surface_panel/ControlHelpers.cpp"
PRIMARY = HELPERS if GLOBAL else COMMANDS
SOURCES = [
    HEADER, COMMANDS, HELPERS, "include/presonus/panel/uart_message.hpp",
    "include/presonus/panel/protocol_comm.hpp",
]
CORE = [
    "third_party/ccl-framework/core/portable/corecomponent.h",
    "third_party/ccl-framework/core/portable/coreparams.h",
]
FORMATTED = [*(ROOT / "uc-library" / path for path in (HEADER, PRIMARY)), HERE / "Replay.cpp"]
FORMATTER = ROOT / "uc-library/.venv/bin/clang-format"
DOMAIN = (
    "Both firmware ARM callbacks execute with all 256 byte-1 selector values. "
    "The zero case enters the actual native handleVersion range with unchanged "
    "receiver, original message and type. Portable replay compares version, "
    "message preservation, initialization and bound-null port state."
    if GLOBAL else
    "Each firmware ARM scan enters the verified writeDualMsg slot exactly once "
    "with its original receiver and a stack-local four-byte message. Portable "
    "replay observes virtual dispatch, same message reference at the actual "
    "provider and borrowed capture port, copied bytes, and the bound-null no-send path."
)
LIMITS = [
    "The original ordinary return declaration is unresolved. Portable void "
    "records the observed side effect and does not establish original ARM ABI, "
    "layout or full vtable equivalence.",
    ("Concrete ControlRegistrar callback and handleVersion provider only. "
     "No other native registrar class or hardware lifecycle is exercised."
     if GLOBAL else
     "Native execution stops writeDualMsg at an offline capture stub on the "
     "verified original slot. The real portable provider runs. "
     "No UART hardware, native transport or original provider ABI is validated."),
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(argv, commands, payload=None):
    argv = list(map(str, argv))
    start = datetime.now(timezone.utc)
    result = subprocess.run(argv, input=payload, text=True, capture_output=True, cwd=ROOT)
    commands.append({
        "argv": argv, "start_utc": start.isoformat(),
        "end_utc": datetime.now(timezone.utc).isoformat(), "returncode": result.returncode,
    })
    if result.returncode:
        print(result.stdout, result.stderr)
        result.check_returncode()
    return result.stdout


def compile_local(commands):
    BUILD.mkdir(parents=True, exist_ok=True)
    flags = [
        "/usr/bin/c++", "-std=c++17", "-O2", "-fno-rtti", "-fno-lto",
        "-ffunction-sections", "-fdata-sections", "-Wno-multichar", "-Ulinux",
        "-Iuc-library/include", "-Ithird_party/ccl-framework",
    ]
    paths = [ROOT / "uc-library" / source for source in (COMMANDS, HELPERS)]
    paths.append(HERE / "Replay.cpp")
    objects = [BUILD / (path.stem + ".o") for path in paths]
    for path, obj in zip(paths, objects):
        run(flags + ["-c", path, "-o", obj], commands)
    run(["/usr/bin/c++", *objects, "-Wl,--gc-sections", "-o", BUILD / "replay"], commands)


def symbols(path, originals, commands):
    listing = run(["nm", "--defined-only", path], commands)
    expected = {row["target"]["mangled"] for row in originals}
    found = [line for line in listing.splitlines() if line.split()[-1:] and line.split()[-1] in expected]
    assert len(found) == len(expected)
    return found


def compare(exe, originals, commands):
    cases = originals[0]["cases"]
    if GLOBAL:
        payload = "".join(
            " ".join(map(str, [case["input"]["type"], *case["input"]["bytes"]])) + "\n"
            for case in cases
        )
        found = [int(line) for line in run([exe], commands, payload).splitlines()]
        for original in originals:
            assert [case["input"] for case in original["cases"]] == [case["input"] for case in cases]
            assert found == [case["version"] for case in original["cases"]]
        return len(cases)
    found = list(map(int, run([exe], commands).split()))
    for original in originals:
        assert len(original["cases"]) == 1
        observed = original["cases"][0]["calls"]
        assert len(observed) == 1 and observed[0]["bytes"] == found
    return 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["compile", "symbols", "proof"])
    parser.add_argument("--fixtures", type=Path, default=HERE / "fixtures.json")
    parser.add_argument("--exe", type=Path, default=BUILD / "replay")
    object_name = Path(PRIMARY).stem + ".o"
    parser.add_argument("--object", type=Path, default=BUILD / object_name)
    parser.add_argument("--integration", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    commands = []
    if args.mode == "compile":
        compile_local(commands)
        (BUILD / "compile.json").write_text(json.dumps(commands, indent=2) + "\n")
        return
    fixture = json.loads(args.fixtures.read_text())
    originals = fixture["originals"]
    compiled = symbols(args.object, originals, commands)
    if args.mode == "symbols":
        print("\n".join(compiled))
        return
    format_version = run([FORMATTER, "--version"], commands).strip()
    run([FORMATTER, "--style=file", "--fallback-style=LLVM", "--dry-run", "--Werror", *FORMATTED], commands)
    cases = compare(args.exe, originals, commands)
    source_hashes = {path: sha(ROOT / "uc-library" / path) for path in SOURCES}
    core_hashes = {path: sha(ROOT / path) for path in CORE}
    pending = [
        dict(row["target"], demangled=run(["c++filt", row["target"]["mangled"]], commands).strip(),
             cpp_compiled=True, mangling_namespace_checked=True, portable_ready=False,
             original_function_verified=False, hardware_verified=False,
             sources=source_hashes, repository_sources=core_hashes,
             validation_domain=DOMAIN, declaration_uncertainties=LIMITS)
        for row in originals
    ]
    proof = {
        "task_id": TASK,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "validation_domain": DOMAIN, "limitations": LIMITS,
        "sources": source_hashes, "repository_sources": core_hashes,
        "compiled_original_mangled_names_matched": True, "compiled_symbols": compiled,
        "cpp_differential_passed": True, "portable_case_count": cases,
        "native_case_count": sum(len(row["cases"]) for row in originals),
        "native": [{key: value for key, value in row.items() if key != "cases"} for row in originals],
        "unicorn_version": fixture["unicorn_version"],
        "fixture_sha256": sha(args.fixtures), "producer_sha256": sha(Path(__file__)),
        "test_sources": {str((HERE / "Replay.cpp").relative_to(ROOT)): sha(HERE / "Replay.cpp")},
        "native_producer_sha256": sha(HERE / "native.py"),
        "formatting": {"version": format_version, "passed": True, "sources": {
            str(path.relative_to(ROOT)): sha(path) for path in FORMATTED
        }},
        "binary_bindings": {str(path): sha(path) for path in (args.exe, args.object)},
        "commands": commands, "proposed_readiness": {"ready": [], "pending": pending},
    }
    if args.integration:
        proof["integration"] = {"path": str(args.integration), "sha256": sha(args.integration)}
    if not args.out:
        parser.error("proof mode requires --out")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(proof, indent=2) + "\n")
    print(f"{TASK}: {cases} portable cases matched both firmwares")


if __name__ == "__main__":
    main()
