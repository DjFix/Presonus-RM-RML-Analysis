"""Compile Linux role inputs and compare real C++ observations with ARM traces."""

import argparse
import hashlib
import json
from pathlib import Path
import shlex
import struct
import subprocess

MANAGER = "uc-library/src/Presonus/DisplayManagerInstance.cpp"
HEADER = "uc-library/include/presonus/surface/DisplayManager.hpp"
WRAPPERS = ["-Wl,--wrap=_Znwm", "-Wl,--wrap=_ZdlPv", "-Wl,--wrap=_ZdlPvm"]


def hash_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(argv, **kwargs):
    argv = list(map(str, argv))
    print(shlex.join(argv), flush=True)
    return subprocess.run(argv, check=True, text=True, **kwargs)


def observed_symbols(path):
    output = run(["nm", "--defined-only", path], capture_output=True).stdout
    return {line.split()[-1] for line in output.splitlines() if line.split()}


def compile_role(build, scratch, here):
    commands = json.loads((build / "compile_commands.json").read_text())
    role_dir = build.parent.parent.parent
    scratch.mkdir(parents=True, exist_ok=True)

    def compile_source(path, output, command_template=None):
        source = command_template or path
        command = next(row for row in commands
                       if row["file"] == str(role_dir / source))
        argv = shlex.split(command["command"])
        argv[argv.index("-o") + 1] = str(output)
        argv[argv.index("-c") + 1] = str(Path(path).resolve())
        argv = [item.replace("-I" + str(role_dir), "-I" + str(Path.cwd()))
                for item in argv]
        run(argv + ["-MD", "-MF", str(output.with_suffix(".d"))])
        return output

    def link(template, exe, test, objects, wraps=()):
        argv = shlex.split((build / "CMakeFiles" / (template + ".dir") /
                            "link.txt").read_text())
        argv = [x for x in argv if "--dependency-file=" not in x]
        argv[argv.index("-o") - 1:argv.index("-o")] = [test, *objects]
        argv[argv.index("-o") + 1] = exe
        run(argv + list(wraps), cwd=build)

    manager = compile_source(MANAGER, scratch / "manager.o")
    providers = [compile_source(f"uc-library/src/Presonus/{name}.cpp",
                                scratch / f"{name}.o")
                 for name in ("LcdView", "DisplayCommandList")]
    role_name = "recovery_real10_g10_s01"
    previous = "uc-library/tests/recovery/real10_g10_s01/Replay.cpp"
    test = compile_source(here / "Replay.cpp", scratch / "replay.o", previous)
    exe = scratch / "replay"
    link(role_name, exe, test, [manager, *providers], WRAPPERS)
    return manager, exe, compile_source, link, providers


def regressions(build, scratch, manager, compile_source, link, providers):
    cases = {}
    receivers = [compile_source(f"uc-library/src/Presonus/{name}.cpp",
                                scratch / f"{name}.o")
                 for name in ("DisplayManagerTouch", "DisplayManagerFlush")]
    for group, ids in (("real10_g10_s", (1, 2, 3)),
                       ("cycle20_g05_s", (6, 7, 8, 9))):
        for i in ids:
            name = f"{group}{i:02}"
            target = next((p.parent.name.removesuffix(".dir")
                           for p in (build / "CMakeFiles").glob("*/link.txt")
                           if f"/{name}/Replay.cpp.o" in p.read_text()), None)
            if target is None:
                raise RuntimeError(f"No canonical replay target for {name}")
            test_dir = Path("uc-library/tests/recovery") / name
            exe = scratch / name
            test = compile_source(test_dir / "Replay.cpp", scratch / f"{name}.o")
            link(target, exe, test, [manager, *providers, *receivers])
            result = run([exe], capture_output=True)
            cases[name] = result.stdout.splitlines()
            fixture = json.loads((test_dir / "fixtures.json").read_text())
            if group == "real10_g10_s":
                expected = [f"{case['views']} {int(case['storage'])} "
                            f"{case['outer_delete']} 1" for case in fixture["cases"]]
                if cases[name] != expected:
                    raise RuntimeError(f"Previous lifecycle regression in {name}")
            else:
                observations = fixture["originals"][0]["observations"]
                expected = ["no-effect" for row in observations
                            if not (row["calls"] or row["object_writes"]
                                    or row["receiver_disposed"])]
                if cases[name] != expected or len(expected) != len(observations):
                    raise RuntimeError(f"Previous receiver regression in {name}")
    name = "surface_display_color_flush"
    exe = scratch / name
    test = compile_source(f"uc-library/tests/{name}.cpp", scratch / f"{name}.o")
    link(name, exe, test, [manager, *providers, *receivers])
    baseline = run([build / name], capture_output=True)
    current = run([exe], capture_output=True)
    if current.stdout != baseline.stdout or current.stderr != baseline.stderr:
        raise RuntimeError("Previous borrowed LCD flush replay differs")
    cases[name] = current.stdout.splitlines()
    run(["uc-library/.venv/bin/python", "-B",
         "uc-library/tests/recovery/ranked09/display/check_symbols.py", manager])
    return cases


def replay(here):
    parser = argparse.ArgumentParser()
    parser.add_argument("--role-build", type=Path)
    parser.add_argument("--scratch", type=Path)
    parser.add_argument("--exe", type=Path)
    parser.add_argument("--object", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--regressions", action="store_true")
    parser.add_argument("--symbols-only", action="store_true")
    args = parser.parse_args()
    fixture_path = here / "fixtures.json"
    fixture = json.loads(fixture_path.read_text())
    if args.role_build:
        manager, exe, compile_source, link, providers = compile_role(
            args.role_build.resolve(), args.scratch.resolve(), here)
    else:
        manager, exe = args.object.resolve(), args.exe.resolve()
    required = {fixture["original"]["mangled"]}
    if args.role_build:
        commands = json.loads(
            (args.role_build / "compile_commands.json").read_text())
        manager_recipes = [row["output"] for row in commands
                           if row["file"].endswith("/" + MANAGER)]
        if manager_recipes != [
            "CMakeFiles/presonus_cs18_objects.dir/src/Presonus/DisplayManagerInstance.cpp.o"
        ]:
            raise RuntimeError(f"Unexpected role compile recipes: {manager_recipes}")
        rm_symbols = observed_symbols(args.role_build / "libpresonus_rm_components.a")
        if required & rm_symbols:
            raise RuntimeError("CS18-only constructor leaked into RM archive")
    else:
        manager_recipes = []

    if not required <= observed_symbols(manager):
        raise RuntimeError("Missing exact DisplayManager constructor symbol")
    if args.symbols_only:
        return

    vectors, expected = [], []
    for case in fixture["cases"]:
        fields = struct.unpack("<5IiBB6s", bytes.fromhex(case["specification_hex"]))[:8]
        vectors.append(" ".join(map(str, fields)))
        views = [x for x in case["events"] if x["event"] == "view_c1"]
        actual_fields = [*fields, int(case["singleton_observed"]),
                         bool(case["command_pointer"]), len(views)]
        for view in views:
            actual_fields.extend([*view["rect"], view["format"], view["render"]])
        actual_fields.extend([len(views), bool(case["command_pointer"]), 1, 1])
        expected.append(" ".join(str(int(field)) for field in actual_fields))
    output = run([exe], input="\n".join(vectors) + "\n", capture_output=True)
    if output.stdout.splitlines() != expected:
        raise RuntimeError(f"Portable observations differ from ARM/provider expectations\n"
                           f"{output.stdout}\nExpected:\n" + "\n".join(expected))
    previous = (regressions(args.role_build.resolve(), args.scratch.resolve(),
                            manager, compile_source, link, providers)
                if args.regressions else {})
    result = dict(success=True, original=fixture["original"], scope=fixture["scope"],
                  native_cases=len(fixture["cases"]), portable_cases=len(expected),
                  object_sha256=hash_file(manager), executable_sha256=hash_file(exe),
                  fixture_sha256=hash_file(fixture_path),
                  source_hashes={path: hash_file(path) for path in (MANAGER, HEADER)},
                  replay_producer_sha256=hash_file(__file__),
                  native_producer_sha256=fixture["producer_sha256"],
                  observed_symbols=sorted(required), previous_replays=previous,
                  local_role_compile_recipes=manager_recipes,
                  portable_observations=output.stdout.splitlines())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(f"PASS {len(expected)} C++ constructor cases and {len(previous)} prior replays")


if __name__ == "__main__":
    replay(Path(__file__).parent)
