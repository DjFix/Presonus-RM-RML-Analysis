"""Local Linux checks and portable fixture adapter for ParamHelper::applyRange."""
import argparse
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[4]
TASK_DIR = Path(__file__).parent.relative_to(ROOT)
SOURCE = Path("uc-library/src/ParamHelper.cpp")
HEADER = Path("uc-library/include/presonus/uc/ParamHelper.hpp")
OUT = Path("temp/recovery-work/sqlite06-param-helper-build")
OBJECT = OUT / "ParamHelper.o"
EXE = OUT / "replay"
SDK = Path("temp/core-upstream/root-integration-01/upstream-core/sdk")
SYMBOL = "_ZN11ParamHelper10applyRangeEPN4Core8Portable9ParameterERKN8Presonus2UC15ParamRangeEventE"


def run(argv, **kwargs):
    print("+", *argv, flush=True)
    return subprocess.run(argv, cwd=ROOT, check=True, text=True, **kwargs)


def compile_replay(sdk):
    (ROOT / OUT).mkdir(parents=True, exist_ok=True)
    common = [
        "c++", "-std=c++17", "-Ulinux", "-DNDEBUG=1", "-DCORE_USE_OPENSSL=1",
        "-DPRESONUS_HAS_UPSTREAM_CORE=1", "-Wno-multichar", "-fno-rtti",
        "-Iuc-library/include", "-isystem", sdk / "include/presonus-core-5",
    ]
    run([*common, "-c", SOURCE, "-o", OBJECT])
    run([*common, TASK_DIR / "Replay.cpp", OBJECT, sdk / "lib/libcorelib.a",
         sdk / "lib/libpresonus_core_allocator.a", "-pthread", "-o", EXE])


def symbols():
    names = run(["nm", "--defined-only", OBJECT], capture_output=True).stdout
    matches = [line for line in names.splitlines() if line.split()[-1] == SYMBOL]
    assert len(matches) == 1, names
    print(matches[0])
    names = run(["nm", "--defined-only", EXE], capture_output=True).stdout
    for name in (
        "_ZN4Core17FormatterRegistry4findEPKc",
        "_ZN4Core19InterpolatorFactory6createEPKc",
        "_ZN4Core8Portable12NumericParam15setInterpolatorEPNS_12InterpolatorE",
    ):
        assert any(line.split()[-1] == name for line in names.splitlines()), name
        print(name)


def replay(exe, fixture):
    records = json.loads(fixture.read_text())
    count = 0
    for role, cases in records.items():
        for row in cases:
            case, observed = row["inputs"], row["observed"]
            command = [exe.resolve(), str(int(case["numeric"])), case["curve"],
                       case["formatter"], *map(str, case["words"])]
            lines = run(command, capture_output=True).stdout.splitlines()
            # Registry internals are pinned and left intact. Read formatter
            # assignment at the typed cast/final state. A missing factory
            # lookup has no callback, but null install must still be observed.
            trace = [
                " ".join(map(str, event)) for event in observed["trace"]
                if event[0] != "formatter" and
                (event[0] != "factory" or event[1] == "observeCurve")
            ]
            trace.append(f"formatter {observed['formatter']}")
            assert lines == trace, (role, case, trace, lines)
            count += 1
        print(f"{role}: {len(cases)} portable cases")
    print(f"portable replay: {count} role-bound cases")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("compile", "symbols", "native", "replay"))
    parser.add_argument("--sdk", type=Path, default=SDK)
    parser.add_argument("--executable", type=Path, default=EXE)
    parser.add_argument("--fixtures", type=Path, default=TASK_DIR / "fixtures.json")
    args = parser.parse_args()
    if args.mode == "compile":
        compile_replay(args.sdk)
    elif args.mode == "symbols":
        symbols()
    elif args.mode == "native":
        from native import observe
        assert observe() == json.loads(args.fixtures.read_text())
        print("native replay: 6 client and 6 server executions")
    else:
        replay(args.executable, args.fixtures)


if __name__ == "__main__":
    main()
