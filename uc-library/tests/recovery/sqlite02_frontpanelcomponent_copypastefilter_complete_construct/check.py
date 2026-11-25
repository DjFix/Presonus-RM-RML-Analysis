"""Compile, inspect and compare CopyPasteFilter lifecycle and load observations."""
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
WORK = Path("temp/recovery-work/sqlite02-copypastefilter-local")
SOURCE = Path("uc-library/src/Presonus/Panel/FrontPanelComponent.cpp")
HEADER = Path("uc-library/include/presonus/panel/FrontPanelComponent.hpp")
PROVIDERS = [Path("third_party/ccl-framework/core/portable/corestorage.h"),
             Path("third_party/ccl-framework/core/portable/coretypeinfo.h"),
             Path("third_party/ccl-framework/core/public/coretypes.h"),
             Path("uc-library/include/presonus/mixer/ChannelComponent.hpp")]
REPLAY = BASE / "Replay.cpp"
FORMATTER = "uc-library/.venv/bin/clang-format"
ORDER = {"C1": "complete_construct", "C2": "base_construct",
         "D1": "complete_destroy", "D2": "base_destroy", "load": "should_load"}
LIFECYCLE = ("C1", "C2", "D1", "D2")
DOMAIN = (
    "The exact original RM mixer target and original storage-filter RTTI/vtable "
    "are verified before execution. Each lifecycle body runs at two receiver addresses "
    "and writes only the original dispatch pointer. Portable complete and derived "
    "lifecycles check actual CCL storage-filter dispatch, tagged construction, "
    "object guards and storage release by the owning caller. For shouldLoad, "
    "compare original shouldSave dispatch and returned predicates over 19 typed cases "
    "with null/name/parameter, controller absence, non-channel and channel tag boundaries."
)
LIMITATIONS = [
    "The pinned CCL base adds ITypedObject::castTo and a different portable vtable. "
    "Original ARM object layout, binary interoperability and hardware are outside this domain.",
    "The ARM parameter getter and C++ RTTI runtime boundary are intercepted with independently "
    "queried typed portable inputs. The native application shouldLoad and shouldSave instructions "
    "execute, but firmware Core and ABI runtime code are outside this test.",
    "The checked destructor variants preserve receiver storage. No deleting destructor is claimed.",
]


def run(argv, *, capture=False):
    argv = [str(arg) for arg in argv]
    print("+", " ".join(argv), file=sys.stderr)
    return subprocess.run(argv, cwd=ROOT, check=True, text=True,
                          stdout=subprocess.PIPE if capture else None).stdout


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def task_id(variant):
    return f"sqlite02_frontpanelcomponent_copypastefilter_{ORDER[variant]}"


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
    flags = ["-std=c++17", "-g", "-O0", "-pthread", "-Ulinux", "-ffunction-sections",
             "-fdata-sections", "-DNDEBUG=1", "-DCORE_USE_OPENSSL=1",
             "-DPRESONUS_HAS_UPSTREAM_CORE=1", "-Iuc-library/include",
             "-Ithird_party/ccl-framework", "-isystem", SDK / "include/presonus-core-5"]
    libraries = [BUILD / "libpresonus_rm_components.a", SDK / "lib/libcorelib.a",
                 SDK / "lib/libpresonus_core_allocator.a", SDK / "lib/libpresonus_png.a",
                 SDK / "lib/libpresonus_zlib.a", Path("/usr/lib/x86_64-linux-gnu/libssl.so"),
                 Path("/usr/lib/x86_64-linux-gnu/libcrypto.so"),
                 BUILD.parent / "external-dev/usr/lib/x86_64-linux-gnu/libdns_sd.so",
                 BUILD / "private-glibc29-provider/libpresonus_private_glibc29.a"]
    hashes = {str(path): digest(path) for path in libraries}
    replay_object = obj.with_name("Replay.o")
    compiler = "/usr/bin/c++"
    commands = [
        [compiler, *flags, "-MD", "-MF", obj.with_suffix(".d"), "-c", SOURCE, "-o", obj],
        [compiler, *flags, "-MD", "-MF", replay_object.with_suffix(".d"),
         "-c", REPLAY, "-o", replay_object],
        [compiler, "-pthread", "-Wl,--gc-sections", obj, replay_object, *libraries,
         "-ldl", "-lm", "-o", executable],
    ]
    for command in commands:
        run(command)
    assert hashes == {str(path): digest(path) for path in libraries}
    definitions = symbols(obj)
    references = run(["nm", "-u", replay_object], capture=True).splitlines()
    referenced = {line.split()[-1] for line in references if line.strip()}
    assert {line.split()[-1] for line in definitions.values()} <= referenced
    outputs = [obj, obj.with_suffix(".d"), replay_object, replay_object.with_suffix(".d"),
               executable]
    receipt = {"cwd": str(ROOT), "argv": [[str(x) for x in command] for command in commands],
               "provider_hashes": hashes, "output_hashes": {str(path): digest(path) for path in outputs},
               "replay_referenced_targets": sorted(set(referenced) &
                                                  {line.split()[-1] for line in definitions.values()}),
               "compiler_version": run([compiler, "--version"], capture=True).strip()}
    executable.with_suffix(".compile.json").write_text(json.dumps(receipt, indent=2) + "\n")


def symbols(obj):
    lines = run(["nm", "--defined-only", obj], capture=True).splitlines()
    prefix = "N8Presonus5Panel19FrontPanelComponent15CopyPasteFilter"
    wanted = {variant: f"_Z{prefix}{variant}Ev" for variant in LIFECYCLE}
    wanted["load"] = f"_ZNK{prefix[1:]}10shouldLoadEiPKcPv"
    found = {}
    for variant, symbol in wanted.items():
        found[variant], = [line for line in lines if line.split()[-1] == symbol]
    return found


def replay(args):
    fixture = json.loads(args.fixture.read_text())
    if args.firmware_root is not None:
        native = run([sys.executable, "-B", BASE / "native.py", args.context or context_for(args.variant),
                      args.firmware_root, args.exe], capture=True)
        assert json.loads(native) == fixture
    result = []
    function_results = []
    source_hashes = {str(path.relative_to("uc-library")): digest(path)
                     for path in (HEADER, SOURCE)}
    repository_hashes = {str(path): digest(path) for path in PROVIDERS
                         if not path.is_relative_to("uc-library")}
    for firmware in fixture:
        for case in firmware["observations"]:
            if args.variant == "load":
                actual = run([args.exe.resolve(), "load", *case["inputs"]], capture=True).strip()
                expected = str(case["output"]["result"])
            else:
                actual = run([args.exe.resolve(), args.variant], capture=True).strip()
                assert case["output"]["dispatch_initialized"] and case["output"]["receiver_retained"]
                expected = "dispatch-initialized receiver-retained"
            assert actual == expected, (case["inputs"], expected, actual)
            result.append({"role": firmware["role"], "inputs": case["inputs"],
                           "observed": actual, "expected": expected})
        if args.variant != "load":
            assert run([args.exe.resolve(), "tagged"], capture=True).strip() == expected
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
    compile_receipt = args.exe.with_suffix(".compile.json")
    if compile_receipt.is_file():
        proof["local_build_receipt"] = json.loads(compile_receipt.read_text())
    if args.integration:
        proof["integration_proof_sha256"] = digest(args.integration)
    if args.out:
        args.out.write_text(json.dumps(proof, indent=2) + "\n")
    print(f"{args.variant}: {len(result)} ARM and portable lifecycle comparisons passed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["format", "compile", "symbols", "replay"])
    parser.add_argument("--variant", choices=ORDER, default="C1")
    parser.add_argument("--exe", type=Path)
    parser.add_argument("--object", type=Path)
    parser.add_argument("--fixture", type=Path)
    parser.add_argument("--firmware-root", type=Path)
    parser.add_argument("--context", type=Path)
    parser.add_argument("--integration", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    args.exe = args.exe or WORK / args.variant / "Replay"
    args.object = args.object or WORK / args.variant / "FrontPanelComponent.o"
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
