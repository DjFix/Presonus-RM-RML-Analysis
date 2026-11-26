"""Compile, inspect and differentially replay MixerClassManager lookup."""
import argparse
import json
from pathlib import Path
import subprocess

TEST = Path(__file__).with_name("Replay.cpp")
SOURCE = Path("uc-library/src/Presonus/MixerClassManager.cpp")
WRAPS = ("strcmp", "_ZdlPv", "_ZdlPvm", "_ZdaPv")


def checked(argv):
    return subprocess.run(argv, check=True, text=True, stdout=subprocess.PIPE).stdout


def compile_replay(out, provider):
    out.mkdir(parents=True, exist_ok=True)
    obj = out / "MixerClassManager.o"
    flags = [
        "c++", "-std=c++20", "-O2", "-UNDEBUG", "-isystem", "third_party/ccl-framework",
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


def check_symbols(out, fixture):
    wanted = {case["original"]["mangled"] for case in json.loads(fixture.read_text())["cases"]}
    rows = checked(["readelf", "--wide", "--syms", out / "MixerClassManager.o"])
    observed = {}
    for line in rows.splitlines():
        row = line.split()
        if len(row) == 8 and row[-1] in wanted:
            assert row[3:6] == ["FUNC", "GLOBAL", "DEFAULT"]
            assert int(row[2]) > 0 and row[-2].isdigit()
            observed[row[-1]] = [row[-2], row[1], row[2]]
    assert wanted and set(observed) == wanted
    print(json.dumps(observed, sort_keys=True))


def replay(executable, fixture):
    data = json.loads(fixture.read_text())
    variant = data["variant"]
    cases = data["cases"]
    assert cases
    for case in cases:
        result = case["expected"]
        expected = [f"strcmp\t{lhs}\t{rhs}" for lhs, rhs in case["compared"]]
        expected.append(f"result {'null' if result is None else result}")
        inputs = [case["query"], *case["roster"]]
        args = ["<null>" if item is None else item for item in inputs]
        argv = [executable.resolve(), variant, *args]
        actual = checked(argv).splitlines()
        assert actual == expected, (variant, inputs, actual, expected)
        print(f"{case['original']['role']} {variant} {inputs!r}: {actual!r}")
    print(f"{len(cases)} portable cases matched native results and ordered strcmp arguments")


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
        check_symbols(args.out, args.fixture)
    else:
        replay(args.executable, args.fixture)


if __name__ == "__main__":
    main()
