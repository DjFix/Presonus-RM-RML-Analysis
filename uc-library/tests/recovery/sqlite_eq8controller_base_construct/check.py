"""Build the EQ8 lifecycle replay and compare it against native ARM observations."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).parent
DSP = Path("uc-library/src/Presonus/Dsp")
SOURCE = DSP / "EQ8Controller.cpp"
PROVIDER_HASHES = {
    "libcorelib.a": "5a2c8bbb20d8d194ff4f5047118696afa918a046b01739c4257416044e83f5f3",
    "libpresonus_core_allocator.a": "69892fbcec9a50a140462982073c686a67ca4763dfb5dfa190534d022b78a40d",
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(argv, **kwargs):
    return subprocess.run([str(arg) for arg in argv], check=True, text=True, **kwargs)


def compile_replay(scratch, providers):
    scratch.mkdir(parents=True, exist_ok=True)
    sources = [
        SOURCE, HERE / "Replay.cpp",
        *(DSP / f"{name}.cpp" for name in (
            "EQController", "EQControllerProcess", "Controller", "ControllerInterface",
            "ControllerSetupProcess", "ControllerInfo", "ParamDescriptorList",
            "EqParameterLists",
        )),
        Path("uc-library/src/mixer_dsp/EQTypeConversions.cpp"),
        *(Path("uc-library/src/DSP") / f"{name}.cpp" for name in (
            "BiquadCalcConstructor", "BiquadMethods", "BiquadIncremental", "BiquadSine",
        )),
    ]
    objects = []
    for source in sources:
        obj = scratch / (source.stem + ".o")
        argv = [
            "g++", "-std=c++20", "-O2", "-Ulinux", "-fno-lto", "-ffp-contract=off",
            "-fno-devirtualize", "-fno-devirtualize-speculatively", "-Wno-multichar",
            "-Iuc-library/include", "-Ithird_party/ccl-framework", "-c", source, "-o", obj,
        ]
        print(json.dumps(list(map(str, argv))), flush=True)
        run(argv)
        objects.append(obj)
    libraries = [providers / name for name in PROVIDER_HASHES]
    for library in libraries:
        assert sha(library) == PROVIDER_HASHES[library.name], library
    argv = [
        "g++", *objects, "-Wl,--start-group", *libraries, "-Wl,--end-group", "-pthread",
        "-ldl", "-Wl,--wrap=_ZdlPv", "-Wl,--wrap=_ZdlPvm", "-o", scratch / "Replay",
    ]
    print(json.dumps(list(map(str, argv))), flush=True)
    run(argv)


def expected(case, variant):
    identifier = case["identifier"]
    if identifier & (1 << 31):
        identifier -= 1 << 32
    if variant in ("C1", "C2"):
        return [
            identifier, case["bands"], case["descriptor_count"], case["enabled"],
            case["dirty"], *(word for band in case["band_words"] for word in band),
            *(word for descriptor in case["descriptors"] for word in descriptor),
            *(result for mapping in case["conversions"] for _, result in mapping),
        ]
    trace = [["ControllerD2"]]
    if identifier == -1:
        trace.append(["release"])
    deleted = case["receiver_deallocated"]
    assert deleted == (variant == "D0")
    if deleted:
        trace.append(["receiver_deallocated"])
    assert case["native_calls"] == trace
    return [int(deleted), *({"release": 1, "receiver_deallocated": 2}[event[0]]
                            for event in trace[1:])]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("compile", "symbols", "replay"))
    parser.add_argument("--fixture", type=Path)
    parser.add_argument("--fixture-sha256")
    parser.add_argument("--exe", type=Path)
    parser.add_argument("--scratch", type=Path)
    parser.add_argument("--providers", type=Path)
    parser.add_argument("--packet", type=Path)
    parser.add_argument("--baseline-root", type=Path)
    args = parser.parse_args()
    if args.mode == "compile":
        compile_replay(args.scratch, args.providers)
        return

    assert sha(args.fixture) == args.fixture_sha256
    fixture = json.loads(args.fixture.read_text())
    symbol = fixture["original"]["mangled"]
    variant = symbol.split("EQ8Controller")[1][:2]
    if args.mode == "symbols":
        defined = run(["nm", "--defined-only", args.scratch / "EQ8Controller.o"],
                      capture_output=True).stdout
        row, = [line for line in defined.splitlines() if line.split()[-1] == symbol]
        assert row.split()[1] == "T", row
        print(row)
        caller = "EQTypeConversions.o" if variant == "D0" else "Replay.o"
        relocs = run(["readelf", "--wide", "--relocs", args.scratch / caller],
                     capture_output=True).stdout
        if variant == "D0":
            vtable = ".rela.data.rel.ro._ZTVN8Presonus3Dsp13EQ8ControllerE"
            sections = relocs.split("Relocation section ")
            relocs, = [section for section in sections if section.startswith(f"'{vtable}'")]
        hits = [line.strip() for line in relocs.splitlines() if symbol in line.split()]
        assert hits, symbol
        print(*hits, sep="\n")
        return

    if args.packet:
        output = args.scratch / (args.fixture.parent.name + ".native.json")
        run([sys.executable, HERE / "native.py", args.packet, output,
             "--baseline-root", args.baseline_root])
        assert output.read_bytes() == args.fixture.read_bytes()
    for case in fixture["cases"]:
        identifier = case["identifier"]
        signed_id = identifier if identifier < (1 << 31) else identifier - (1 << 32)
        actual = list(map(int, run([args.exe, variant, signed_id],
                                   capture_output=True).stdout.split()))
        want = expected(case, variant)
        assert actual == want, (symbol, signed_id, actual, want)
    print(f"{symbol}: {len(fixture['cases'])} native/portable cases")


if __name__ == "__main__":
    main()
