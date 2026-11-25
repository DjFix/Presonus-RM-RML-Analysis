"""Build, check exact exports, and replay immutable native observations."""

import argparse
import json
from pathlib import Path
import subprocess

from native import ROOT, TASK_PREFIX, fixture_input, generate

SOURCE = Path("uc-library/src/Presonus/Surface")
HEADER = Path("uc-library/include/presonus/surface/FatChannelClipboard.hpp")
SELECTION = SOURCE / "FatChannelClipboardSelection.cpp"
BASE = Path(__file__).resolve().parent.relative_to(ROOT)
DEFAULT_BUILD = Path("/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01")
FLAGS = [
    "-std=c++17", "-O2", "-Ulinux", "-fno-rtti", "-pthread",
    "-ffunction-sections", "-fdata-sections",
    "-Iuc-library/include", "-isystem", "third_party/ccl-framework",
]


def run(argv, **kwargs):
    return subprocess.run([str(value) for value in argv], check=True, cwd=ROOT, **kwargs)


def compile_replay(out, build):
    out.mkdir(parents=True, exist_ok=True)
    selection = out / "selection.o"
    replay = out / "Replay.o"
    for source, obj in ((SELECTION, selection), (BASE / "Replay.cpp", replay)):
        run(["c++", *FLAGS, "-MMD", "-MF", obj.with_suffix(".d"), "-c", source, "-o", obj])
    sdk = build / "upstream-core/sdk/lib"
    run([
        "c++", *FLAGS, replay, SOURCE / "FatChannelClipboard.cpp",
        selection, "-Wl,--gc-sections", sdk / "libcorelib.a",
        sdk / "libpresonus_core_allocator.a", "-lssl", "-lcrypto", "-ldl",
        build / "private-glibc29-provider/libpresonus_private_glibc29.a",
        "-o", out / "replay",
    ])


def check_symbols(obj, fixture):
    output = run(["nm", "--defined-only", obj], capture_output=True, text=True).stdout
    name = fixture["original"]["mangled"]
    symbols = [row.split() for row in output.splitlines()]
    assert sum(len(row) == 3 and row[1:] == ["T", name] for row in symbols) == 1
    print(name)


def check_replay(executable, mode, fixture):
    for index, case in enumerate(fixture["cases"], 1):
        result = run([executable.resolve(), mode], capture_output=True, text=True,
                     input=fixture_input(case["inputs"]))
        actual = result.stdout.split()
        assert actual == case["expected"], (index, case["expected"], actual)
    print(f"{mode}: {len(fixture['cases'])} portable cases matched the native fixtures")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("compile", "symbols", "native", "replay"))
    parser.add_argument("--method", choices=("copy", "collectpastechannels"), required=True)
    parser.add_argument("--out", type=Path,
                        default=Path("temp/recovery-work/clipboard-selection-local"))
    parser.add_argument("--build", type=Path, default=DEFAULT_BUILD)
    parser.add_argument("--executable", type=Path)
    parser.add_argument("--fixtures", type=Path)
    args = parser.parse_args()
    if args.action == "compile":
        compile_replay(args.out, args.build)
        return
    fixture_path = args.fixtures or BASE.with_name(TASK_PREFIX + args.method) / "fixtures.json"
    fixture = json.loads(fixture_path.read_text())
    executable = args.executable or args.out / "replay"
    if args.action == "symbols":
        check_symbols(args.out / "selection.o", fixture)
    elif args.action == "native":
        assert generate(executable.resolve(), args.method) == fixture
        print(f"{args.method}: {len(fixture['cases'])} exact native executions reproduced")
    else:
        check_replay(executable, args.method, fixture)


if __name__ == "__main__":
    main()
