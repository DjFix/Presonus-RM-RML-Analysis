"""Compare PCM4104 transport and failure diagnostics offline."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

SOURCE = "uc-library/src/Presonus/PCM4104/Pcm4104Spi.cpp"
HEADER = "uc-library/include/presonus/pcm4104/Pcm4104Spi.hpp"
REPLAY = str(Path(__file__).parent / "Replay.cpp")
CORE_DEBUG = "third_party/ccl-framework/core/system/coredebug.cpp"
SCRATCH = Path("temp/recovery-work/sqlite-pcm4104-register-io")
FORMATTER = "uc-library/.venv/bin/clang-format"
LOOKUP_SYMBOL = "_ZN8Presonus7PCM410410Pcm4104Spi32lookupChannelAttenuationRegisterEi"
LOOKUP_TEST = "uc-library/tests/graph_trial03_pcm_tests.cpp"
LOOKUP_FIXTURE = "uc-library/candidates/graph-live-trial-03-pcm/fixtures.txt"
DIAGNOSTIC = "_ZN4Core11DebugPrintfEPKcz"
BOUNDARIES = ("ioctl", "__errno_location", DIAGNOSTIC)
WRAPPERS = [f"-Wl,--wrap={name}" for name in BOUNDARIES]
COMPILER = ["c++", "-std=c++17", "-Wall", "-Wextra", "-Wpedantic", "-Werror",
            "-Iuc-library/include", "-pthread", "-Ulinux"]


def capture(argv, **kwargs):
    print("+", " ".join(map(str, argv)), file=sys.stderr)
    return subprocess.check_output(argv, text=True, **kwargs)


def build_flags(sdk, variant):
    flags = (["-O3", "-DNDEBUG", "-DNDEBUG=1"] if variant == "release"
             else ["-O0", "-g", "-DDEBUG", "-DDEBUG_LOG=1"])
    return [*COMPILER, *flags, "-DCORE_USE_OPENSSL=1", "-DPRESONUS_HAS_UPSTREAM_CORE=1",
            "-isystem", sdk / "include/presonus-core-5"]


def compile_replay(object_path, binary, sdk, variant):
    object_path.parent.mkdir(parents=True, exist_ok=True)
    compiler = build_flags(sdk, variant)
    macros = capture([*compiler, "-dM", "-E", "-x", "c++", "-include",
                      "core/system/coredebug.h", "/dev/null"])
    expected_debug = int(variant == "debug")
    assert f"#define DEBUG {expected_debug}" in macros.splitlines()
    assert f"#define DEBUG_LOG {expected_debug}" in macros.splitlines()
    print(f"Core DEBUG={expected_debug} DEBUG_LOG={expected_debug}")
    capture([*compiler, "-c", SOURCE, "-o", object_path])
    provider = [sdk / "lib/libcorelib.a", sdk / "lib/libpresonus_core_allocator.a"]
    if variant == "debug":
        debug_object = object_path.parent / "coredebug.o"
        capture([*compiler, "-c", CORE_DEBUG, "-o", debug_object])
        provider.insert(0, debug_object)
    capture([*compiler, REPLAY, object_path, *WRAPPERS, *provider, "-o", binary])


def symbols(fixture, object_path, binary):
    names = capture(["nm", "--defined-only", object_path])
    undefined = capture(["nm", "--undefined-only", object_path])
    relocations = capture(["readelf", "--relocs", "--wide", object_path])
    linked = capture(["nm", "--defined-only", binary])
    emitted = {line.split()[-1] for line in names.splitlines()}
    assert {LOOKUP_SYMBOL, fixture["original"]["mangled"]} <= emitted
    for boundary in BOUNDARIES:
        assert any(line.split() == ["U", boundary] for line in undefined.splitlines())
        assert any(boundary in line.split() for line in relocations.splitlines())
    assert any(line.split()[-2:] in (["T", DIAGNOSTIC], ["t", DIAGNOSTIC]) for line in linked.splitlines())
    print(fixture["original"]["mangled"], LOOKUP_SYMBOL,
          "relocations for libc ioctl, libc errno and direct Core DebugPrintf")


def replay(fixture, binary):
    cases = fixture["cases"]
    assert cases
    arguments = "".join(" ".join(map(str, case["args"])) + "\n" for case in cases)
    lines = iter(capture([binary, fixture["mode"]], input=arguments).splitlines())
    diagnostics = 0
    for i, case in enumerate(cases):
        for message, errno in case["original_diagnostics"]:
            assert next(lines) == (message % errno).rstrip("\n"), case
            diagnostics += 1
        actual = list(map(int, next(lines).split()))
        original_calls = case["original_calls"]
        assert actual[3:5] == [original_calls.count("errno"),
                               original_calls.count("diagnostic")], case
        actual = [*actual[:3], [actual[5:]] if len(actual) > 5 else []]
        if actual != case["observed"]:
            raise ValueError(f"case {i} with {case['args']}: {actual} != {case['observed']}")
    assert next(lines, None) is None
    print(len(cases), fixture["mode"], "cases matched ARM transport and state observations;",
          diagnostics, "actual Core diagnostic lines matched in order")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("format", "compile", "symbols", "replay", "native", "lookup"))
    parser.add_argument("fixture", type=Path)
    parser.add_argument("--binary", type=Path)
    parser.add_argument("--context", type=Path)
    parser.add_argument("--sdk", type=Path)
    parser.add_argument("--variant", choices=("release", "debug"), default="release")
    args = parser.parse_args()
    fixture = json.loads(args.fixture.read_text())
    build = SCRATCH / fixture["mode"] / args.variant
    object_path = build / "Pcm4104Spi.o"
    binary = build / "pcm4104-register-replay"
    if args.phase == "format":
        capture([FORMATTER, "--style=file", "--fallback-style=LLVM", "--dry-run",
                 "--Werror", SOURCE, HEADER, REPLAY])
    elif args.phase == "compile":
        compile_replay(object_path, binary, args.sdk, args.variant)
    elif args.phase == "symbols":
        symbols(fixture, object_path, binary)
    elif args.phase == "replay":
        replay(fixture, args.binary or binary)
    elif args.phase == "lookup":
        lookup = build / "lookup-replay"
        capture([*build_flags(args.sdk, args.variant), LOOKUP_TEST, object_path,
                 args.sdk / "lib/libcorelib.a", "-o", lookup])
        print(capture([lookup, LOOKUP_FIXTURE]), end="")
    else:
        original = capture([sys.executable, str(Path(__file__).with_name("native.py")),
                            args.context])
        assert json.loads(original) == fixture
        print(len(fixture["cases"]), fixture["mode"], "independent ARM cases regenerated")


if __name__ == "__main__":
    main()
