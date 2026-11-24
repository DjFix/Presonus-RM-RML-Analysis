"""Check exact mangling and replay fresh original ARM observations against Linux C++."""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

import native

TASK = "sqlite01_gambit_panel_tags"
TEST = Path("uc-library/tests/recovery") / TASK
SCRATCH = Path("temp/recovery-work") / TASK
HEADER = Path("uc-library/include/presonus/panel/GambitPanelRegistrar.hpp")
SOURCE = Path("uc-library/src/Presonus/Panel/GambitPanelRegistrar.cpp")
REPLAY = TEST / "Replay.cpp"
FORMAT = ("uc-library/.venv/bin/clang-format", "--style=file", "--fallback-style=LLVM",
          "--dry-run", "--Werror", HEADER, SOURCE, REPLAY)
COMPILER = "/usr/bin/c++"
DOMAIN = (
    "200 direct original ARM calls and 200 portable Linux calls spanning two receivers, 20 "
    "group values (0–16, -1 and signed extrema) and five initial count values. "
    "Every call returned null and preserved count and its canaries. Native instruction/data "
    "hooks observed the full exact method and stack-only accesses."
)
DECLARATIONS = [
    "The portable return type const int* follows RoguePanelRegistrar; the original return "
    "declaration, pointee type and const qualification remain unresolved.",
    "Original layout, inheritance, lifecycle and virtual dispatch remain unresolved. "
    "ARM calls used mapped opaque receiver memory; Linux used two actual portable objects.",
]
LIMITATIONS = DECLARATIONS + ["ARM binary interoperability and hardware behavior were outside the replay."]


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def bind(path):
    return {"path": str(path), "sha256": digest(path)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("format", "compile", "symbols", "replay"))
    parser.add_argument("--fixture", default=TEST / "fixtures.json", type=Path)
    parser.add_argument("--object", default=SCRATCH / "Owner.o", type=Path)
    parser.add_argument("--exe", default=SCRATCH / "Replay", type=Path)
    parser.add_argument("--elf", default=native.ELF_PATH, type=Path)
    parser.add_argument("--integration", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    started = datetime.now(timezone.utc).isoformat()
    commands = []

    def run(*argv, stdin=None):
        command = [str(arg) for arg in argv]
        commands.append(command)
        print(command, flush=True)
        return subprocess.check_output(command, input=stdin, text=True)

    if args.mode in ("format", "replay"):
        run(*FORMAT)
    if args.mode == "format":
        return
    if args.mode == "compile":
        SCRATCH.mkdir(parents=True, exist_ok=True)
        flags = (COMPILER, "-std=c++17", "-Wall", "-Wextra", "-Werror", "-O2",
                 "-Iuc-library/include")
        run(*flags, "-c", SOURCE, "-o", args.object)
        run(*flags, REPLAY, args.object, "-o", args.exe)
        return

    definitions = run("/usr/bin/nm", "--defined-only", args.object).splitlines()
    symbols = [line for line in definitions if line.split()[-2:] == ["T", native.MANGLED]]
    native.require(len(symbols) == 1, "Missing exact scoped ELF definition")
    print(symbols[0])
    if args.mode == "symbols":
        return

    fixture = json.loads(args.fixture.read_text())
    observed = native.observe(args.elf)
    native.require(observed == fixture, "Fresh original observations differ from the fixture")
    cases = observed["cases"]
    native.require(all(row["return_word"] == 0 and row["count_before"] == row["count_after"]
                       for row in cases), "Original return/count contract changed")
    inputs = "".join(f'{row["group"]} {row["count_before"]} {index % 2}\n'
                     for index, row in enumerate(cases))
    output = run(args.exe.resolve(), stdin=inputs).splitlines()
    expected = [f'{int(row["return_word"] != 0)} {row["count_after"]} {0xCADFBEDA} {0xDABEDFAC}'
                for row in cases]
    native.require(output == expected, "Portable return, output count, or guards differ from native")
    formatter = run(FORMAT[0], "--version").strip()
    compiler = run(COMPILER, "--version").splitlines()[0]
    row = {
        "original_elf_sha256": native.ELF_SHA256, "mangled": native.MANGLED,
        "original_address": native.ADDRESS, "cpp_compiled": True,
        "mangling_namespace_checked": True, "portable_ready": False,
        "sources": {str(path.relative_to("uc-library")): digest(path) for path in (HEADER, SOURCE)},
        "repository_sources": {}, "domain": DOMAIN, "declaration_uncertainties": DECLARATIONS,
    }
    proof = {
        **row, "version": 1, "task_id": TASK, "start_utc": started,
        "success": True, "format_check_passed": True, "behavior_validation_passed": True,
        "limitations": LIMITATIONS, "functions": [dict(row, success=True)],
        "proposed_readiness": {"ready": [], "pending": [row]},
        "argv": sys.argv, "commands": commands, "native": observed,
        "original_input": {"path": str(args.elf), "sha256": native.ELF_SHA256},
        "fixture": bind(args.fixture), "object": bind(args.object), "executable": bind(args.exe),
        "test": bind(REPLAY), "producers": [bind(TEST / name) for name in ("native.py", "check.py")],
        "native_case_count": len(cases), "portable_case_count": len(output), "symbol": symbols[0],
        "portable_observations": output, "formatter_version": formatter,
        "compiler_version": compiler, "canonical_binding_pending": args.integration is None,
        "end_utc": datetime.now(timezone.utc).isoformat(),
    }
    if args.integration:
        proof["integration"] = bind(args.integration)
    if args.out:
        args.out.write_text(json.dumps(proof, indent=2) + "\n")
    print(f"PASS {len(cases)} original ARM calls and {len(output)} portable Linux calls")


if __name__ == "__main__":
    main()
