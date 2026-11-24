"""Compare a Linux build of the portable getter against exact ARM observations."""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

import native

TASK = "rolling_literal_b84de2b18bf4"
LIBRARY = Path("uc-library")
TEST = LIBRARY / "tests/recovery" / TASK
SCRATCH = Path("temp/recovery-work") / (TASK + "-local")
SOURCES = (
    LIBRARY / "include/presonus/panel/GambitPanelRegistrar.hpp",
    LIBRARY / "src/Presonus/Panel/GambitPanelRegistrar.cpp",
    TEST / "Replay.cpp",
)
FORMATTER = LIBRARY / ".venv/bin/clang-format"
DOMAIN = (
    "Three direct original ARM calls with two receiver addresses and distinct read-only "
    "32-byte sentinels. The exact ARM range returns a stable mapped read-only word "
    "and NUL-terminated text, preserves receiver bytes and restores the frame. Four "
    "Linux calls on two concrete source objects compare text and pointer identity, "
    "including across one object's destruction. Group lookup observations for -1 "
    "through 16 are compared before and after the calls."
)
LIMITATIONS = [
    "The portable non-const member returns const char*. The original return declaration "
    "and character const qualification remain unresolved.",
    "ARM direct invocation uses opaque receiver sentinels. Original virtual dispatch, "
    "class layout, ARM ABI interoperability and physical serial use are outside this evidence.",
]


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def binding(path):
    return {"path": str(path), "sha256": digest(path)}


def run(*argv):
    command = [str(item) for item in argv]
    print(" ".join(command), flush=True)
    return subprocess.check_output(command, text=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("format", "compile", "symbols", "replay"))
    parser.add_argument("--fixture", type=Path, default=TEST / "fixtures.json")
    parser.add_argument("--exe", type=Path, default=SCRATCH / "Replay")
    parser.add_argument("--object", type=Path, default=SCRATCH / "Owner.o")
    parser.add_argument("--integration", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    start = datetime.now(timezone.utc).isoformat()
    if args.mode in ("format", "replay"):
        run(FORMATTER, "--style=file", "--fallback-style=LLVM", "--dry-run", "--Werror", *SOURCES)
    if args.mode == "format":
        return
    if args.mode == "compile":
        SCRATCH.mkdir(parents=True, exist_ok=True)
        flags = ("/usr/bin/c++", "-std=c++17", "-Wall", "-Wextra", "-Werror", "-O2",
                 "-Iuc-library/include")
        run(*flags, "-c", SOURCES[1], "-o", args.object)
        run(*flags, SOURCES[2], args.object, "-o", args.exe)
        return

    definitions = run("nm", "--defined-only", args.object).splitlines()
    matching = [line for line in definitions if line.split()[-2:] == ["T", native.MANGLED]]
    native.require(len(matching) == 1, "Exact scoped ELF definition missing from object")
    print(matching[0])
    if args.mode == "symbols":
        return

    fixture = json.loads(args.fixture.read_text())
    native.require((fixture["elf_sha256"], fixture["mangled"], fixture["range_sha256"]) ==
                   (native.ELF_HASH, native.MANGLED, native.BODY_HASH), "Fixture identity mismatch")
    cases = fixture["cases"]
    native.require(len(cases) == 3 and all(case["receiver_preserved"] for case in cases),
                   "Incomplete original domain")
    portable = run(args.exe.resolve())
    native.require(all(portable == case["literal"] + "\n" for case in cases),
                   "Original ARM and portable Linux text differ")
    row = {
        "original_elf_sha256": native.ELF_HASH,
        "original_address": native.ADDRESS,
        "mangled": native.MANGLED,
        "cpp_compiled": True,
        "mangling_namespace_checked": True,
        "portable_ready": False,
        "sources": {str(path.relative_to(LIBRARY)): digest(path) for path in SOURCES[:2]},
        "repository_sources": {},
        "domain": DOMAIN,
        "declaration_uncertainties": LIMITATIONS,
    }
    proof = {
        "version": 1, "task_id": TASK, "start_utc": start, "argv": sys.argv,
        "success": True, "format_check_passed": True, "behavior_validation_passed": True,
        **row, "limitations": LIMITATIONS, "functions": [dict(row, success=True)],
        "proposed_readiness": {"ready": [], "pending": [row]},
        "native": fixture, "native_case_count": len(cases), "portable_case_count": 4,
        "local_observation": portable.rstrip("\n"),
        "fixture": binding(args.fixture), "object": binding(args.object),
        "executable": binding(args.exe), "test": binding(SOURCES[2]), "symbol": matching[0],
        "producers": [binding(TEST / name) for name in ("native.py", "check.py")],
        "formatter_version": run(FORMATTER, "--version").strip(),
        "compiler_version": run("/usr/bin/c++", "--version").splitlines()[0],
        "canonical_binding_pending": args.integration is None,
        "end_utc": datetime.now(timezone.utc).isoformat(),
    }
    if args.integration:
        proof["integration"] = binding(args.integration)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(proof, indent=2) + "\n")
    print("PASS three ARM invocations and four Linux invocations")


if __name__ == "__main__":
    main()
