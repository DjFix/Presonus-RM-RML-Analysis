"""Compare Linux painting, geometry returns and persistent draw bounds to ARM traces."""

import argparse
import json
import shutil
import subprocess
from pathlib import Path


BASE = Path(__file__).resolve().parent.relative_to(Path.cwd())
SOURCE = Path("uc-library/src/Presonus/SpectrumPainter.cpp")
OUT = Path("temp/recovery-work/sqlite02-spectrum-painter-check-v2")
CORE_BUILD = Path("/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01")
COMPILER = [
    "g++", "-O0", "-std=c++20", "-fno-rtti", "-Wno-multichar",
    "-I", "uc-library/include", "-I", "third_party/ccl-framework",
]


def command(argv):
    argv = [str(arg) for arg in argv]
    print(argv, flush=True)
    subprocess.run(argv, check=True)


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    objects = []
    for src in (SOURCE, BASE / "Replay.cpp"):
        obj = OUT / (src.name + ".o")
        command(COMPILER + ["-MMD", "-MF", obj.with_suffix(".d"), "-c", src, "-o", obj])
        objects.append(obj)
    role_archive = OUT / "libpresonus_cs18_components.a"
    shutil.copyfile(CORE_BUILD / role_archive.name, role_archive)
    command(["ar", "r", role_archive, objects[0]])
    members = subprocess.check_output(["ar", "t", role_archive], text=True).splitlines()
    assert members.count(objects[0].name) == 1
    exact_member = subprocess.check_output(["ar", "p", role_archive, objects[0].name])
    assert exact_member == objects[0].read_bytes()
    libraries = [
        "-L", CORE_BUILD / "upstream-core/sdk/lib", "-lcorelib",
        "-lpresonus_core_allocator", "-lpresonus_png", "-lpresonus_zlib",
        CORE_BUILD / "private-glibc29-provider/libpresonus_private_glibc29.a", "-ldl", "-lm",
    ]
    command(["g++", *objects, role_archive, *libraries, "-o", OUT / "Replay"])
    command([
        "g++", objects[1], role_archive, *libraries,
        "-Wl,-Map=" + str(OUT / "CS18.map"), "-o", OUT / "ReplayCS18",
    ])
    assert f"{role_archive}({objects[0].name})" in (OUT / "CS18.map").read_text()



def check_symbol(symbol):
    output = subprocess.check_output(
        ["nm", "--defined-only", str(OUT / "SpectrumPainter.cpp.o")], text=True
    )
    for row in output.splitlines():
        if row.split()[-1] == symbol:
            print(row)
            return
    raise SystemExit("Missing exact object symbol " + symbol)


def check_native():
    output = subprocess.check_output(
        ["uc-library/.venv/bin/python", "-B", str(BASE / "native.py")], text=True
    )
    if output != (BASE / "fixtures.json").read_text():
        raise SystemExit("Current ARM execution differs from retained fixtures")
    print("All seven ELF ranges and independent ARM observations replayed")


def lines(case):
    command, *args = case["action"]
    if command == "bind":
        args = [len(args[0]), *args[0], *args[1]]
    elif command == "paint":
        args = [*args[0], args[1]]
    return " ".join(map(str, [command, *args]))


def main():
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--build", action="store_true")
    mode.add_argument("--symbol")
    mode.add_argument("--native", action="store_true")
    parser.add_argument("--driver", "--exe", type=Path)
    parser.add_argument("--fixtures", "--fixture", type=Path)
    args = parser.parse_args()
    if args.build:
        build()
        return
    if args.symbol:
        check_symbol(args.symbol)
        return
    if args.native:
        check_native()
        return
    if args.driver is None or args.fixtures is None:
        parser.error("Provide --driver and --fixtures for portable replay")
    runs = json.loads(args.fixtures.read_text())["runs"]
    observed = subprocess.run(
        [str(args.driver.resolve())],
        input="".join("\n".join(map(lines, run)) + "\nend\n" for run in runs),
        check=True,
        capture_output=True,
        text=True,
    ).stdout.split("end\n")
    cases = [case for run in runs for case in run]
    assert len(observed) == len(cases) + 1 and not observed[-1]
    for index, (case, result) in enumerate(zip(cases, observed)):
        expected = [call for call in case["calls"] if call[0] in ("grid", "fill")]
        if case["result"] is not None:
            expected.append(["result", *case["result"]])
        expected.append(["last", *case["state"]["last"]])
        want = "".join(" ".join(map(str, call)) + "\n" for call in expected)
        if result != want:
            raise SystemExit(f"Operation {index} {case['action']}: {result!r} != {want!r}")
    print(f"{len(cases)} ARM/portable operations in {len(runs)} constructor sequences matched")


if __name__ == "__main__":
    main()
