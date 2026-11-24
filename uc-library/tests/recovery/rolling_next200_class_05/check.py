"""Replay verified ARM cases and compare the compiled PermissionsComponent."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[4]
BASE = Path(__file__).resolve().parent
LIBRARY = ROOT / "uc-library"
SOURCES = (
    "src/Presonus/Mixer/PermissionsComponent.cpp",
    "include/presonus/mixer/PermissionsComponent.hpp",
)
CORE_SOURCES = (
    "core/portable/corecomponent.h",
    "core/portable/coreparams.h",
    "core/public/corevector.h",
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(argv):
    return subprocess.check_output(argv, text=True)


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def main():
    started = datetime.now(timezone.utc)
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("exe", "object", "integration", "out", "fixture"):
        parser.add_argument("--" + flag, required=True, type=Path)
    args = parser.parse_args()
    native_argv = [sys.executable, "-B", str(BASE / "native.py")]
    native = json.loads(run(native_argv))
    require(native == json.loads(args.fixture.read_text()), "Native fixture differs")
    symbol_argv = ["nm", "--defined-only", str(args.object)]
    symbols = [row.split()[-1] for row in run(symbol_argv).splitlines() if row.strip()]
    require(symbols.count(native["mangled"]) == 1, "Exact scoped symbol missing or duplicated")
    replay_argv = [str(args.exe.resolve())]
    replay = run(replay_argv)
    expected = [
        f"{case['case']} unchanged"
        for case in native["cases"] if case["receiver_unchanged"] and case["frame_restored"]
    ]
    require(len(expected) == 3 and replay.splitlines() == expected, "Portable replay differs")
    format_argv = [
        "uc-library/.venv/bin/clang-format", "--style=file", "--fallback-style=LLVM",
        "--dry-run", "--Werror", *[str(LIBRARY / p) for p in SOURCES], str(BASE / "Replay.cpp")
    ]
    run(format_argv)
    domain = (
        "Three verified RM/RML 13731 ARM executions use separate aligned receiver "
        "offsets and differing 4 KiB memory/register sentinels. The body restores "
        "caller SP/FP and branches to LR with no receiver access or call. Three "
        "pinned-CCL-backed C++ states exercise absent selection, borrowed "
        "selection, and owned selection plus a device entry; snapshots, "
        "component and binding representations, and device projection are unchanged."
    )
    uncertainty = (
        "The native body preserves entry r0. Its original return declaration "
        "and virtual slot, if any, remain unresolved. Portable void is provisional."
    )
    row = dict(
        original_elf_sha256=native["elf_sha256"], mangled=native["mangled"],
        original_address=native["address"], cpp_compiled=True,
        mangling_namespace_checked=True, portable_ready=False, domain=domain,
        declaration_uncertainties=[uncertainty],
        sources={p: digest(LIBRARY / p) for p in SOURCES},
        repository_sources={
            f"third_party/ccl-framework/{p}": digest(ROOT / "third_party/ccl-framework" / p)
            for p in CORE_SOURCES
        },
    )
    proof = dict(
        cpp_differential_passed=True, compiled_mangled_names_matched=True,
        original_function_verified=False, hardware_verified=False, portable_ready=False,
        functions=[row], proposed_readiness={"ready": [], "pending": [row]},
        native=native, native_argv=native_argv, native_cases=len(native["cases"]),
        portable_cases=len(expected), portable_output=replay.splitlines(), replay_argv=replay_argv,
        symbol_argv=symbol_argv, fixture_sha256=digest(args.fixture),
        native_producer_sha256=digest(BASE / "native.py"), proof_producer_sha256=digest(Path(__file__)),
        replay_source_sha256=digest(BASE / "Replay.cpp"),
        format_argv=format_argv, formatter_version=run([format_argv[0], "--version"]).strip(),
        core_provider_release="CCL 5.0.0",
        object_sha256=digest(args.object), executable_sha256=digest(args.exe),
        integration=str(args.integration), integration_sha256=digest(args.integration),
        replay_started_utc=started.isoformat(), replay_finished_utc=datetime.now(timezone.utc).isoformat(),
    )
    args.out.write_text(json.dumps(proof, indent=2) + "\n")
    print(f"{len(expected)} independent ARM cases and {len(expected)} compiled C++ cases passed")


if __name__ == "__main__":
    main()
