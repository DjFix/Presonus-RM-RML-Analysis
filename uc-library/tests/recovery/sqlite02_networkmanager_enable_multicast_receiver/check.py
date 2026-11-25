"""Compile and compare this bounded NetworkManager replay with native fixtures."""

import argparse
import hashlib
import json
from pathlib import Path
import shlex
import subprocess

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
TASK = HERE.name
SOURCE = "uc-library/src/Presonus/UC/NetworkManagerNextServices.cpp"
SYMBOL = "_ZN8Presonus2UC14NetworkManager23enableMulticastReceiverEb"
WORK = ROOT / "temp/recovery-work/sqlite02-local" / TASK
OBJECT = WORK / "NetworkManagerNextServices.o"
EXE = WORK / "Replay"
WRAP = ('_ZN8Presonus2UC17ConnectionHandler22getMulticastConnectionEv', '_ZN8Presonus2UC19MulticastConnection11addReceiverEPNS0_18IMulticastReceiverE', '_ZN8Presonus2UC19MulticastConnection14removeReceiverEPNS0_18IMulticastReceiverE')
SUPPORT = ('ConnectionHandlerQueries', 'MulticastSocketServices')


def run(argv, **kwargs):
    args = [str(arg) for arg in argv]
    print(shlex.join(args), flush=True)
    return subprocess.run(args, check=True, **kwargs)


def compile_replay():
    build = next(
        directory / "temp/core-upstream/root-integration-01"
        for directory in (ROOT, *ROOT.parents)
        if (directory / "temp/core-upstream/root-integration-01/compile_commands.json").is_file()
    )
    sdk = build / "upstream-core/sdk"
    library = sdk / "lib"
    WORK.mkdir(parents=True, exist_ok=True)
    compiler = [
        "/usr/bin/c++", "-std=c++17", "-DCORE_USE_OPENSSL=1", "-DNDEBUG=1",
        "-DPRESONUS_HAS_UPSTREAM_CORE=1", "-I", ROOT / "uc-library/include",
        "-isystem", sdk / "include/presonus-core-5", "-pthread", "-Ulinux", "-O2",
    ]
    run([*compiler, "-MD", "-MF", OBJECT.with_suffix(".d"), "-c", ROOT / SOURCE, "-o", OBJECT])
    linked = [OBJECT]
    for source in SUPPORT:
        obj = WORK / (source + ".o")
        run([*compiler, "-MD", "-MF", obj.with_suffix(".d"), "-c",
             ROOT / "uc-library/src/Presonus/UC" / (source + ".cpp"), "-o", obj])
        linked.append(obj)
    replay_object = WORK / "Replay.o"
    run([*compiler, "-MD", "-MF", replay_object.with_suffix(".d"), "-c",
         HERE / "Replay.cpp", "-o", replay_object])
    external = build.parent / "external-dev/usr/lib/x86_64-linux-gnu"
    run([
        *compiler, replay_object, *linked, *("-Wl,--wrap=" + symbol for symbol in WRAP),
        "-Wl,-rpath," + str(external), build / "libpresonus_uc.a",
        library / "libcorelib.a", library / "libpresonus_core_allocator.a",
        library / "libpresonus_png.a", library / "libpresonus_zlib.a",
        "-lssl", "-lcrypto", external / "libdns_sd.so", "-ldl",
        build / "private-glibc29-provider/libpresonus_private_glibc29.a", "-lm",
        "-o", EXE,
    ])


def check_symbols():
    result = run(["nm", "--defined-only", OBJECT], text=True, capture_output=True)
    names = [line.split()[-1] for line in result.stdout.splitlines() if line.strip()]
    assert names.count(SYMBOL) == 1, SYMBOL
    print(SYMBOL)


def replay(executable, fixtures, fixture_sha256):
    data = fixtures.read_bytes()
    assert hashlib.sha256(data).hexdigest() == fixture_sha256
    observations = json.loads(data)["observations"]
    assert {item["role"] for item in observations} == {"client", "server"}
    count = 0
    for item in observations:
        assert item["mangled"] == SYMBOL
        for case in item["cases"]:

            args = case["input"]
            calls = "".join(f" {name}:{flag}" for name, flag in case["calls"])
            expected = f"{case['final']}{calls}\n"
            result = run([executable.resolve(), *args], text=True, capture_output=True)
            assert result.stdout == expected, (result.stdout, expected, result.stderr)
            count += 1
    print(json.dumps({"case_count": count, "fixture_sha256": fixture_sha256, "passed": True}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("compile", "symbols", "replay"))
    parser.add_argument("--exe", type=Path, default=EXE)
    parser.add_argument("--fixtures", type=Path, default=HERE / "fixtures.json")
    parser.add_argument("--fixture-sha256")
    args = parser.parse_args()
    if args.phase == "compile":
        compile_replay()
    elif args.phase == "symbols":
        check_symbols()
    elif args.fixture_sha256:
        replay(args.exe, args.fixtures, args.fixture_sha256)
    else:
        parser.error("replay requires --fixture-sha256")


if __name__ == "__main__":
    main()
