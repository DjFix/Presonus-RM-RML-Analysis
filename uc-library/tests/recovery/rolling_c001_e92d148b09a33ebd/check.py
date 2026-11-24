"""Build and replay the production AVB count methods against each ARM original."""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import time


TEST = Path(__file__).parent.relative_to(Path.cwd())
LIBRARY = Path("uc-library")
HEADER = LIBRARY / "include/presonus/avb/protocol.hpp"
RECEIVE = LIBRARY / "include/presonus/avb/receive_services.hpp"
SRC = LIBRARY / "src/Presonus/AVB"
SOURCE = SRC / "Protocol.cpp"
KEEPERS = [SRC / name for name in ("AvbManagerLookup.cpp", "AvbManagerReceive.cpp", "Streams.cpp")]
CORE = Path("third_party/ccl-framework/core/public/corelinkedlist.h")
FORMATTER = LIBRARY / ".venv/bin/clang-format"
DOMAIN = ("Exact ARM and linked Linux C++ executions for separate listener and talker rosters "
          "with zero to 32 links. The cases cover empty, partial, full, asymmetric and "
          "over-capacity rosters, including the 4 and 16 boundaries. ARM returns are compared "
          "as raw R0 bits, with the accessed links and stack-only writes checked separately. "
          "Portable replay uses real CCL nodes, checks role clearing and keeps lookup behavior intact.")
LIMITS = ["The portable choices are non-static nonvirtual int members. Exact original return "
          "spelling, virtual declaration and class layout remain unresolved. Original execution "
          "uses synthetic acyclic ARM links without provider stubs. Unconfigured portable free "
          "queries throw; the original has no analogous role binding. Hardware and ARM ABI are unverified."]


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("compile", "symbols", "replay", "all"))
    parser.add_argument("--exe", required=True, type=Path)
    parser.add_argument("--object", required=True, type=Path)
    parser.add_argument("--fixtures", required=True, type=Path)
    parser.add_argument("--integration", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--core-sdk", type=Path)
    args = parser.parse_args()
    checks = []
    start = datetime.now(timezone.utc).isoformat()

    def run(argv, input_text=None):
        argv = list(map(str, argv))
        before = time.monotonic()
        result = subprocess.run(argv, input=input_text, text=True, capture_output=True)
        checks.append(dict(argv=argv, returncode=result.returncode, stdout=result.stdout,
                           stderr=result.stderr, elapsed_seconds=time.monotonic() - before))
        if result.returncode:
            raise RuntimeError(checks[-1])
        return result.stdout

    format_command = [FORMATTER, "--style=file", "--fallback-style=LLVM", "--dry-run",
                      "--Werror", SOURCE, HEADER, TEST / "Replay.cpp"]
    archives = []
    if args.core_sdk:
        archives = [args.core_sdk / "lib" / name for name in
                    ("libcorelib.a", "libpresonus_core_allocator.a")]
    if args.mode in ("compile", "all"):
        assert args.core_sdk is not None
        args.object.parent.mkdir(parents=True, exist_ok=True)
        args.exe.parent.mkdir(parents=True, exist_ok=True)
        flags = ["c++", "-std=c++17", "-O2", "-DNDEBUG", "-Ulinux", "-Wno-multichar",
                 "-ffunction-sections", "-fdata-sections", "-Iuc-library/include",
                 "-Ithird_party/ccl-framework"]
        run([*flags, "-c", SOURCE, "-o", args.object])
        run([*flags, TEST / "Replay.cpp", *KEEPERS, args.object, "-Wl,--gc-sections",
             "-Wl,--start-group", *archives, "-Wl,--end-group", "-lpthread", "-ldl", "-o", args.exe])

    fixture = json.loads(args.fixtures.read_text())
    originals = fixture["originals"]
    mangled = originals[0]["mangled"]
    assert all(original["mangled"] == mangled for original in originals)
    if args.mode in ("symbols", "replay", "all"):
        for path in (args.object, args.exe):
            output = run(["nm", "--defined-only", path])
            assert sum(line.split()[-1] == mangled for line in output.splitlines() if line) == 1
    if args.mode in ("replay", "all"):
        assert args.out is not None
        run(format_command)
        native = [sys.executable, "-B", TEST / "native.py", "--fixtures", args.fixtures]
        run(native)
        if "ActiveListeners" in mangled:
            query = "active-listeners"
        elif "FreeListeners" in mangled:
            query = "free-listeners"
        else:
            assert "FreeTalkers" in mangled
            query = "free-talkers"
        original_cases = list(zip(originals, fixture["observations"], strict=True))
        rows = [(original["role"], case) for original, cases in original_cases for case in cases]
        input_text = "".join(f"{query} {role} {case['listeners']} {case['talkers']}\n" for role, case in rows)
        result = run([args.exe.resolve()], input_text).splitlines()
        assert result == [str(case["result"]) for _, case in rows], (result, rows)

        sources = {str(path.relative_to(LIBRARY)): digest(path) for path in [
            SOURCE, HEADER, RECEIVE, *KEEPERS, TEST / "Replay.cpp", TEST / "native.py",
            TEST / "check.py", args.fixtures
        ]}
        pending = [dict(original_elf_sha256=original["elf_sha256"], mangled=mangled,
                        sources=sources, repository_sources={str(CORE): digest(CORE)},
                        domain=DOMAIN, original_address=original["address"], portable_ready=False, cpp_compiled=True,
                        mangling_namespace_checked=True, declaration_uncertainties=LIMITS)
                   for original in originals]
        proof = dict(verified=True, validation_domain=DOMAIN, cpp_differential_passed=True,
                     compiled_mangled_names_matched=True, mangled_names=[mangled],
                     proposed_readiness=dict(ready=[], pending=pending), originals=originals,
                     native_cases_per_original=[len(cases) for _, cases in original_cases],
                     portable_cases=len(result), native_replay_argv=list(map(str, native)),
                     source_hashes=sources, object_sha256=digest(args.object),
                     executable_sha256=digest(args.exe), provider_archives={str(path): digest(path) for path in archives},
                     integration_sha256=digest(args.integration) if args.integration else None,
                     formatter=run([FORMATTER, "--version"]).strip(),
                     compiler=run(["c++", "--version"]).splitlines()[0],
                     unicorn_version=fixture["unicorn_version"], checks=checks,
                     worktree=run(["git", "rev-parse", "--show-toplevel"]).strip(),
                     start_utc=start, end_utc=datetime.now(timezone.utc).isoformat())
        args.out.write_text(json.dumps(proof, indent=2) + "\n")
        print(json.dumps({"verified": True, "domain": DOMAIN, "portable_cases": len(result)}))


if __name__ == "__main__":
    main()
