"""Compile the local lifecycle port or compare its Linux replay to a fixture."""

import argparse
import json
from pathlib import Path
import shlex
import subprocess

TEST = Path(__file__)
SOURCE = Path("uc-library/src/Presonus/Surface/MuteGroupsComponent.cpp")
WRAPS = [
    "_Znwm", "_ZdlPv", "_ZdlPvm", "_ZN8Presonus10DelayTimerC1Ef",
    "_ZN8Presonus10DelayTimerD1Ev", "_ZN4Core8Portable9ComponentD2Ev",
    "_ZN8presonus4dice19packetClockRawTicksEv",
]


def run(argv, **kwargs):
    print(shlex.join(str(arg) for arg in argv), flush=True)
    return subprocess.run(argv, check=True, text=True, **kwargs)


def compile_check(build, out):
    build, out = build.resolve(), out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    flagfile = build / "CMakeFiles/presonus_cs18_objects.dir/flags.make"
    flags = []
    for line in flagfile.read_text().splitlines():
        if line.startswith(("CXX_DEFINES =", "CXX_FLAGS =")):
            flags.extend(shlex.split(line.split("=", 1)[1]))
        elif line.startswith("CXX_INCLUDES ="):
            includes = shlex.split(line.split("=", 1)[1])
            flags.extend(includes)
            flags[flags.index(next(f for f in includes if f.startswith("-I")))] = (
                "-I" + str(Path("uc-library/include").resolve()))
    flags += ["-fno-lto", "-fno-fast-math", "-ffp-contract=off", "-fno-rtti"]
    for src, name in ((SOURCE, "Mute.o"), (TEST.with_name("Replay.cpp"), "Replay.o")):
        run(["/usr/bin/c++", *flags, "-MD", "-c", src, "-o", out / name])
    linkfile = build / "CMakeFiles/MappingDestructorLifecycleReplay.dir/link.txt"
    command = shlex.split(linkfile.read_text())
    libraries = command[command.index("libpresonus_cs18_components.a"):]
    run(["/usr/bin/c++", *(f"-Wl,--wrap={name}" for name in WRAPS),
         out / "Replay.o", out / "Mute.o", "-o", out / "Replay", *libraries], cwd=build)


def symbol_check(obj, name):
    result = run(["nm", "--defined-only", obj], stdout=subprocess.PIPE)
    rows = [line for line in result.stdout.splitlines()
            if line.split()[-1:] == [name] and line.split()[-2:-1] == ["T"]]
    assert len(rows) == 1, (name, rows)
    print(rows[0])


def replay(exe, fixture):
    body = json.loads(fixture.read_text())
    variant = body["original"]["mangled"][-4:-2]
    expected = body["output"]
    lines = [f"configuration {expected['feedback']} {int(expected['empty_name'])}"]
    for (_, seconds), state in zip(expected["timer_inputs"], expected["states"], strict=True):
        lines.append("timer " + " ".join(map(str, [seconds, *state])))
    lines.extend(expected.get("events", []))
    for roster in ("default", "borrowed"):
        output = run([exe.resolve(), variant, roster], stdout=subprocess.PIPE).stdout
        assert output.splitlines() == lines, (variant, roster, output, lines)
    print(f"{variant}: 2 portable cases matched native lifecycle and timer inputs/state")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(required=True)
    build = sub.add_parser("compile")
    build.add_argument("--build", required=True, type=Path)
    build.add_argument("--out", required=True, type=Path)
    build.set_defaults(handler=lambda a: compile_check(a.build, a.out))
    symbol = sub.add_parser("symbol")
    symbol.add_argument("--object", required=True, type=Path)
    symbol.add_argument("--name", required=True)
    symbol.set_defaults(handler=lambda a: symbol_check(a.object, a.name))
    test = sub.add_parser("replay")
    test.add_argument("--exe", required=True, type=Path)
    test.add_argument("--fixture", required=True, type=Path)
    test.set_defaults(handler=lambda a: replay(a.exe, a.fixture))
    args = parser.parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()
