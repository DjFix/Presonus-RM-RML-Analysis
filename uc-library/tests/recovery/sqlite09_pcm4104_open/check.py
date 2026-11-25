"""Build and replay each PCM4104 lifecycle/regulator entry offline."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

SOURCE = "uc-library/src/Presonus/PCM4104/Pcm4104Spi.cpp"
HEADER = "uc-library/include/presonus/pcm4104/Pcm4104Spi.hpp"
BASE = Path("uc-library/tests/recovery/sqlite09_pcm4104_open")
PRIOR = Path("uc-library/tests/recovery/sqlite_pcm4104_read_register")
REPLAY = BASE / "Replay.cpp"
SCRATCH = Path("temp/recovery-work/sqlite-pcm4104-followup09")
FORMATTER = "uc-library/.venv/bin/clang-format"
BOUNDARIES = ("open", "close", "ioctl", "__errno_location", "_ZN4Core11DebugPrintfEPKcz")
WRAPPERS = [f"-Wl,--wrap={name}" for name in BOUNDARIES]
COMPILER = ["c++", "-std=c++17", "-O3", "-DNDEBUG", "-Ulinux", "-Wall",
            "-Wextra", "-Wpedantic", "-Werror", "-Iuc-library/include", "-pthread"]


def capture(argv, **kwargs):
    print("+", " ".join(map(str, argv)), file=sys.stderr)
    return subprocess.check_output(argv, text=True, **kwargs)


def build_flags(sdk):
    return [*COMPILER, "-DCORE_USE_OPENSSL=1", "-DPRESONUS_HAS_UPSTREAM_CORE=1",
            "-isystem", sdk / "include/presonus-core-5"]


def compile_replay(object_path, binary, sdk):
    object_path.parent.mkdir(parents=True, exist_ok=True)
    flags = build_flags(sdk)
    capture([*flags, "-c", SOURCE, "-o", object_path])
    capture([*flags, REPLAY, object_path, *WRAPPERS, sdk / "lib/libcorelib.a", "-o", binary])


def symbols(fixture, object_path, binary):
    names = capture(["nm", "--defined-only", object_path])
    undefined = capture(["nm", "--undefined-only", object_path])
    relocations = capture(["readelf", "--relocs", "--wide", object_path])
    linked = capture(["nm", "--defined-only", binary])
    emitted = {line.split()[-1]: line.split()[0] for line in names.splitlines()}
    mangled = fixture["original"]["mangled"]
    assert mangled in emitted
    for boundary in BOUNDARIES:
        assert any(line.split() == ["U", boundary] for line in undefined.splitlines())
        assert any(boundary in line.split() for line in relocations.splitlines())
    for boundary in (*BOUNDARIES[:-1], "log10f"):
        assert any(boundary in line.split() for line in relocations.splitlines())
    assert any(line.split()[-1] == BOUNDARIES[-1] for line in linked.splitlines())
    variants = {name: address for name, address in emitted.items()
                if name.endswith(("SpiC1EPKc", "SpiC2EPKc", "SpiD1Ev", "SpiD2Ev"))}
    print(mangled, "production symbol; portable variant addresses:", variants)


def replay(fixture, binary):
    cases = fixture["cases"]
    assert cases
    arguments = "".join(" ".join(map(str, case["args"])) + "\n" for case in cases)
    lines = iter(capture([binary, fixture["mode"]], input=arguments).splitlines())
    for i, case in enumerate(cases):
        observed = [next(lines, None) for _ in case["observed"]]
        if observed != case["observed"]:
            raise ValueError(f"case {i} with {case['args']}: {observed} != {case['observed']}")
    assert next(lines, None) is None
    capture([binary, "borrowed"])
    print(len(cases), fixture["mode"],
          "ARM/native cases matched; independent borrowed teardown verified")


def predecessor_replay(object_path, sdk):
    flags = build_flags(sdk)
    mode = "-DPCM4104_PREDECESSOR_REPLAY"
    binary = object_path.parent / "predecessor-register-replay"
    capture([*flags, mode, REPLAY, PRIOR / "Replay.cpp", object_path, *WRAPPERS,
             sdk / "lib/libcorelib.a", "-o", binary])
    for operation in ("read", "write"):
        fixture = PRIOR.with_name(f"sqlite_pcm4104_{operation}_register") / "fixtures.json"
        print(capture([sys.executable, PRIOR / "check.py", "replay", fixture,
                       "--binary", binary]), end="")
    lookup_test = "uc-library/tests/graph_trial03_pcm_tests.cpp"
    lookup_fixture = "uc-library/candidates/graph-live-trial-03-pcm/fixtures.txt"
    lookup = object_path.parent / "lookup-replay"
    capture([*flags, mode, REPLAY, lookup_test, object_path, *WRAPPERS[:2],
             sdk / "lib/libcorelib.a", "-o", lookup])
    print(capture([lookup, lookup_fixture]), end="")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("format", "compile", "symbols", "replay",
                                         "native", "predecessors"))
    parser.add_argument("fixture", type=Path)
    parser.add_argument("--binary", type=Path)
    parser.add_argument("--context", type=Path)
    parser.add_argument("--sdk", type=Path)
    parser.add_argument("--firmware-libm", type=Path)
    args = parser.parse_args()
    fixture = json.loads(args.fixture.read_text())
    build = SCRATCH / fixture["mode"]
    object_path = build / "Pcm4104Spi.o"
    binary = build / "pcm4104-followup-replay"
    if args.phase == "format":
        capture([FORMATTER, "--style=file", "--fallback-style=LLVM", "--dry-run",
                 "--Werror", SOURCE, HEADER, REPLAY])
    elif args.phase == "compile":
        compile_replay(object_path, binary, args.sdk)
    elif args.phase == "symbols":
        symbols(fixture, object_path, binary)
    elif args.phase == "replay":
        replay(fixture, args.binary or binary)
    elif args.phase == "predecessors":
        predecessor_replay(object_path, args.sdk)
    else:
        command = [sys.executable, BASE / "native.py", args.context]
        if fixture["mode"] == "attenuate_channel":
            command = [sys.executable, args.fixture.with_name("native.py"), args.context,
                       args.firmware_libm]
        original = capture(command)
        assert json.loads(original) == fixture
        print(len(fixture["cases"]), fixture["mode"], "independent ARM cases regenerated")


if __name__ == "__main__":
    main()
