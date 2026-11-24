"""Check the compiled DialogMenu replay against separately executed ARM fixtures."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

TASK = "rolling_dialog_debug"
DIRECTORY = Path("uc-library/tests/recovery") / TASK
SOURCE = Path("uc-library/src/Presonus/IDAWDialogHandler.cpp")
HEADER = Path("uc-library/include/presonus/IDAWDialogHandler.hpp")
FORMATTED = [SOURCE, HEADER, DIRECTORY / "Replay.cpp"]
FORMAT = [
    "uc-library/.venv/bin/clang-format", "--style=file", "--fallback-style=LLVM",
    "--dry-run", "--Werror", *map(str, FORMATTED),
]
DOMAIN = (
    "Each exact firmware debug range executed 12 times on four initialized empty "
    "ARM receivers across C1/D1 and C2/D2 and two prefills. Each call completed "
    "with stack-only accesses and no receiver mutation. Portable replay exercised "
    "24 calls on eight initialized receivers with a live pinned empty Core vector."
)
UNCERTAINTIES = [
    "The exact original debug return declaration is unresolved; void is the portable interface.",
    "Native ctor/dtor runs instrument Core boundary calls only. No native Core body or "
    "populated child ownership was validated; lifecycle variants are supporting evidence.",
    "Parse, separator decisions, original class layout, ARM ABI and hardware remain outside the domain.",
]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("exe", "object", "integration", "out", "fixtures", "mixer", "surface"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    start = datetime.now(timezone.utc).isoformat()
    watch = time.monotonic()

    oracle = [
        sys.executable, "-B", str(DIRECTORY / "native.py"), "--mixer", args.mixer,
        "--surface", args.surface, "--fixtures", args.fixtures,
    ]
    native_output = subprocess.check_output(oracle, text=True).strip()
    observations = json.loads(Path(args.fixtures).read_text())
    assert len(observations) == 2
    subprocess.run(FORMAT, check=True)
    symbols = subprocess.check_output(["nm", "--defined-only", args.object], text=True)
    defined = {line.split()[-1] for line in symbols.splitlines() if line.split()}
    assert all(row["debug_range"]["mangled"] in defined for row in observations)
    replay_argv = [str(Path(args.exe).resolve())]
    replay_output = subprocess.check_output(replay_argv, text=True).strip()
    native_cases = [case for row in observations for case in row["cases"]]
    assert all(case["debug_receiver_unchanged"] and case["initialized_words"][5:9] == [0, 0, 0, 5]
               for case in native_cases)
    total_calls = sum(case["debug_calls"] for case in native_cases)
    assert replay_output == (
        f"{len(native_cases)} empty DialogMenu receivers, {total_calls} debug calls, empty Core vector"
    )

    sources = {
        str(path.resolve().relative_to(Path("uc-library").resolve())): digest(path)
        for path in [*FORMATTED, Path(args.fixtures), DIRECTORY / "native.py", Path(__file__)]
    }
    provider_paths = [
        "core/public/corevector.h", "core/public/corecontainer.h", "core/public/coreplatform.h",
        "core/public/coreclibrary.h", "core/public/coremalloc.h",
    ]
    provider_paths = [Path("third_party/ccl-framework") / name for name in provider_paths]
    providers = {str(path): digest(path) for path in provider_paths}
    pending = [
        dict(original_elf_sha256=row["elf_sha256"], mangled=row["debug_range"]["mangled"],
             original_address=row["debug_range"]["address"], domain=DOMAIN, sources=sources,
             repository_sources=providers, cpp_compiled=True, mangling_namespace_checked=True,
             portable_ready=False, declaration_uncertainties=UNCERTAINTIES,
             original_function_verified=False, hardware_verified=False)
        for row in observations
    ]
    proof = dict(
        version=1, task_id=TASK, domain=DOMAIN, limitations=UNCERTAINTIES,
        cpp_differential_passed=True, compiled_original_mangled_names_matched=True,
        mangling_namespace_checked=True, sources=sources, repository_sources=providers,
        proposed_readiness=dict(ready=[], pending=pending),
        functions=[
            dict(record, range_verified=True, cpp_differential_passed=True,
                 native_cases=sum(case["debug_calls"] for case in row["cases"]))
            for record, row in zip(pending, observations)
        ],
        native=dict(argv=oracle, output=native_output, elf_inputs={
            args.mixer: digest(args.mixer), args.surface: digest(args.surface),
        }, ranges_and_observations=observations),
        replay=dict(argv=replay_argv, output=replay_output, portable_calls=total_calls),
        fixture=dict(path=args.fixtures, sha256=digest(args.fixtures)),
        oracle_producer_sha256=digest(DIRECTORY / "native.py"),
        producer_sha256=digest(__file__),
        format=dict(argv=FORMAT, version=subprocess.check_output([FORMAT[0], "--version"], text=True).strip(),
                    sources={str(path): digest(path) for path in FORMATTED}),
        executable=dict(path=args.exe, sha256=digest(args.exe)),
        objects={args.object: digest(args.object)}, compiled_symbols=symbols.splitlines(),
        phase_accounting=dict(start_utc=start, end_utc=datetime.now(timezone.utc).isoformat(),
                              elapsed_seconds=time.monotonic() - watch),
    )
    if args.integration != "local":
        proof["integration"] = dict(path=args.integration, sha256=digest(args.integration))
    Path(args.out).write_text(json.dumps(proof, indent=2) + "\n")
    print(replay_output)


if __name__ == "__main__":
    main()
