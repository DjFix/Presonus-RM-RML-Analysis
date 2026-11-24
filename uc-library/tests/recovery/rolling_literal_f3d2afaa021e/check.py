"""Compare fresh offline ARM observations and the built portable receiver."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import native

ROOT = Path(__file__).resolve().parents[4]
TASK = "rolling_literal_f3d2afaa021e"
TEST = Path("uc-library/tests/recovery") / TASK
HEADER = Path("include/presonus/panel/WolverinePanelRegistrar.hpp")
SOURCE = Path("src/Presonus/Panel/WolverinePanelRegistrar.cpp")
TABLE_HEADER = Path("include/presonus/panel/PanelParameterTables.hpp")
TABLE_SOURCE = Path("src/Presonus/Panel/PanelParameterTables.cpp")
CORE = Path("third_party/ccl-framework/core")
FORMATTER = "uc-library/.venv/bin/clang-format"
FORMAT = [FORMATTER, "--style=file", "--fallback-style=LLVM", "--dry-run", "--Werror",
          Path("uc-library") / HEADER, Path("uc-library") / SOURCE, TEST / "Replay.cpp"]
DOMAIN = (
    "RM/RML mixer 13731: three isolated ARM runs with two distinct receiver "
    "addresses and sentinel patterns, exact original range, r0 word and mapped "
    "read-only NUL-terminated bytes, unchanged receiver bytes, restored stack "
    "and frame registers, writes confined to the stack, no external calls. "
    "Linux: four calls on three real source receivers, exact typed const char* "
    "result and text, repeated and cross-instance pointer identity after the "
    "first receivers were destroyed, and seven existing parameter count/table "
    "pointer observations preserved for each of the first two receivers."
)
LIMITS = [
    "Original ordinary return type and pointee const qualification unresolved. "
    "The explicit const char* is a portable source declaration.",
    "Original class layout and ARM ABI unresolved. Native receiver storage is "
    "synthetic, and the test never opens the device or accesses hardware.",
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def run(argv):
    return subprocess.run(list(map(str, argv)), cwd=ROOT, capture_output=True,
                          text=True, check=True).stdout


def symbols(obj):
    output = run(["nm", "--defined-only", obj])
    matches = [line for line in output.splitlines()
               if len(line.split()) == 3 and line.split()[1:] == ["T", native.SYMBOL]]
    assert len(matches) == 1, matches
    return matches[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=("compile", "symbols", "replay"))
    parser.add_argument("--exe", type=Path)
    parser.add_argument("--object", type=Path, required=True)
    parser.add_argument("--elf", type=Path)
    parser.add_argument("--fixture", type=Path)
    parser.add_argument("--integration", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.kind == "compile":
        common = ["/usr/bin/c++", "-std=c++17", "-O2", "-fno-lto",
                  "-Iuc-library/include", "-Ithird_party/ccl-framework"]
        args.object.parent.mkdir(parents=True, exist_ok=True)
        run([*common, "-c", Path("uc-library") / SOURCE, "-o", args.object])
        run([*common, TEST / "Replay.cpp", Path("uc-library") / TABLE_SOURCE,
             args.object, "-o", args.exe])
        return
    symbol = symbols(args.object)
    if args.kind == "symbols":
        print(symbol)
        return
    started = now()
    run(FORMAT)
    observed = native.observe(args.elf)
    assert observed == json.loads(args.fixture.read_text()), "Native observation drift"
    stdout = run([args.exe.resolve(), observed["literal"]["text"]]).strip()
    sources = {str(p): sha(Path("uc-library") / p)
               for p in (SOURCE, HEADER, TABLE_SOURCE, TABLE_HEADER)}
    core = {str(CORE / p): sha(CORE / p) for p in
            ("portable/coreparaminfo.h", "public/coretypes.h", "public/coremacros.h")}
    row = dict(original_elf_sha256=native.ELF_HASH, mangled=native.SYMBOL,
               original_address=observed["address"], original_size=observed["size"],
               original_section=observed["section_index"], cpp_compiled=True,
               mangling_namespace_checked=True, portable_ready=False,
               original_function_verified=False, hardware_verified=False,
               domain=DOMAIN, sources=sources, repository_sources=core,
               declaration_uncertainties=LIMITS)
    proof = dict(version=1, task_id=TASK, started_utc=started, completed_utc=now(),
                 argv=sys.argv, behavior_validation_passed=True, format_check_passed=True,
                 cpp_compiled=True, mangling_namespace_checked=True, portable_ready=False,
                 canonical_binding_pending=args.integration is None, domain=DOMAIN,
                 sources=sources, repository_sources=core,
                 proposed_readiness=dict(ready=[], pending=[row]),
                 original_native=dict(elf_path=str(args.elf), **observed),
                 portable_cases=dict(calls=4, receivers=3, output=stdout),
                 fixture=dict(path=str(args.fixture), sha256=sha(args.fixture)),
                 producers={str(TEST / p): sha(TEST / p) for p in
                            ("native.py", "check.py", "Replay.cpp")},
                 executable=dict(path=str(args.exe), sha256=sha(args.exe)),
                 object=dict(path=str(args.object), sha256=sha(args.object)),
                 symbols=[symbol], limitations=LIMITS,
                 versions=dict(compiler=run(["/usr/bin/c++", "--version"]).splitlines()[0],
                               formatter=run([FORMATTER, "--version"]).strip()))
    if args.integration:
        proof["integration"] = dict(path=str(args.integration), sha256=sha(args.integration))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(proof, indent=2) + "\n")
    print(stdout)


if __name__ == "__main__":
    main()
