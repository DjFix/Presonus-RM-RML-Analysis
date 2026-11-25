"""Local compile and bounded differential replay for the UC Element family."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

from native import CASES

ROOT = Path(__file__).resolve().parents[4]
PROJECT = Path("/home/rs/projects/opencs/ai-line-analysis")
BASE = Path(__file__).resolve().parent.relative_to(ROOT)
WORK = Path("temp/recovery-work/sqlite02-uc-element-local")
SOURCE = Path("uc-library/src/Presonus/UC/Element.cpp")
HEADER = Path("uc-library/include/presonus/uc/element.hpp")
META_SOURCE = Path("uc-library/src/Presonus/UC/MetaElement.cpp")
META_HEADER = Path("uc-library/include/presonus/uc/meta_element.hpp")
REPLAY = BASE / "Replay.cpp"
PROVIDERS = [META_HEADER, META_SOURCE, *[Path("third_party/ccl-framework/core/public") / name
              for name in ("corevector.h", "corestringbuffer.h", "corestringtraits.h", "coretypes.h")]]
FMT = "uc-library/.venv/bin/clang-format"
WRAP = ["-Wl,--wrap=_Znam", "-Wl,--wrap=_ZdaPv", "-Wl,--wrap=_ZdlPv", "-Wl,--wrap=_ZdlPvm"]
UNCERTAINTIES = {
    "is_empty": "Original return declaration is unencoded. Portable bool matches observed 0/1 predicate.",
    "get_meta_element": "Original pointer/reference and const return spelling are unencoded. Portable const reference preserves borrowed identity.",
    "get_index": "Original return declaration is unencoded. Portable int preserves signed -1 sentinel.",
    "add_child": "Original return declaration is unencoded. Portable void follows state-only behavior; ARM R0 carries path-dependent residue.",
    "find_child": "Original returned pointer qualification is unencoded. Portable Element* preserves the match or null.",
}
LIMITATIONS = [
    "Native app instructions execute; CCL CString64 default and Vector resize boundaries use independently executed pinned portable observations. Guest vector storage release is mediated at its exact call boundary.",
    "Original app Unknown initializes the native descriptor with intercepted ABI guard operations; the alternate guest identity is a byte copy. Portable metadata consists of genuine separately scoped values with callable factories.",
    "Verified native operator-delete calls unmap the relevant allocation at the PLT boundary. Portable wrappers forward to real delete and monitor real vector array release.",
    "Native failed resize retains the linked parent without inserting. Portable allocation failure throws and restores the detached child intentionally.",
    "Portable source model only; ARM binary layout, XML/parser, hardware, cycles and malformed trees are outside this scope.",
]


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def run(argv, capture=False):
    argv = list(map(str, argv))
    print("+", " ".join(argv), file=sys.stderr)
    return subprocess.run(argv, cwd=ROOT, text=True, check=True,
                          stdout=subprocess.PIPE if capture else None).stdout


def format_check():
    run([FMT, "--style=file", "--fallback-style=LLVM", "--dry-run", "--Werror",
         SOURCE, HEADER, META_SOURCE, META_HEADER, REPLAY])
    return run([FMT, "--version"], True).strip()


def compile_local(exe, obj):
    exe.parent.mkdir(parents=True, exist_ok=True)
    compiler = "/usr/bin/c++"
    flags = ["-std=c++17", "-g", "-O0", "-Ulinux", "-Iuc-library/include",
             "-isystem", "third_party/ccl-framework"]
    pairs = [(SOURCE, obj), (META_SOURCE, obj.with_name("MetaElement.o")),
             (REPLAY, obj.with_name("Replay.o"))]
    commands = [[compiler, *flags, "-MD", "-MF", output.with_suffix(".d"), "-c",
                 source, "-o", output] for source, output in pairs]
    commands.append([compiler, *[output for _, output in pairs], *WRAP, "-o", exe])
    for command in commands:
        run(command)
    outputs = [exe, *[part for _, output in pairs for part in (output, output.with_suffix(".d"))]]
    receipt = {"cwd": str(ROOT), "argv": [list(map(str, row)) for row in commands],
               "compiler_version": run([compiler, "--version"], True).strip(),
               "output_hashes": {str(part): digest(part) for part in outputs},
               "provider_hashes": {str(path): digest(path) for path in PROVIDERS}}
    exe.with_suffix(".compile.json").write_text(json.dumps(receipt, indent=2) + "\n")


def symbols(obj, contract):
    names = {row["original"]["mangled"] for row in contract["originals"]}
    found = [row for row in run(["nm", "--defined-only", obj], True).splitlines()
             if row.split()[-1] in names]
    assert len(found) == len(names)
    return found


def expected(variant, case):
    output = case["output"]
    if variant.endswith("construct"):
        result = [*output[:3], "empty", output[4]]
    elif variant.endswith("destroy"):
        result = [int(output["retained"]), int(output["receiver_vector_released"]), *output["free"]]
    elif variant == "add_child":
        count, capacity, parent, children = output
        if case["inputs"][1]:
            assert parent and count == case["inputs"][0]
            parent = False
        result = [count, capacity, int(parent), *children]
    else:
        result = [output]
    return list(map(str, result))


def replay(args, contract, task):
    assert args.firmware_root is not None
    fixture = read(args.fixture)
    assert fixture == json.loads(run([sys.executable, "-B", BASE / "native.py", args.context,
                                      args.firmware_root, args.exe], True))
    observations = []
    funcs = []
    uncertainty = UNCERTAINTIES.get(args.variant)
    ready = uncertainty is None
    domain = contract["task"]["review"]["domain"]
    sources = {str(path.relative_to("uc-library")): digest(path) for path in (SOURCE, HEADER)}
    repos = {str(path): digest(path) for path in PROVIDERS if path.parts[0] == "third_party"}
    for record in fixture:
        for case in record["cases"]:
            actual = run([args.exe.resolve(), args.variant, *[
                arg if arg is not None else "<null>" for arg in case["inputs"]]], True).split()
            assert actual == expected(args.variant, case), (case["inputs"], expected(args.variant, case), actual)
            observations.append({"role": record["role"], "inputs": case["inputs"], "observed": actual})
        funcs.append({"original_elf_sha256": record["elf_sha256"], "mangled": record["target"]["mangled"],
                      "original_address": record["target"]["address"], "domain": domain,
                      "sources": sources, "repository_sources": repos, "portable_ready": ready,
                      "cpp_compiled": True, "mangling_namespace_checked": True,
                      "declaration_uncertainties": [uncertainty] if uncertainty else [], "success": True})
    proof = {"version": 1, "task_id": task, "success": True, "domain": domain,
             "format_check_passed": True, "formatter_version": format_check(),
             "cpp_compiled": True, "mangling_namespace_checked": True,
             "cpp_differential_passed": True, "behavior_validation_passed": True,
             "portable_ready": ready, "functions": funcs,
             "proposed_readiness": {"ready": funcs if ready else [], "pending": funcs if not ready else []},
             "limitations": LIMITATIONS, "native": fixture, "native_replayed": True,
             "observations": observations, "argv": sys.argv,
             "symbols": symbols(args.object, contract), "binary_sha256": digest(args.exe),
             "object_sha256": digest(args.object), "fixture_sha256": digest(args.fixture),
             "provider_hashes": {str(path): digest(path) for path in PROVIDERS},
             "producer_sha256": digest(BASE / "check.py"), "oracle_sha256": digest(BASE / "native.py"),
             "portable_replay_sha256": digest(REPLAY)}
    if args.integration:
        proof["integration_proof_sha256"] = digest(args.integration)
    receipt = args.exe.with_suffix(".compile.json")
    if receipt.is_file():
        proof["local_build_receipt"] = read(receipt)
    if args.out:
        args.out.write_text(json.dumps(proof, indent=2) + "\n")
    print(f"{args.variant}: {len(observations)} ARM and portable cases passed")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=("format", "compile", "symbols", "replay"))
    p.add_argument("--variant", required=True, choices=CASES)
    for arg in ("exe", "object", "fixture", "context", "firmware-root", "integration", "out"):
        p.add_argument("--" + arg, type=Path)
    args = p.parse_args()
    task = "sqlite02_element_" + args.variant
    args.context = args.context or Path("temp/recovery-work/sqlite-issued/packet") / task / "CONTEXT.json"
    args.fixture = args.fixture or Path("uc-library/tests/recovery") / task / "fixtures.json"
    args.exe = args.exe or WORK / args.variant / "Replay"
    args.object = args.object or WORK / args.variant / "Element.o"
    if args.action == "format":
        print(format_check())
    elif args.action == "compile":
        compile_local(args.exe, args.object)
    elif args.action == "symbols":
        print(symbols(args.object, read(args.context)))
    else:
        replay(args, read(args.context), task)


if __name__ == "__main__":
    main()
