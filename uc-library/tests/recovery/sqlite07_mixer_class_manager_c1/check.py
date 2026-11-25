"""Compile, inspect or replay the shared MixerClassManager lifecycle."""
import argparse
import json
from pathlib import Path
import subprocess

SUFFIXES = ("C1", "C2", "D1", "D2")
STEM = "_ZN8Presonus17MixerClassManager"
TEST = Path(__file__).with_name("Replay.cpp")
SOURCE = Path("uc-library/src/Presonus/MixerClassManager.cpp")
WRAPS = ("_ZdlPv", "_ZdlPvm", "_ZdaPv")


def checked(argv):
    result = subprocess.run(argv, check=True, text=True, stdout=subprocess.PIPE)
    return result.stdout


def compile_replay(out, provider):
    out.mkdir(parents=True, exist_ok=True)
    obj = out / "MixerClassManager.o"
    flags = [
        "c++", "-std=c++20", "-UNDEBUG", "-isystem", "third_party/ccl-framework",
        "-Iuc-library/include", "-DLINUX=1", "-DCORE_PLATFORM_LINUX=1",
        "-ffunction-sections", "-fdata-sections", "-Wall", "-Wextra", "-Werror",
    ]
    commands = [
        [*flags, "-c", str(SOURCE), "-o", str(obj)],
        [*flags, str(TEST), str(obj), "-Wl,--gc-sections",
         *(f"-Wl,--wrap={symbol}" for symbol in WRAPS), "-Wl,--start-group",
         str(provider / "libcorelib.a"), str(provider / "libpresonus_core_allocator.a"),
         "-Wl,--end-group", "-pthread", "-ldl", "-o", str(out / "replay")],
    ]
    for command in commands:
        print(json.dumps(command), flush=True)
        subprocess.run(command, check=True)


def check_symbols(out):
    symbols = {STEM + suffix + "Ev" for suffix in SUFFIXES}
    rows = checked(["readelf", "--wide", "--syms", out / "MixerClassManager.o"])
    observed = {}
    for line in rows.splitlines():
        row = line.split()
        if len(row) == 8 and row[-1] in symbols:
            assert row[3:6] == ["FUNC", "GLOBAL", "DEFAULT"]
            assert int(row[2]) > 0 and row[-2].isdigit()
            observed[row[-1]] = [row[-2], row[1], row[2]]
    assert set(observed) == symbols
    assert observed[STEM + "C1Ev"] == observed[STEM + "C2Ev"]
    assert observed[STEM + "D1Ev"] == observed[STEM + "D2Ev"]
    assert observed[STEM + "C1Ev"][0] != observed[STEM + "D1Ev"][0]
    assert STEM + "D0Ev" not in rows
    print(json.dumps(observed, sort_keys=True))


def replay(executable, fixture):
    cases = json.loads(fixture.read_text())["cases"]
    assert cases
    for case in cases:
        variant = case["original"]["mangled"][-4:-2].lower()
        native = case["events"]
        if variant.startswith("c"):
            assert native == [["vector_resize", 0]]
        else:
            assert native[-1] == ["vector_destroy"]
        delta = case["observed_native_fields"][-1]
        expected = [f"empty 0 0 {delta}"]
        expected.extend(f"record_delete {index}" for label, *indices in native
                        if label == "record_delete" for index in indices)
        if case["count"]:
            expected.append("vector_storage_release")
        actual = checked([executable.resolve(), variant, str(case["count"])]).splitlines()
        assert actual == expected, (variant, case["count"], expected, actual)
        print(f"{case['original']['role']} {variant} count={case['count']}: {'; '.join(actual)}")
    print(f"{len(cases)} portable scenarios matched native lifecycle observations")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("check", choices=("compile", "symbols", "replay"))
    parser.add_argument("--out", type=Path)
    parser.add_argument("--provider", type=Path)
    parser.add_argument("--executable", type=Path)
    parser.add_argument("--fixture", type=Path)
    args = parser.parse_args()
    if args.check == "compile":
        compile_replay(args.out, args.provider)
    elif args.check == "symbols":
        check_symbols(args.out)
    else:
        replay(args.executable, args.fixture)


if __name__ == "__main__":
    main()
