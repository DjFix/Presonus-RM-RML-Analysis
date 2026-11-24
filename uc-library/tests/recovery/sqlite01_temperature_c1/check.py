"""Build and audit the Linux replay, or compare the canonical CTest executable."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[4]
TASK = Path(__file__).parent.name
VARIANT = TASK.rsplit("_", 1)[1].upper()
PANEL = Path("uc-library/src/Presonus/Panel")
FIRMWARE_SYMBOL_PREFIX = "_ZN8Presonus5Panel18TemperatureControl"
CONTROL = "_ZN8Presonus5Panel7ControlC2Ei"
SYMBOLS = [f"{FIRMWARE_SYMBOL_PREFIX}{variant}Ei" for variant in ("C1", "C2")]


def command(argv, **kwargs):
    argv = [str(arg) for arg in argv]
    print(json.dumps(argv), flush=True)
    return subprocess.run(argv, cwd=ROOT, check=True, text=True, **kwargs)


def compile_replay(build, work):
    work.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, TMPDIR=str(work.resolve()))
    sdk = build / "upstream-core/sdk"
    common = [
        "/usr/bin/c++", "-DPRESONUS_HAS_UPSTREAM_CORE=1", "-DCORE_USE_OPENSSL=1",
        "-Iuc-library/include", "-isystem", sdk / "include/presonus-core-5",
        "-pthread", "-Ulinux",
    ]
    rtti = ["-frtti", "-fno-lto", "-fno-fast-math", "-ffp-contract=off"]
    temperature = work / "TemperatureControl.o"
    control = work / "control.o"
    replay = work / "Replay.o"
    command([*common, "-O3", "-DNDEBUG", *rtti, "-c", PANEL / "TemperatureControl.cpp", "-o", temperature], env=env)
    command([*common, "-O3", "-DNDEBUG", "-c", PANEL / "control.cpp", "-o", control], env=env)
    command([*common, "-O0", *rtti, "-c", Path(__file__).with_name("Replay.cpp"), "-o", replay], env=env)

    provider_objects = sorted((build / "CMakeFiles/panel_hal_core_rtti.dir").rglob("*.cpp.o"))
    assert sorted(path.name for path in provider_objects) == [
        "coreatomicstack.posix.cpp.o", "coreattributes.cpp.o", "coreparams.cpp.o",
    ]
    dns = build.parent / "external-dev/usr/lib/x86_64-linux-gnu"
    command([
        "/usr/bin/c++", "-pthread", replay, temperature, control, *provider_objects,
        build / "libpresonus_uc.a", sdk / "lib/libcorelib.a",
        sdk / "lib/libpresonus_core_allocator.a", sdk / "lib/libpresonus_png.a",
        sdk / "lib/libpresonus_zlib.a", "-lssl", "-lcrypto",
        f"-Wl,-rpath,{dns}", dns / "libdns_sd.so", "-ldl",
        build / "private-glibc29-provider/libpresonus_private_glibc29.a",
        "-lm", "-o", work / "Replay",
    ], env=env)
    providers = [*provider_objects, build / "libpresonus_uc.a", sdk / "lib/libcorelib.a",
                 sdk / "lib/libpresonus_core_allocator.a", sdk / "lib/libpresonus_png.a",
                 sdk / "lib/libpresonus_zlib.a", dns / "libdns_sd.so",
                 build / "private-glibc29-provider/libpresonus_private_glibc29.a",
                 Path("/usr/lib/x86_64-linux-gnu/libssl.so"), Path("/usr/lib/x86_64-linux-gnu/libcrypto.so")]
    print(json.dumps({"link_provider_sha256": {
        str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in providers
    }}, sort_keys=True))


def symbol_rows(object_path, *flags):
    out = command(["nm", *flags, object_path], capture_output=True).stdout
    return {row.split()[-1]: row for row in out.splitlines() if row.split()}


def check_symbols(object_path, replay_object=None):
    defined = symbol_rows(object_path, "--defined-only")
    undefined = symbol_rows(object_path, "--undefined-only")
    for name in SYMBOLS:
        assert defined[name].split()[-2] == "T", defined
        print(defined[name])
    assert CONTROL in undefined
    print(undefined[CONTROL])
    if replay_object:
        calls = symbol_rows(replay_object, "--undefined-only")
        for name in SYMBOLS:
            assert name in calls
            print(calls[name])


def observe(exe, mode, tag):
    out = subprocess.run([str(exe.resolve()), mode, str(tag)], check=True, text=True, capture_output=True)
    return [int(value) for value in out.stdout.split()]


def replay(exe, fixtures):
    raw = fixtures.read_bytes()
    data = json.loads(raw)
    assert data["task_id"] == TASK
    originals = data["originals"]
    assert {entry["original"]["role"] for entry in originals} == {"client", "server"}
    observations = []
    for entry in originals:
        original = entry["original"]
        assert original["mangled"] == f"{FIRMWARE_SYMBOL_PREFIX}{VARIANT}Ei"
        for case in entry["cases"]:
            tag = case["input_tag"]
            expected = case["common_state"] + [1, 1]
            states = {mode: observe(exe, mode, tag) for mode in ("control", "tagged", VARIANT)}
            assert all(state == expected for state in states.values()), (original["role"], tag, states, expected)
            observations.append({
                "elf_sha256": original["elf"], "role": original["role"], "input_tag": tag,
                "observed": states,
            })
    return {
        "task_id": TASK, "fixture_sha256": hashlib.sha256(raw).hexdigest(),
        "cases": len(observations), "observations": observations,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("compile", "symbols", "replay"))
    parser.add_argument("--work", type=Path)
    parser.add_argument("--build", type=Path)
    parser.add_argument("--exe", type=Path)
    parser.add_argument("--object", type=Path)
    parser.add_argument("--fixtures", type=Path, default=Path(__file__).with_name("fixtures.json"))
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.action == "compile":
        compile_replay(args.build, args.work)
    elif args.action == "symbols":
        check_symbols(args.object or (args.work / "TemperatureControl.o"),
                      args.work / "Replay.o" if args.work else None)
    else:
        result = replay(args.exe or (args.work / "Replay"), args.fixtures)
        if args.out:
            args.out.write_text(json.dumps(result, indent=2) + "\n")
        print(f"{TASK}: {result['cases']} role/tag cases, native and actual Control composition agree")


if __name__ == "__main__":
    main()
