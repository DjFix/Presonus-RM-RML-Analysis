"""Compile and differentially replay MetaElement::isClass on Linux."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
PROJECT = Path("/home/rs/projects/opencs/ai-line-analysis")
BASE = Path(__file__).resolve().parent.relative_to(ROOT)
TASK = "sqlite02_metaelement_is_class"
WORK = Path("temp/recovery-work/sqlite02-metaelement-local/build-v1")
SOURCE = Path("uc-library/src/Presonus/UC/MetaElement.cpp")
HEADER = Path("uc-library/include/presonus/uc/meta_element.hpp")
PROVIDER = Path("third_party/ccl-framework/core/public/coretypes.h")
REPLAY = BASE / "Replay.cpp"
EVIDENCE = Path("temp/recovery-work/rolling-c001-20261124/selection/rolling-owner-selection-current/"
                "sqlite-only-cycle02/next-wave/META_ELEMENT_TYPED_PROVIDER_EVIDENCE.json")
CTX = Path("temp/recovery-work/sqlite-issued/packet") / TASK / "CONTEXT.json"
SYMBOL = "_ZNK8Presonus2UC11MetaElement7isClassEPKc"
FMT = "uc-library/.venv/bin/clang-format"
DOMAIN = ("25 crossed pairs per original using null, empty, case-distinct, different and "
          "equal-content distinct borrowed name/argument identities; no receiver mutation.")
UNCERTAINTY = "The native predicate returns 0/1; the exact original return declaration is not encoded. Portable bool is provisional."
LIMITATIONS = [
    "Real ARM isClass instructions and exact strcmp PLT dispatch were observed with the host libc provider.",
    "The portable metadata fields have the observed semantic roles. Original layout, standalone constructor, Unknown, factory execution and hardware remain outside this test.",
]


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def run(command, capture=False):
    argv = list(map(str, command))
    print("+", " ".join(argv), file=sys.stderr)
    return subprocess.run(argv, cwd=ROOT, check=True, text=True,
                          stdout=subprocess.PIPE if capture else None).stdout


def format_check():
    run([FMT, "--style=file", "--fallback-style=LLVM", "--dry-run", "--Werror", SOURCE, HEADER, REPLAY])
    return run([FMT, "--version"], True).strip()


def compile_local(exe, obj):
    exe.parent.mkdir(parents=True, exist_ok=True)
    flags = ["/usr/bin/c++", "-std=c++17", "-g", "-O0", "-Ulinux",
             "-Iuc-library/include", "-isystem", "third_party/ccl-framework"]
    pairs = [(SOURCE, obj), (REPLAY, obj.with_name("Replay.o"))]
    commands = [[*flags, "-MD", "-MF", output.with_suffix(".d"), "-c", source, "-o", output]
                for source, output in pairs]
    commands.append([flags[0], *[output for _, output in pairs], "-o", exe])
    for command in commands:
        run(command)
    outputs = [exe, *[part for _, output in pairs for part in (output, output.with_suffix(".d"))]]
    exe.with_suffix(".compile.json").write_text(json.dumps({
        "cwd": str(ROOT), "argv": [list(map(str, line)) for line in commands],
        "compiler_version": run([flags[0], "--version"], True).strip(),
        "output_hashes": {str(p): digest(p) for p in outputs},
        "provider_hashes": {str(PROVIDER): digest(PROVIDER)}}, indent=2) + "\n")


def check_symbol(obj):
    checked, = [line for line in run(["nm", "--defined-only", obj], True).splitlines()
                if line.split()[-1] == SYMBOL]
    return checked


def replay(args):
    fixture = json.loads(args.fixture.read_text())
    native = json.loads(run([sys.executable, "-B", BASE / "native.py", args.context,
                             args.firmware_root, args.evidence], True))
    assert native == fixture
    functions, cases = [], []
    for record in native:
        for case in record["cases"]:
            actual = run([args.exe.resolve(), *[value if value is not None else "<null>"
                                               for value in case["inputs"]]], True).strip()
            assert actual == str(case["output"]), (case["inputs"], actual)
            cases.append({"role": record["role"], "inputs": case["inputs"], "result": actual})
        functions.append({"original_elf_sha256": record["elf_sha256"], "mangled": SYMBOL,
                          "original_address": record["target"]["address"], "domain": DOMAIN,
                          "origins": [record["role"]], "cpp_compiled": True,
                          "mangling_namespace_checked": True, "portable_ready": False,
                          "sources": {str(p.relative_to("uc-library")): digest(p) for p in (SOURCE, HEADER)},
                          "repository_sources": {str(PROVIDER): digest(PROVIDER)},
                          "declaration_uncertainties": [UNCERTAINTY], "success": True})
    report = {
        "version": 1, "task_id": TASK, "success": True, "domain": DOMAIN,
        "cpp_compiled": True, "mangling_namespace_checked": True, "format_check_passed": True,
        "formatter_version": format_check(), "cpp_differential_passed": True,
        "behavior_validation_passed": True, "portable_ready": False, "functions": functions,
        "proposed_readiness": {"ready": [], "pending": functions}, "limitations": LIMITATIONS,
        "observations": cases, "native": native, "native_replayed": True, "argv": sys.argv,
        "symbol": check_symbol(args.object), "object_sha256": digest(args.object),
        "binary_sha256": digest(args.exe), "fixture_sha256": digest(args.fixture),
        "producer_sha256": digest(BASE / "check.py"), "oracle_sha256": digest(BASE / "native.py"),
        "portable_replay_sha256": digest(REPLAY), "typed_evidence_sha256": digest(args.evidence),
    }
    if args.integration:
        report["integration_proof_sha256"] = digest(args.integration)
    receipt = args.exe.with_suffix(".compile.json")
    if receipt.is_file():
        report["local_build_receipt"] = json.loads(receipt.read_text())
    if args.out:
        args.out.write_text(json.dumps(report, indent=2) + "\n")
    print(f"{len(cases)} ARM and portable comparisons passed")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=("format", "compile", "symbols", "replay"))
    p.add_argument("--exe", type=Path, default=WORK / "Replay")
    p.add_argument("--object", type=Path, default=WORK / "MetaElement.o")
    p.add_argument("--context", type=Path, default=CTX)
    p.add_argument("--fixture", type=Path, default=BASE / "fixtures.json")
    p.add_argument("--firmware-root", type=Path, default=PROJECT)
    p.add_argument("--evidence", type=Path, default=EVIDENCE)
    p.add_argument("--integration", type=Path)
    p.add_argument("--out", type=Path)
    args = p.parse_args()
    if args.action == "format":
        print(format_check())
    elif args.action == "compile":
        compile_local(args.exe, args.object)
    elif args.action == "symbols":
        print(check_symbol(args.object))
    else:
        replay(args)


if __name__ == "__main__":
    main()
