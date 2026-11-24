"""Compile and compare the canonical registrar against fresh ARM observations."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import native

ROOT = Path(__file__).resolve().parents[4]
TASK = Path(__file__).parent.name
TEST = Path("uc-library/tests/recovery") / TASK
SCRATCH = Path("temp/recovery-work") / TASK
HEADER = Path("include/presonus/panel/WolverinePanelRegistrar.hpp")
SOURCE = Path("src/Presonus/Panel/WolverinePanelRegistrar.cpp")
TABLE_HEADER = Path("include/presonus/panel/PanelParameterTables.hpp")
TABLE_SOURCE = Path("src/Presonus/Panel/PanelParameterTables.cpp")
FORMATTER = "uc-library/.venv/bin/clang-format"
COMPILE = ["c++", "-std=c++17", "-O2", "-fno-lto", "-Wall", "-Wextra", "-Werror",
           "-Iuc-library/include", "-isystem", "third_party/ccl-framework"]
FORMAT = [FORMATTER, "--style=file", "--fallback-style=LLVM", "--dry-run", "--Werror",
          Path("uc-library") / HEADER, Path("uc-library") / SOURCE, TEST / "Replay.cpp"]
DOMAIN = (
    "110 exact-range ARM executions across 22 signed group values and five seeded "
    "count values, using two receiver and reference addresses. Observed r0, count, "
    "receiver and canary bytes, instruction range, stack accesses and restored SP "
    "and frame pointer. Linux replay compares null and unchanged count on two "
    "real const registrar instances across all corresponding inputs."
)
LIMITS = [
    "Original ordinary return declaration, including pointee type and qualifiers, is pending. "
    "The portable const int* follows the existing sibling registrar convention.",
    "Original object layout, inheritance, virtual dispatch, ARM ABI and hardware behavior remain unresolved. "
    "Native receiver/reference storage is synthetic and guarded with canaries.",
    "The tested body has no calls. The actual existing parameter table provider is linked "
    "for other methods in the same source unit.",
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def run(logs, argv, **kwargs):
    argv = list(map(str, argv))
    before = time.monotonic()
    result = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, **kwargs)
    logs.append({
        "argv": argv, "returncode": result.returncode, "seconds": time.monotonic() - before,
        "stdout": result.stdout, "stderr": result.stderr,
    })
    if result.returncode:
        print(result.stderr, file=sys.stderr)
        result.check_returncode()
    return result.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=("format", "compile", "symbols", "native", "replay"))
    parser.add_argument("--object", type=Path, default=SCRATCH / "WolverinePanelRegistrar.o")
    parser.add_argument("--exe", type=Path, default=SCRATCH / "Replay")
    parser.add_argument("--elf", type=Path)
    parser.add_argument("--fixture", type=Path, default=TEST / "fixtures.json")
    parser.add_argument("--integration", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    os.chdir(ROOT)
    logs = []
    if args.kind == "format":
        print(run(logs, [FORMATTER, "--version"]).strip())
        run(logs, FORMAT)
        return
    if args.kind == "compile":
        SCRATCH.mkdir(parents=True, exist_ok=True)
        run(logs, [*COMPILE, "-c", Path("uc-library") / SOURCE, "-o", args.object])
        run(logs, [*COMPILE, TEST / "Replay.cpp", Path("uc-library") / TABLE_SOURCE,
                   args.object, "-o", args.exe])
        (SCRATCH / "compile.json").write_text(json.dumps(logs, indent=2) + "\n")
        print("Compiled registrar and linked replay with the actual parameter table provider.")
        return

    if args.kind == "native":
        observed = native.observe(args.elf)
        assert observed == json.loads(args.fixture.read_text()), "Native observation drift"
        print(f"Re-executed {len(observed['cases'])} native cases.")
        return

    symbol_lines = run(logs, ["nm", "--defined-only", args.object]).splitlines()
    symbols = [line for line in symbol_lines if line.split()[1:] == ["T", native.SYMBOL]]
    assert len(symbols) == 1, symbols
    print(symbols[0])
    if args.kind == "symbols":
        return

    started = now()
    run(logs, FORMAT)
    observed = native.observe(args.elf)
    assert observed == json.loads(args.fixture.read_text()), "Native observation drift"
    cases = observed.pop("cases")
    addresses = sorted({case["receiver"] for case in cases})
    assert all(case["return_word"] == 0 for case in cases)
    stdin = "".join(
        f"{case['group']} {case['count_before']} {addresses.index(case['receiver'])}\n"
        for case in cases
    )
    stdout = run(logs, [args.exe.resolve()], input=stdin)
    expected = [f"{int(case['return_word'] == 0)} {case['count_after']}" for case in cases]
    assert stdout.splitlines() == expected, "Portable null/count behavior differs from native"
    sources = {str(path): sha(Path("uc-library") / path)
               for path in (SOURCE, HEADER, TABLE_SOURCE, TABLE_HEADER)}
    core = Path("third_party/ccl-framework/core")
    provider_headers = (
        "portable/coreparaminfo.h", "public/coretypes.h", "public/coremacros.h",
        "public/coreplatform.h", "public/coreclibrary.h", "public/coremalloc.h",
        "public/corebasicmacros.h", "public/coreclassmacros.h",
    )
    repository_sources = {str(core / path): sha(core / path) for path in provider_headers}
    row = dict(
        original_elf_sha256=native.ELF_HASH, mangled=native.SYMBOL,
        original_address=native.ADDRESS, original_size=native.SIZE,
        original_section=native.SECTION, cpp_compiled=True,
        mangling_namespace_checked=True, portable_ready=False, domain=DOMAIN,
        original_function_verified=False, hardware_verified=False,
        sources=sources, repository_sources=repository_sources,
        declaration_uncertainties=LIMITS,
    )
    versions = {
        "compiler": run(logs, ["c++", "--version"]).splitlines()[0],
        "formatter": run(logs, [FORMATTER, "--version"]).strip(),
    }
    proof = dict(
        version=1, task_id=TASK, started_utc=started, completed_utc=now(),
        argv=sys.argv, behavior_validation_passed=True, format_check_passed=True,
        cpp_compiled=True, mangling_namespace_checked=True, portable_ready=False,
        canonical_binding_pending=args.integration is None, domain=DOMAIN,
        sources=sources, repository_sources=repository_sources, symbols=symbols,
        proposed_readiness=dict(ready=[], pending=[row]), limitations=LIMITS,
        original_native=dict(elf_path=str(args.elf), cases=len(cases), **observed),
        portable_cases=dict(calls=len(cases), receivers=len(addresses)),
        fixture=dict(path=str(args.fixture), sha256=sha(args.fixture)),
        producers={str(TEST / path): sha(TEST / path)
                   for path in ("native.py", "check.py", "Replay.cpp")},
        object=dict(path=str(args.object), sha256=sha(args.object)),
        executable=dict(path=str(args.exe), sha256=sha(args.exe)),
        commands=logs, versions=versions,
    )
    if args.integration:
        proof["integration"] = {"path": str(args.integration), "sha256": sha(args.integration)}
    else:
        proof["compilation"] = json.loads((SCRATCH / "compile.json").read_text())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(proof, indent=2) + "\n")
    print(f"Passed {len(cases)} native/portable differential cases.")


if __name__ == "__main__":
    main()
