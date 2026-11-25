"""Compile the local replay and compare the portable trace to ARM observations."""
import argparse
import json
import os
from pathlib import Path
import subprocess

HERE = Path(__file__).parent
IMPLEMENTATION = "uc-library/src/Presonus/MappingTableItem.cpp"
HEADER = "uc-library/include/presonus/MappingTable.hpp"
CORE = "third_party/ccl-framework/core/"
SUPPORT = [
    "uc-library/src/Presonus/Panel/SwitchControl.cpp",
    "uc-library/src/Presonus/Panel/SwitchDispatch.cpp",
    "uc-library/src/Presonus/Panel/LEDControlLifecycle.cpp",
    "uc-library/src/Presonus/Panel/control.cpp",
    "uc-library/src/Presonus/Panel/param_edit_handler.cpp",
    "uc-library/src/surface_panel/LEDState.cpp",
    "uc-library/src/portable/panel/SwitchParameterGateway.cpp",
    "uc-library/src/portable/panel/SwitchDispatchParameterGateway.cpp",
    "uc-library/src/Presonus/DICE/PacketClockGateway.cpp",
    *[CORE + path for path in [
        "portable/coreparams.cpp", "portable/coreattributes.cpp",
        "platform/shared/coreplatformtime.cpp",
        "platform/shared/posix/coreatomicstack.posix.cpp",
        "platform/shared/posix/corethread.posix.cpp",
        "public/coreinterpolator.cpp", "public/coreformatter.cpp",
    ]],
]
BASE = ["g++", "-std=c++17", "-Ulinux", "-DNDEBUG", "-Wno-multichar",
        "-ffunction-sections", "-fdata-sections",
        "-Iuc-library/include", "-Ithird_party/ccl-framework"]
METHODS = {
    "setenabled": "_ZN8Presonus12MappingTable4Item10setEnabledEb",
    "setfulloff": "_ZN8Presonus12MappingTable4Item10setFullOffEv",
    "setimmediate": "_ZN8Presonus12MappingTable4Item12setImmediateEb",
}


def compile_replay(output):
    output.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, TMPDIR=str(output.absolute()))
    commands = [
        [*BASE, "-c", IMPLEMENTATION, "-o", str(output / "item.o")],
        [*BASE, "-Wl,--gc-sections", str(HERE / "Replay.cpp"),
         str(output / "item.o"), *SUPPORT, "-o", str(output / "replay")],
    ]
    for argv in commands:
        print(json.dumps(argv), flush=True)
        subprocess.run(argv, check=True, env=env)


def symbols(object_path, method):
    argv = ["nm", "--defined-only", str(object_path)]
    output = subprocess.check_output(argv, text=True)
    lines = [line for line in output.splitlines()
             if line.split()[-1:] == [METHODS[method]]]
    if len(lines) != 1 or lines[0].split()[-2] != "T":
        raise ValueError(f"Expected one exported {METHODS[method]} in {object_path}")
    print(lines[0])


def replay(executable, fixture, method):
    evidence = json.loads(fixture.read_text())
    if evidence["original"]["mangled"] != METHODS[method]:
        raise ValueError("Fixture and requested symbol disagree")
    input_lines, expected = [], []
    for row in evidence["rows"]:
        steps = row["steps"]
        input_lines.append(" ".join(str(v) for v in
                                    [row["kind"], row["attached"], row["initial"], len(steps)]))
        for step in steps:
            input_lines.append(str(step["input"]))
            # ARM direct call entries are recorded by the oracle, while the
            # portable driver compares their provider state and virtual effects.
            events = [event for event in step["trace"] if event[0] not in (3, 4)]
            expected.append([step["state"], *(v for event in events for v in event)])
    proc = subprocess.run([str(executable.resolve()), method], check=True,
                          input="\n".join(input_lines) + "\n",
                          text=True, capture_output=True)
    actual = [list(map(int, line.split())) for line in proc.stdout.splitlines()]
    if actual != expected:
        for i, (want, got) in enumerate(zip(expected, actual)):
            if want != got:
                raise ValueError(f"case step {i}: expected {want}, got {got}")
        raise ValueError(f"expected {len(expected)} steps, received {len(actual)}")
    print(f"portable {method}: {len(evidence['rows'])} cases, {len(expected)} calls")


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("compile")
    build.add_argument("out", type=Path)
    nm = sub.add_parser("symbols")
    nm.add_argument("object", type=Path)
    nm.add_argument("method", choices=METHODS)
    execute = sub.add_parser("replay")
    execute.add_argument("exe", type=Path)
    execute.add_argument("fixture", type=Path)
    execute.add_argument("method", choices=METHODS)
    execute.add_argument("--packet", type=Path)
    execute.add_argument("--object", type=Path)
    args = parser.parse_args()
    if args.command == "compile":
        compile_replay(args.out)
    elif args.command == "symbols":
        symbols(args.object, args.method)
    else:
        if args.packet:
            import sys
            subprocess.run([sys.executable, "-B", str(HERE / "native.py"),
                            str(args.packet), str(args.fixture)], check=True)
        if args.object:
            symbols(args.object, args.method)
        replay(args.exe, args.fixture, args.method)


if __name__ == "__main__":
    main()
