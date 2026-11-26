"""Build the Linux probe and compare it to independently replayed ARM fixtures."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess

SOURCE = Path("uc-library/src/Presonus/Mixer/FxTypeFormatter.cpp")
NUMBER = SOURCE.with_name("NumberPrepender.cpp")
TESTS = Path("uc-library/tests/recovery")
SCRATCH = Path("temp/recovery-work/fxtype-linux-checks")
FORMATTER = "uc-library/.venv/bin/clang-format"
WRAP_DELETE = "-Wl,--wrap=_ZdlPv,--wrap=_ZdlPvm"
WRAP_ADD = "-Wl,--wrap=_ZN4Core17FormatterRegistry3addEPNS_9FormatterE"
CXX = ["g++", "-std=c++20", "-Iuc-library/include", "-Ithird_party/ccl-framework",
       "-Wno-multichar"]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def version(argv):
    return subprocess.check_output(argv, text=True).splitlines()[0]


def compare(task, fixture, executable, optimized=False):
    rows = json.loads(fixture.read_text())
    matches = []
    executable = executable.resolve()
    for row in rows:
        original = row["original"]
        if task.endswith("register_fxtype"):
            registrations = sum(event["routine"] == "add" for event in row["effects"])
            for case in row["printing"]["cases"]:
                value, = struct.unpack("<f", struct.pack("<I", case["input_value"]))
                output = subprocess.check_output([executable, str(value), str(case["capacity"])], text=True)
                expected = f"{registrations} {row['name']} {row['scan']}\n{case['output_hex']}\n"
                assert output == expected, (original["role"], case, output)
                matches.append({"role": original["role"], "value": value,
                                "capacity": case["capacity"], "observed": output.splitlines()})
        else:
            output = subprocess.check_output([executable], text=True)
            deleting = task.endswith("deleting_destroy")
            if deleting:
                assert row["allocation_after_d0"] == row["receiver"]
                expected_count = sum(event[1] == row["receiver"] and event[0] == row["events"][-1][0]
                                     for event in row["events"])
            else:
                expected_count = row["deallocation_count"]
            traces = [list(map(int, line.split())) for line in output.splitlines()]
            contexts = ["typed delete", "virtual base-pointer delete"] if deleting else ["explicit complete destructor"]
            assert len(traces) == len(contexts)
            for context, (observed_count, restored_vptr) in zip(contexts, traces):
                assert observed_count == expected_count
                if not optimized:
                    assert restored_vptr == 1, (original["role"], context, output)
                matches.append({"role": original["role"], "context": context,
                                "deallocations": observed_count, "core_vptr_observed": bool(restored_vptr)})
    print(f"Matched {len(matches)} Linux observations against original ARM fixtures")
    return matches


def fixture_originals(fixture):
    return [row["original"] for row in json.loads(fixture.read_text())]


def symbols(obj, fixture):
    names = {row["mangled"] for row in fixture_originals(fixture)}
    lines = subprocess.check_output(["nm", "--defined-only", obj], text=True).splitlines()
    matches = sorted(line for line in lines if line.split()[-1] in names and line.split()[-2] == "T")
    assert {line.split()[-1] for line in matches} == names, (obj, names, matches)
    print("\n".join(matches))
    return matches


def build(task, sdk, optimized):
    folder = SCRATCH / task / ("release" if optimized else "diagnostic")
    folder.mkdir(exist_ok=True, parents=True)
    env = os.environ | {"TMPDIR": str(folder.resolve())}
    obj, executable = folder / "FxTypeFormatter.o", folder / "Replay"
    wrap = WRAP_ADD if task.endswith("register_fxtype") else WRAP_DELETE
    comp = CXX + (["-O3"] if optimized else ["-O0"])
    archives = [sdk / "lib" / name for name in ("libcorelib.a", "libpresonus_core_allocator.a")]
    commands = [
        [*comp, "-c", SOURCE, "-o", obj],
        [*comp, TESTS / task / "Replay.cpp", obj, NUMBER, wrap, "-Wl,--start-group", *archives,
         "-Wl,--end-group", "-pthread", "-o", executable],
    ]
    for argv in commands:
        print(" ".join(map(str, argv)), flush=True)
        subprocess.run(argv, env=env, check=True)
    log = folder / "build.json"
    log.write_text(json.dumps({"argv": [[str(x) for x in argv] for argv in commands],
                               "core_archives": {str(archive): sha(archive) for archive in archives},
                               "compiler": version(["g++", "--version"]),
                               "executed_successfully": True}, indent=2) + "\n")


def main(task):
    folder = TESTS / task
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("compile", "symbols", "replay"))
    parser.add_argument("--sdk", type=Path)
    parser.add_argument("--fixtures", type=Path, default=folder / "fixtures.json")
    parser.add_argument("--exe", type=Path)
    parser.add_argument("--optimized", action="store_true")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    build_dir = SCRATCH / task / ("release" if args.optimized else "diagnostic")
    obj = build_dir / "FxTypeFormatter.o"
    if args.mode == "compile":
        assert args.sdk
        build(task, args.sdk, args.optimized)
        return
    if args.mode == "symbols":
        symbols(obj, args.fixtures)
        return
    executable = args.exe or build_dir / "Replay"
    observations = compare(task, args.fixtures, executable, args.optimized)
    if args.out:
        proof = {"observations": observations, "case_count": len(observations),
                 "build": json.loads((build_dir / "build.json").read_text()),
                 "compiled_mangled_names_matched": True, "verified_symbols": symbols(obj, args.fixtures),
                 "cpp_differential_passed": True, "object_sha256": sha(obj),
                 "executable_sha256": sha(executable), "fixture_sha256": sha(args.fixtures),
                 "format_version": version([FORMATTER, "--version"])}
        args.out.write_text(json.dumps(proof, indent=2) + "\n")


if __name__ == "__main__":
    main(Path(__file__).parent.name)
