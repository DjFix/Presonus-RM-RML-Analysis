"""Rerun bounded host and firmware checks for a MidiEndpointRegistry packet."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

PREFIX = "sqlite02_midiendpointregistry_"
TESTS = Path("uc-library/tests/recovery")
SHARED = TESTS / (PREFIX + "complete_construct")
SOURCE = Path("uc-library/src/Presonus/UC/MidiEndpointRegistry.cpp")

def read_json(path):
    return json.loads(path.read_text())

def native_rows(observation):
    return [case["comparison"] for row in observation["observations"] for case in row["cases"]]

def portable(executable, fixture):
    data = read_json(fixture)
    cases = data["cases"]
    assert cases and all(isinstance(value, int) for row in cases for value in row)
    inputs = "\n".join([str(len(cases)), *(" ".join(map(str, row)) for row in cases)]) + "\n"
    subprocess.run([executable, data["task"]], check=True, text=True, input=inputs)

def run(argv):
    result = subprocess.run(argv, check=True, text=True, capture_output=True)
    print(" ".join(map(str, argv)), flush=True)
    print(result.stdout, end="")
    return dict(argv=list(map(str, argv)), cwd=str(Path.cwd()),
                returncode=result.returncode, stdout=result.stdout, stderr=result.stderr)

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def compile_replay(destination):
    destination.mkdir(parents=True, exist_ok=True)
    records = []
    objects = []
    for path in (SOURCE, SHARED / "Replay.cpp"):
        objects.append(destination / (path.stem + ".o"))
        depfile = destination / (path.stem + ".d")
        argv = ["c++", "-std=c++20", "-g", "-O0", "-Iuc-library/include",
                "-Ithird_party/ccl-framework", "-MMD", "-MF", depfile,
                "-MT", objects[-1], "-c", path, "-o", objects[-1]]
        records.append(dict(**run(argv), source=str(path), source_sha256=digest(path),
                            object=str(objects[-1]), object_sha256=digest(objects[-1]),
                            depfile=str(depfile), depfile_sha256=digest(depfile)))
    argv = ["c++", *objects, "-Wl,--wrap=_Znam,--wrap=_ZdaPv",
            "-o", destination / "replay"]
    records.append(run(argv))
    (destination / "compile-audit.json").write_text(json.dumps(records, indent=2) + "\n")

def symbols(destination, observation):
    names = {row["original"]["mangled"]
             for row in read_json(observation)["observations"]}
    for path in (destination / (SOURCE.stem + ".o"), destination / "replay"):
        table = subprocess.check_output(["nm", "--defined-only", path], text=True)
        for name in sorted(names):
            entries = [line for line in table.splitlines() if line.split()[-1] == name]
            assert len(entries) == 1, (path, name, entries)
            print(path, entries[0])

def native(destination, observation, fixture, root):
    destination.mkdir(parents=True, exist_ok=True)
    fresh = destination / "fresh-native.json"
    task = read_json(fixture)["task"]
    run([sys.executable, SHARED / "native.py", "--firmware-root", root,
         "--packet-root", "temp/recovery-work/sqlite-issued/packet", "--output",
         fresh, "--task", task])
    assert fresh.read_bytes() == observation.read_bytes()
    assert native_rows(read_json(fresh)) == read_json(fixture)["cases"]
    print("Fresh native results match frozen observation and portable fixture:", digest(fresh))

def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    compile_parser = subparsers.add_parser("compile")
    compile_parser.add_argument("destination", type=Path)
    symbol_parser = subparsers.add_parser("symbols")
    symbol_parser.add_argument("destination", type=Path)
    symbol_parser.add_argument("observation", type=Path)
    portable_parser = subparsers.add_parser("portable")
    portable_parser.add_argument("executable", type=Path)
    portable_parser.add_argument("fixture", type=Path)
    native_parser = subparsers.add_parser("native")
    native_parser.add_argument("destination", type=Path)
    native_parser.add_argument("observation", type=Path)
    native_parser.add_argument("fixture", type=Path)
    native_parser.add_argument("firmware_root", type=Path)
    args = parser.parse_args()
    if args.command == "compile":
        compile_replay(args.destination)
    elif args.command == "symbols":
        symbols(args.destination, args.observation)
    elif args.command == "portable":
        portable(args.executable, args.fixture)
    else:
        native(args.destination, args.observation, args.fixture, args.firmware_root)

if __name__ == "__main__":
    main()
