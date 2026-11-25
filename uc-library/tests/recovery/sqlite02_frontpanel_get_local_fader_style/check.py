"""Worker compilation, ELF-symbol binding, and native/portable differential replay."""
import argparse
import json
from pathlib import Path
import shlex
import subprocess
import sys

HERE = Path(__file__).parent
SOURCE = "uc-library/src/Presonus/Panel/FrontPanelComponent.cpp"
ROLE_OBJECT = "CMakeFiles/presonus_rm_objects.dir/src/Presonus/Panel/FrontPanelComponent.cpp.o"
LINK_REPLAY = "CMakeFiles/FrontPanelCopyPasteFilterReplay.dir/link.txt"


def run(argv, **kwargs):
    return subprocess.run(argv, check=True, text=True, **kwargs)


def compile_local(build, scratch, implementation):
    scratch.mkdir(parents=True, exist_ok=True)
    root = Path.cwd()
    object_file = scratch / "FrontPanelComponent.o"
    test_object = scratch / "Replay.o"
    database = json.loads((build / "compile_commands.json").read_text())
    def compile_unit(unit, source, output):
        command = shlex.split(unit["command"])
        upstream_include = Path(unit["file"]).parents
        canonical_include = next(p / "include" for p in upstream_include
                                 if p.name == "uc-library")
        flags = ["-I" + str(root / "uc-library/include")
                 if flag == "-I" + str(canonical_include) else flag
                 for flag in command[1:command.index("-o")]]
        assert "-I" + str(root / "uc-library/include") in flags
        return [command[0], *flags, "-c", str(source), "-o", str(output)]

    front = next(x for x in database if x["output"] == ROLE_OBJECT)
    commands = [compile_unit(front, SOURCE, object_file),
                compile_unit(front, implementation, test_object)]
    provider_objects = []
    for source in ("src/Presonus/Panel/ControlRegistrarAccess.cpp",
                   "src/Presonus/Panel/control.cpp",
                   "src/surface_panel/ControlGroup.cpp",
                   "src/surface_panel/ControlHelpers.cpp"):
        provider = next(x for x in database if x["file"].endswith("/" + source))
        provider_object = scratch / (Path(source).stem + ".o")
        commands.append(compile_unit(provider, Path("uc-library") / source,
                                     provider_object))
        provider_objects.append(str(provider_object))
    link = shlex.split((build / LINK_REPLAY).read_text())
    libraries = [str(build / x) if x.endswith(".a") and not x.startswith("/") else x
                 for x in link[link.index("libpresonus_rm_components.a"):]]
    rpath = next(arg for arg in link if arg.startswith("-Wl,-rpath,"))
    commands.append([link[0], rpath, "-Wl,--gc-sections", str(test_object),
                     str(object_file), *provider_objects, *libraries,
                     "-o", str(scratch / "Replay")])
    for argv in commands:
        run(argv)
    print(json.dumps(commands, indent=2))


def symbols(obj, mangled):
    output = run(["nm", "--defined-only", str(obj)], capture_output=True).stdout
    rows = [line for line in output.splitlines()
            if line.split()[-1:] == [mangled] and line.split()[-2] == "T"]
    assert len(rows) == 1, (mangled, rows)
    print(rows[0])


def encode(roster):
    words = [len(roster)]
    for group, entries in roster:
        words.extend([group, len(entries)])
        for tag, kind, parameter in entries:
            words.extend([tag, kind, int(parameter is not None), parameter or 0])
    return " ".join(map(str, words)) + "\n"


def replay(args):
    fixtures = json.loads(args.fixture.read_text())
    verified = run([sys.executable, "-B", str(args.fixture.parent / "native.py"),
                    "--context", str(args.context), "--evidence", str(args.evidence),
                    "--firmware", str(args.firmware)], capture_output=True)
    assert fixtures == json.loads(verified.stdout), "Native fixtures changed"
    for case in fixtures["cases"]:
        actual = run([str(args.exe.resolve())], input=encode(case["roster"]),
                     capture_output=True).stdout.strip()
        assert actual == str(case["result"]), (case["name"], actual, case["result"])
    print(f"Matched {len(fixtures['cases'])} native and portable cases")


def main(test_dir):
    parser = argparse.ArgumentParser()
    subs = parser.add_subparsers(dest="command", required=True)
    cc = subs.add_parser("compile")
    cc.add_argument("--build", type=Path, required=True)
    cc.add_argument("--scratch", type=Path, required=True)
    nm = subs.add_parser("symbols")
    nm.add_argument("--object", type=Path, required=True)
    nm.add_argument("--mangled", required=True)
    test = subs.add_parser("replay")
    for arg in ("fixture", "context", "evidence", "firmware", "exe"):
        test.add_argument("--" + arg, type=Path, required=True)
    args = parser.parse_args()
    if args.command == "compile":
        compile_local(args.build, args.scratch, test_dir / "Replay.cpp")
    elif args.command == "symbols":
        symbols(args.object, args.mangled)
    else:
        replay(args)


if __name__ == "__main__":
    main(HERE)
