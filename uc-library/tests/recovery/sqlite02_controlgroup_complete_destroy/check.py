"""Compile, inspect and compare ControlGroup destructor observations."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
PROJECT = Path("/home/rs/projects/opencs/ai-line-analysis")
BUILD = PROJECT / "temp/core-upstream/root-integration-01"
SDK = BUILD / "upstream-core/sdk"
BASE = Path(__file__).resolve().parent.relative_to(ROOT)
WORK = Path("temp/recovery-work/sqlite02-controlgroup-local")
SOURCE = Path("uc-library/src/surface_panel/ControlGroup.cpp")
HEADER = Path("uc-library/include/presonus/surface_panel/ControlGroup.hpp")
CONTROL = Path("uc-library/src/Presonus/Panel/control.cpp")
PROVIDERS = [CONTROL, Path("uc-library/include/presonus/panel/control.hpp"),
             Path("third_party/ccl-framework/core/public/corevector.h")]
REPLAY = BASE / "Replay.cpp"
FORMATTER = "uc-library/.venv/bin/clang-format"
ORDER = {"D0": "deleting", "D1": "complete", "D2": "base"}
DOMAIN = (
    "Each firmware executes the exact ControlGroup variant after original constructors "
    "and add calls, with empty, null-only, singleton and two-Control interspersed-null "
    "rosters. The ARM oracle captures ordered real Control D0 entries, guest heap unmaps "
    "reached by exact delete call sites, receiver lifetime and object writes. Linux "
    "compares actual Control and receiver deallocations, and checks borrowed and injected "
    "state using the pinned CCL vector and live provider Controls."
)
LIMITATIONS = [
    "The native delete PLT boundary unmaps each allocated guest object page; the ARM "
    "libc allocator and its internals are outside this domain.",
    "Control parameters are null and the timer roster is empty. Only exact base Control "
    "instances are exercised; parameter callbacks and other derived Control providers "
    "are outside this domain.",
    "Portable source ownership is explicit per slot. Original layout, vtable ABI, "
    "ARM binary interoperability and hardware operation are outside this domain.",
]


def run(argv, *, capture=False):
    argv = [str(arg) for arg in argv]
    print("+", " ".join(argv), file=sys.stderr)
    return subprocess.run(argv, cwd=ROOT, check=True, text=True,
                          stdout=subprocess.PIPE if capture else None).stdout


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def task_id(variant):
    return f"sqlite02_controlgroup_{ORDER[variant]}_destroy"


def fixture_for(variant):
    return Path("uc-library/tests/recovery") / task_id(variant) / "fixtures.json"


def context_for(variant):
    return Path("temp/recovery-work/sqlite-issued/packet") / task_id(variant) / "CONTEXT.json"


def format_check():
    run([FORMATTER, "--style=file", "--fallback-style=LLVM", "--dry-run", "--Werror",
         HEADER, SOURCE, REPLAY])
    return run([FORMATTER, "--version"], capture=True).strip()


def compile_local(executable, obj):
    executable.parent.mkdir(parents=True, exist_ok=True)
    flags = ["c++", "-std=c++17", "-g", "-O0", "-pthread", "-Ulinux",
             "-DNDEBUG=1", "-DCORE_USE_OPENSSL=1", "-DPRESONUS_HAS_UPSTREAM_CORE=1",
             "-Iuc-library/include", "-Ithird_party/ccl-framework",
             "-isystem", SDK / "include/presonus-core-5"]
    control_obj = obj.with_name("control.o")
    run([*flags, "-c", SOURCE, "-o", obj])
    run([*flags, "-c", CONTROL, "-o", control_obj])
    libraries = [BUILD / "libpresonus_uc.a", SDK / "lib/libcorelib.a",
                 SDK / "lib/libpresonus_core_allocator.a",
                 SDK / "lib/libpresonus_png.a", SDK / "lib/libpresonus_zlib.a",
                 "-lssl", "-lcrypto", "-ldl", "-lm"]
    run([*flags, REPLAY, obj, control_obj, *libraries, "-Wl,--wrap=_ZdlPv",
         "-Wl,--wrap=_ZdlPvm", "-o", executable])


def symbols(obj):
    lines = run(["nm", "--defined-only", obj], capture=True).splitlines()
    found = {}
    for variant in ORDER:
        symbol = f"_ZN8Presonus5Panel12ControlGroup{variant}Ev"
        found[variant], = [line for line in lines if line.split()[-1] == symbol]
    return found


def replay(args):
    fixture = json.loads(args.fixture.read_text())
    if args.firmware_root is not None:
        native = run([sys.executable, "-B", BASE / "native.py", args.context or context_for(args.variant),
                      args.firmware_root], capture=True)
        assert json.loads(native) == fixture
    result = []
    function_results = []
    source_hashes = {str(path.relative_to("uc-library")): digest(path)
                     for path in (HEADER, SOURCE)}
    repository_hashes = {str(path): digest(path) for path in PROVIDERS
                         if not path.is_relative_to("uc-library")}
    for firmware in fixture:
        for case in firmware["cases"]:
            actual = run([args.exe.resolve(), args.variant, *case["entries"]], capture=True).split()
            expected = ["retained" if case["receiver_mapped"] else "freed", *case["free_order"]]
            assert actual == expected, (firmware["role"], case["entries"], expected, actual)
            result.append({"role": firmware["role"], "entries": case["entries"],
                           "observed": actual, "expected": expected})
        function_results.append({
            "original_elf_sha256": firmware["elf_sha256"],
            "mangled": firmware["target"]["mangled"],
            "original_address": firmware["target"]["address"],
            "cpp_compiled": True, "mangling_namespace_checked": True,
            "behavior_validation_passed": True, "portable_ready": True,
            "sources": source_hashes, "repository_sources": repository_hashes,
            "domain": DOMAIN, "success": True,
        })
    proof = {"version": 1, "task_id": task_id(args.variant), "success": True,
             "domain": DOMAIN, "limitations": LIMITATIONS, "functions": function_results,
             "proposed_readiness": {"ready": function_results, "pending": []},
             "cpp_differential_passed": True, "portable_ready": True,
             "provider_hashes": {str(path): digest(path) for path in PROVIDERS},
             "cpp_compiled": True, "mangling_namespace_checked": True,
             "format_check_passed": True, "behavior_validation_passed": True,
             "formatter_version": format_check(),
             "fixture": {"path": str(args.fixture), "sha256": digest(args.fixture)},
             "oracle_sha256": digest(BASE / "native.py"),
             "producer_sha256": digest(BASE / "check.py"),
             "portable_replay_sha256": digest(REPLAY),
             "actual_argv": sys.argv, "binary_sha256": digest(args.exe),
             "object_sha256": digest(args.object), "symbols": symbols(args.object),
             "native": fixture, "observations": result,
             "native_replayed": args.firmware_root is not None}
    if args.integration:
        proof["integration_proof_sha256"] = digest(args.integration)
    if args.out:
        args.out.write_text(json.dumps(proof, indent=2) + "\n")
    print(f"{args.variant}: {len(result)} ARM and portable lifecycle comparisons passed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["format", "compile", "symbols", "replay"])
    parser.add_argument("--variant", choices=ORDER, default="D1")
    parser.add_argument("--exe", type=Path)
    parser.add_argument("--object", type=Path)
    parser.add_argument("--fixture", type=Path)
    parser.add_argument("--firmware-root", type=Path)
    parser.add_argument("--context", type=Path)
    parser.add_argument("--integration", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    args.exe = args.exe or WORK / args.variant / "Replay"
    args.object = args.object or WORK / args.variant / "ControlGroup.o"
    if args.action == "format":
        print(format_check())
    elif args.action == "compile":
        compile_local(args.exe, args.object)
    elif args.action == "symbols":
        print(json.dumps(symbols(args.object), indent=2))
    else:
        args.fixture = args.fixture or fixture_for(args.variant)
        replay(args)


if __name__ == "__main__":
    main()
