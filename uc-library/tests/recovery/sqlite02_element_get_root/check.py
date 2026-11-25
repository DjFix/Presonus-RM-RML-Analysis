"""Compile and compare Element methods against bounded original executions."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

from unicorn import __version__ as unicorn_version

ROOT = Path(__file__).resolve().parents[4]
BASE = Path(__file__).resolve().parent.relative_to(ROOT)
WORK = Path("temp/recovery-work/element-foundation-projection")
SOURCE = Path("uc-library/src/Presonus/UC/Element.cpp")
HEADER = Path("uc-library/include/presonus/uc/element.hpp")
META = Path("uc-library/src/Presonus/UC/MetaElement.cpp")
META_HEADER = Path("uc-library/include/presonus/uc/meta_element.hpp")
CCL = Path("third_party/ccl-framework")
ATTR = CCL / "core/portable/coreattributes.cpp"
BUFFER = CCL / "core/public/corebuffer.cpp"
ALLOCATOR = CCL / "core/malloc/coremalloc.cpp"
PROVIDERS = [META, META_HEADER, ATTR, BUFFER, ALLOCATOR,
             CCL / "core/portable/coreattributes.h",
             CCL / "core/public/corevector.h", CCL / "core/public/corestringbuffer.h"]
OLD_ORACLE = BASE.parent / "sqlite02_element_complete_construct/native.py"
FMT = "uc-library/.venv/bin/clang-format"
LIMITATIONS = [
    "Original Element bodies and Metadata predicate execute in Unicorn. Pinned CCL "
    "CString64 and Vector observations mediate verified native call boundaries. "
    "Host strcmp, fixture attribute virtual slots, an override root slot, and delete "
    "PLT are intercepted. No original CCL implementation was reconstructed.",
    "Portable attributes use the pinned in-memory provider, with pool disabled in the "
    "standalone check. ARM attribute class layout, full XML loading and hardware are outside scope.",

]
UNCERTAINTIES = {
    "get_root": "Original pointer type and qualification are unencoded. Portable Element* preserves observed null and override identity.",
    "is_element_class": "Original return declaration is unencoded. Portable bool preserves the observed 0/1 predicate.",
    "load_local_attributes": "Original return declaration is unencoded. Portable bool preserves the observed successful flag.",
    "save_local_attributes": "Original return declaration is unencoded. Portable bool preserves the observed successful flag.",
}


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def run(argv):
    argv = list(map(str, argv))
    print("+", " ".join(argv), file=sys.stderr)
    return subprocess.check_output(argv, cwd=ROOT, text=True)


def format_check():
    run([FMT, "--style=file", "--fallback-style=LLVM", "--dry-run", "--Werror",
         HEADER, SOURCE, BASE / "Replay.cpp"])
    return run([FMT, "--version"]).strip()


def compile_local(exe, obj):
    obj.parent.mkdir(parents=True, exist_ok=True)
    compiler = "/usr/bin/c++"
    flags = ["-std=c++17", "-Ulinux", "-Iuc-library/include", "-isystem", CCL,
             "-DCORE_ATTRIBUTE_POOL_DISABLED", "-DCORE_DISABLE_NEW_OPERATOR=1"]
    pairs = [(path, obj.with_name(path.stem + ".o"))
             for path in (SOURCE, META, BASE / "Replay.cpp", ATTR, BUFFER, ALLOCATOR)]
    commands = [[compiler, *flags, "-MD", "-MF", output.with_suffix(".d"),
                 "-c", path, "-o", output] for path, output in pairs]
    commands.append([compiler, *[output for _, output in pairs], "-o", exe])
    for command in commands:
        run(command)
    exe.with_suffix(".compile.json").write_text(json.dumps({
        "argv": [list(map(str, row)) for row in commands],
        "compiler_version": run([compiler, "--version"]).splitlines()[0],
        "output_hashes": {str(path): digest(path) for path in
                          (exe, *[output for _, output in pairs])},
    }, indent=2) + "\n")


def symbols(obj, packet):
    expected = {row["original"]["mangled"] for row in packet["originals"]}
    rows = [line for line in run(["nm", "--defined-only", obj]).splitlines()
            if len(line.split()) == 3 and line.split()[2] in expected]
    assert {row.split()[2] for row in rows} == expected
    return rows


def compare(exe, variant, case):
    inputs, result = case["inputs"], case["output"]
    actual = run([exe.resolve(), variant, *[part if part is not None else "<null>" for part in inputs]])
    if variant.endswith("attributes"):
        status, name = result
        assert actual == f"{status} @{name}", (case, actual)
    else:
        assert int(actual) == result, (case, actual)
    return actual


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("format", "compile", "symbols", "replay"))
    parser.add_argument("--variant", required=True, choices=UNCERTAINTIES)
    parser.add_argument("--exe", type=Path, default=WORK / "Replay")
    parser.add_argument("--object", type=Path, default=WORK / "Element.o")
    parser.add_argument("--firmware-root", type=Path, default=ROOT)
    for field in ("fixture", "context", "out", "integration"):
        parser.add_argument("--" + field, type=Path)
    args = parser.parse_args()
    task = "sqlite02_element_" + args.variant
    args.context = args.context or Path("temp/recovery-work/sqlite-issued/packet") / task / "CONTEXT.json"
    args.fixture = args.fixture or BASE.parent / task / "fixtures.json"
    packet = json.loads(args.context.read_text())
    assert packet["task"]["id"] == task
    if args.action == "format":
        print(format_check())
    elif args.action == "compile":
        compile_local(args.exe, args.object)
    elif args.action == "symbols":
        print(*symbols(args.object, packet), sep="\n")
    else:
        fixture = json.loads(args.fixture.read_text())
        assert fixture == json.loads(run([sys.executable, "-B", BASE / "native.py",
                                          args.context, args.firmware_root, args.exe]))
        observed = [{"role": item["original"]["role"], "inputs": case["inputs"],
                     "portable": compare(args.exe, args.variant, case)}
                    for item in fixture for case in item["cases"]]
        domain = packet["task"]["review"]["domain"]
        sources = {str(p.relative_to("uc-library")): digest(p) for p in (SOURCE, HEADER)}
        repos = {str(p): digest(p) for p in PROVIDERS if p.parts[0] == "third_party"}
        functions = [dict(original_elf_sha256=item["original"]["elf"],
                          mangled=item["original"]["mangled"],
                          original_address=item["original"]["address"], domain=domain,
                          sources=sources, repository_sources=repos, portable_ready=False,
                          cpp_compiled=True, mangling_namespace_checked=True,
                          declaration_uncertainties=[UNCERTAINTIES[args.variant]], success=True)
                     for item in fixture]
        proof = dict(version=1, task_id=task, success=True, domain=domain,
                     format_check_passed=True, cpp_compiled=True, portable_ready=False,
                     mangling_namespace_checked=True, cpp_differential_passed=True,
                     behavior_validation_passed=True, native_replayed=True,
                     formatter_version=format_check(), unicorn_version=unicorn_version,
                     functions=functions, proposed_readiness=dict(ready=[], pending=functions),
                     native=fixture, observations=observed, case_count=len(observed),
                     argv=sys.argv, symbols=symbols(args.object, packet),
                     binary_sha256=digest(args.exe), object_sha256=digest(args.object),
                     fixture_sha256=digest(args.fixture), limitations=LIMITATIONS,
                     provider_hashes={str(p): digest(p) for p in PROVIDERS},
                     producer_sha256=digest(BASE / "check.py"),
                     oracle_sha256=digest(BASE / "native.py"),
                     support_oracle_sha256=digest(OLD_ORACLE),
                     portable_replay_sha256=digest(BASE / "Replay.cpp"))
        if args.integration:
            proof["integration_proof_sha256"] = digest(args.integration)
        receipt = args.exe.with_suffix(".compile.json")
        if receipt.is_file():
            proof["local_build_receipt"] = json.loads(receipt.read_text())
        if args.out:
            args.out.write_text(json.dumps(proof, indent=2) + "\n")
        print(f"{task}: {len(observed)} original and portable cases passed.")


if __name__ == "__main__":
    main()
