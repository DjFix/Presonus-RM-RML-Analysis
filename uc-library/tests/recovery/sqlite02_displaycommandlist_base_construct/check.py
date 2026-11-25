"""Compile, inspect symbols, and compare portable state with recorded ARM observations."""
import argparse
import json
from pathlib import Path
import struct
import subprocess
import sys

TEST = Path(__file__).parent
TASK = TEST.name
SOURCE = Path("uc-library/src/Presonus/DisplayCommandList.cpp")
SCRATCH = Path("temp/recovery-work") / TASK
PRODUCTION = SCRATCH / "DisplayCommandList.o"
DRIVER = SCRATCH / "Replay.o"
EXECUTABLE = SCRATCH / "Replay"
FIXTURE = TEST / "fixtures.json"


def run(argv, **kwargs):
    print(json.dumps([str(arg) for arg in argv]), flush=True)
    return subprocess.run(argv, check=True, text=True, **kwargs)


def compile_replay(provider):
    SCRATCH.mkdir(parents=True, exist_ok=True)
    flags = ["c++", "-std=c++17", "-O0", "-g", "-pthread", "-Ulinux",
             "-DCORE_USE_OPENSSL=1", "-DPRESONUS_HAS_UPSTREAM_CORE=1",
             "-Iuc-library/include", "-isystem", "third_party/ccl-framework"]
    run([*flags, "-c", SOURCE, "-o", PRODUCTION])
    run([*flags, "-c", TEST / "Replay.cpp", "-o", DRIVER])
    libraries = [
        provider / name for name in ("libcorelib.a", "libpresonus_core_allocator.a",
                                     "libpresonus_png.a", "libpresonus_zlib.a")
    ]
    run(["c++", "-pthread", PRODUCTION, DRIVER, "-o", EXECUTABLE,
         *libraries, "-lssl", "-lcrypto", "-ldl", "-lm"])


def check_symbols(fixture, object_file, driver_object):
    original = fixture["original"]["mangled"]
    defined = run(["nm", "--defined-only", object_file], capture_output=True).stdout.splitlines()
    references = run(["nm", "--undefined-only", driver_object], capture_output=True).stdout.splitlines()
    assert any(row.split()[-2:] == ["T", original] for row in defined)
    assert any(row.split()[-2:] == ["U", original] for row in references)
    print("Exact constructor definition and replay reference:", original)


def check_native(fixture):
    data = run([sys.executable, "-B", TEST / "native.py"], capture_output=True).stdout
    assert json.loads(data) == fixture
    print(f"{len(fixture['cases'])} exact ARM constructor executions and first-operation traces matched")


def decode_state(line):
    count, cursor, bitmap_count, next_bitmap_id, *entries = map(int, line.split())
    assert len(entries) == bitmap_count * 2
    return dict(count=count, auxiliary_cursor=cursor, bitmap_count=bitmap_count,
                next_bitmap_id=next_bitmap_id,
                entries=[entries[i:i+2] for i in range(0, len(entries), 2)])


def check_replay(fixture, exe):
    requested = " ".join(map(str, fixture["rect"] + fixture["rgba"] + fixture["bitmap_args"]))
    for case in fixture["cases"]:
        output = run([exe], input=requested + "\n", capture_output=True).stdout
        capacities, initial, unaffected, drawn, commands = output.splitlines()
        command_capacity, table_capacity, portable_key = map(int, capacities.split())
        constructor_writes = case["constructor_writes"]
        assert command_capacity == len([row for row in constructor_writes
                                       if 0x3FC <= row[0] < 0x107C and row[1] == 1])
        assert table_capacity == len([row for row in constructor_writes
                                     if 0x1084 <= row[0] < 0x1184 and row[1] == 4])
        assert decode_state(initial) == decode_state(unaffected) == case["initial"]
        assert case["initial"]["entries"] == []
        recorded = decode_state(drawn)
        assert recorded["entries"][0][0] == portable_key
        recorded["entries"][0][0] = fixture["bitmap_key"]
        assert recorded == case["result"]
        actual = bytearray.fromhex(commands)
        expected = bytes.fromhex(case["native_commands"])
        assert len(actual) == len(expected)
        token_offset = 20 + 8
        portable_token = struct.unpack_from("<I", actual, token_offset)[0]
        native_token = struct.unpack_from("<I", expected, token_offset)[0]
        assert (portable_token - portable_key) & 0xFFFFFFFF == native_token - fixture["bitmap_key"]
        struct.pack_into("<I", actual, token_offset, native_token)
        assert all(actual[index] == expected[index] for index in case["command_offsets"])
    print(f"{len(fixture['cases'])} portable replays matched native state, geometry and bitmap writes; independent owned and external-state lists exercised")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["compile", "symbols", "native", "replay"])
    parser.add_argument("--fixture", type=Path, default=FIXTURE)
    parser.add_argument("--provider-dir", type=Path,
                        default=Path("temp/core-upstream/root-integration-01/upstream-core/sdk/lib"))
    parser.add_argument("--exe", type=Path, default=EXECUTABLE)
    parser.add_argument("--object", type=Path, default=PRODUCTION)
    parser.add_argument("--driver-object", type=Path, default=DRIVER)
    args = parser.parse_args()
    if args.mode == "compile":
        compile_replay(args.provider_dir)
        return
    fixture = json.loads(args.fixture.read_text())
    if args.mode == "symbols":
        check_symbols(fixture, args.object, args.driver_object)
    elif args.mode == "native":
        check_native(fixture)
    else:
        check_replay(fixture, args.exe)


if __name__ == "__main__":
    main()
