"""Compile and compare the shared EQ5 lifecycle driver with native fixtures."""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
SOURCE = Path("uc-library/src/Presonus/Dsp/EQ5Controller.cpp")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command, **kwargs):
    return subprocess.run([str(piece) for piece in command], check=True, text=True, **kwargs)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("check", choices=("compile", "symbols", "replay"))
    parser.add_argument("--fixture", type=Path)
    parser.add_argument("--fixture-sha256")
    parser.add_argument("--exe", type=Path)
    parser.add_argument("--object", type=Path)
    parser.add_argument("--packet", type=Path)
    parser.add_argument("--scratch", type=Path)
    parser.add_argument("--providers", type=Path)
    args = parser.parse_args()

    if args.check == "compile":
        args.scratch.mkdir(parents=True, exist_ok=True)
        objects = []
        dsp = SOURCE.parent
        sources = [SOURCE, HERE / "Replay.cpp", *(dsp / (name + ".cpp") for name in (
            "EQController", "EQControllerProcess", "Controller", "ControllerInterface",
            "ControllerSetupProcess", "ControllerInfo", "ParamDescriptorList",
            "Eq8LimiterParameterLists",
        )), Path("uc-library/src/mixer_dsp/EQTypeConversions.cpp"),
            *(Path("uc-library/src/DSP") / name for name in (
                "BiquadCalcConstructor.cpp", "BiquadMethods.cpp", "BiquadIncremental.cpp", "BiquadSine.cpp",
            ))]
        for source in sources:
            obj = args.scratch / (source.stem + ".o")
            run(["g++", "-std=c++20", "-O2", "-fno-rtti", "-ffp-contract=off",
                 "-fno-sized-deallocation", "-fno-devirtualize", "-fno-devirtualize-speculatively", "-Wno-multichar", "-Iuc-library/include",
                 "-Ithird_party/ccl-framework", "-c", source, "-o", obj])
            objects.append(obj)
        libraries = [args.providers / name for name in ("libcorelib.a", "libpresonus_core_allocator.a")]
        expected = ("5a2c8bbb20d8d194ff4f5047118696afa918a046b01739c4257416044e83f5f3",
                    "69892fbcec9a50a140462982073c686a67ca4763dfb5dfa190534d022b78a40d")
        assert tuple(digest(path) for path in libraries) == expected
        print(json.dumps(dict(zip(map(str, libraries), expected))))
        run(["g++", *objects, "-Wl,--start-group", *libraries, "-Wl,--end-group",
             "-pthread", "-ldl", "-Wl,--wrap=_ZdlPv", "-Wl,--wrap=_ZdlPvm",
             "-o", args.scratch / "replay"])
        return

    assert digest(args.fixture) == args.fixture_sha256
    fixture = json.loads(args.fixture.read_text())
    symbol = fixture["original"]["mangled"]
    mode = symbol.split("Controller")[-1][:2].lower()
    if args.check == "symbols":
        lines = run(["nm", "--defined-only", args.object], capture_output=True).stdout.splitlines()
        row, = (line for line in lines if line.split()[-1] == symbol)
        assert row.split()[1] in ("T", "W")
        print(row)
        return

    if args.packet:
        output = args.scratch / (args.fixture.parent.name + ".native.json")
        run([sys.executable, HERE / "native.py", args.packet, output])
        assert args.fixture.read_bytes() == output.read_bytes()

    cases = fixture["cases"]
    result = run([args.exe, mode], input="".join(f"{case['identifier']}\n" for case in cases),
                 capture_output=True).stdout.splitlines()
    assert len(result) == len(cases)
    for case, line in zip(cases, result):
        if mode in ("c1", "c2"):
            expected = [case[key] for key in ("identifier", "bands", "descriptor_count", "enabled", "dirty")]
            expected += [value for band in case["band_words"] for value in band]
            expected += [value for descriptor in case["descriptors"] for value in descriptor]
        else:
            trace = case["native_calls"]
            assert trace[0] == ["ControllerD2"]
            released = int(["release"] in trace)
            deleted = int(case["receiver_deallocated"])
            assert trace == [["ControllerD2"]] + ([["release"]] if released else []) + (
                [["receiver_deallocated"]] if deleted else [])
            expected = [released, 1, deleted, released, released + 1 if deleted else 0]
        actual = list(map(int, line.split()))
        assert actual == expected, (mode, case["identifier"], [
            (i, got, want) for i, (got, want) in enumerate(zip(actual, expected)) if got != want
        ], len(actual), len(expected))
    print(f"{symbol}: {len(cases)} independent native/portable cases")


if __name__ == "__main__":
    main()
