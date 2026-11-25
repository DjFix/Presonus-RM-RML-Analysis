"""Compile and compare the real CCL replay with independently captured ARM results."""

import argparse
import json
from pathlib import Path
import subprocess

from native import generate, TASK

TEST = Path("uc-library/tests/recovery") / TASK
WORK = Path("temp/recovery-work/lcd-view-check") / TASK
HEADER = "uc-library/include/presonus/LcdView.hpp"
SOURCE = "uc-library/src/Presonus/LcdView.cpp"
SDK = Path("/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01/upstream-core/sdk/lib")
CXX = ["c++", "-std=c++20", "-fno-rtti", "-Wno-multichar",
       "-Iuc-library/include", "-Ithird_party/ccl-framework"]


def run(argv):
    print("+", *argv, flush=True)
    subprocess.run(argv, check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("check", choices=["format", "compile", "symbols", "replay"])
    parser.add_argument("--exe", type=Path)
    args = parser.parse_args()
    replay = args.exe or WORK / "replay"
    fixture = json.loads((TEST / "fixtures.json").read_text())
    original = fixture["original"]["mangled"]
    if args.check == "format":
        run(["uc-library/.venv/bin/clang-format", "--version"])
        run(["uc-library/.venv/bin/clang-format", "--style=file", "--fallback-style=LLVM",
             "--dry-run", "--Werror", HEADER, SOURCE, TEST / "Replay.cpp"])
    if args.check == "compile":
        WORK.mkdir(parents=True, exist_ok=True)
        run([*CXX, "-MMD", "-MF", WORK / "LcdView.d", "-c", SOURCE, "-o", WORK / "LcdView.o"])
        run([*CXX, "-MMD", "-MF", WORK / "Replay.d", "-c", TEST / "Replay.cpp", "-o", WORK / "Replay.o"])
        run(["c++", WORK / "Replay.o", WORK / "LcdView.o", "-Wl,--start-group",
             *[SDK / x for x in ("libcorelib.a", "libpresonus_core_allocator.a",
                                 "libpresonus_png.a", "libpresonus_zlib.a")],
             "-Wl,--end-group", "-pthread", "-ldl", "-o", replay])
    if args.check == "symbols":
        rows = subprocess.check_output(["nm", "--defined-only", WORK / "LcdView.o"], text=True)
        symbols = {row.split()[-1] for row in rows.splitlines()}
        if fixture["variant"].endswith("construct"):
            resolved = original.replace("ENS1_8Portable8RootView10RenderModeE",
                                        "ENS1_8Portable12RootViewBase10RenderModeE")
            assert original not in symbols and resolved in symbols
            print("Original:", original, "Portable:", resolved, "Declaration pending")
        else:
            assert original in symbols
            print("Exact original:", original)
    if args.check == "replay":
        if args.exe is None:
            assert generate() == fixture
        for case in fixture["cases"]:
            command = [replay, fixture["variant"], *map(str, case["arguments"])]
            output = subprocess.check_output(command, text=True)
            assert list(map(int, output.split())) == case["observation"], (command, output, case)
        print(f"{TASK}: {len(fixture['cases'])} sealed native and portable cases")


if __name__ == "__main__":
    main()
