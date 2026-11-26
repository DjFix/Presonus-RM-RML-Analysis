"""Test schedule and fixture comparison for MeterManagerBase::deleteAll."""

import argparse
import hashlib
import json
import shlex
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
WORK = ROOT / "temp/recovery-work/meter-roster"
SOURCE = ROOT / "uc-library/src/Presonus/MeterManagerBase.cpp"
OBJECT = WORK / "MeterManagerBase.o"
EXE = WORK / "Replay"
SYMBOL = "_ZN8Presonus16MeterManagerBase9deleteAllERN4Core6VectorIPNS_9MeterMaidEEE"
WRAPS = ("_ZdlPv", "_ZdlPvm", "_ZdaPv", "_ZdaPvm")


def run(*argv, **kwargs):
    argv = [str(arg) for arg in argv]
    print(shlex.join(argv), flush=True)
    return subprocess.run(argv, check=True, **kwargs)


def compile_replay():
    build = next(
        parent / "temp/core-upstream/root-integration-01"
        for parent in (ROOT, *ROOT.parents)
        if (parent / "temp/core-upstream/root-integration-01/compile_commands.json").is_file()
    )
    sdk = build / "upstream-core/sdk"
    WORK.mkdir(parents=True, exist_ok=True)
    compiler = ["/usr/bin/c++", "-std=c++17", "-DNDEBUG=1",
                "-DCORE_USE_OPENSSL=1", "-DPRESONUS_HAS_UPSTREAM_CORE=1",
                "-I", ROOT / "uc-library/include", "-isystem",
                sdk / "include/presonus-core-5", "-pthread", "-Ulinux", "-O2"]
    objects = []
    for source in (SOURCE, SOURCE.with_name("MeterMaid.cpp"),
                   SOURCE.with_name("MeterBallistics.cpp"), HERE / "Replay.cpp"):
        obj = WORK / (source.stem + ".o")
        run(*compiler, "-MD", "-MF", obj.with_suffix(".d"), "-c", source, "-o", obj)
        objects.append(obj)
    lib = sdk / "lib"
    run(*compiler, *objects, *("-Wl,--wrap=" + name for name in WRAPS),
        lib / "libcorelib.a", lib / "libpresonus_core_allocator.a", "-ldl", "-lm",
        "-o", EXE)


def symbols():
    result = run("nm", "--defined-only", OBJECT, text=True, capture_output=True)
    assert sum(line.split()[-1] == SYMBOL for line in result.stdout.splitlines() if line) == 1
    print(SYMBOL)


def compare(exe, fixture, expected_sha256):
    data = fixture.read_bytes()
    assert hashlib.sha256(data).hexdigest() == expected_sha256
    evidence = json.loads(data)
    assert evidence["original"]["mangled"] == SYMBOL
    for case in evidence["cases"]:
        result = run(exe.resolve(), case["slots"], case["capacity"], text=True, capture_output=True)
        assert result.stdout.splitlines() == case["events"], (case, result.stdout)
    print(f"{len(evidence['cases'])} Linux cases matched, 2 runs per case")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("compile", "symbols", "replay"))
    parser.add_argument("--exe", type=Path, default=EXE)
    parser.add_argument("--fixtures", type=Path, default=HERE / "fixtures.json")
    parser.add_argument("--fixture-sha256")
    args = parser.parse_args()
    if args.phase == "compile":
        compile_replay()
    elif args.phase == "symbols":
        symbols()
    elif args.fixture_sha256:
        compare(args.exe, args.fixtures, args.fixture_sha256)
    else:
        parser.error("replay requires --fixture-sha256")


if __name__ == "__main__":
    main()
