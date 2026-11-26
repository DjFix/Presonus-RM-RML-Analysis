"""Compile and compare the owned Linux implementation with the ARM fixture."""

import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
APP = ROOT / "uc-library"
WORK = ROOT / "temp/recovery-work" / (HERE.name + "-check")
ELF_FIXTURE = HERE / "fixtures.json"
SOURCE = APP / "src/Presonus/Surface/PageHeaderComponent.cpp"
TABLE_SOURCE = APP / "src/Presonus/AssignmentHandlerTable.cpp"
BASE_SOURCE = APP / "src/Presonus/MappablePageComponent.cpp"
OBJECT = WORK / "PageHeaderComponent.o"
EXE = WORK / "replay"


def run(argv):
    argv = list(map(str, argv))
    print(json.dumps(argv), flush=True)
    subprocess.run(argv, cwd=ROOT, check=True)


def compile_replay():
    relative_sdk = Path("temp/core-upstream/root-integration-01/upstream-core/sdk")
    sdk = next(parent / relative_sdk for parent in (ROOT, *ROOT.parents)
               if (parent / relative_sdk).is_dir())
    common = [
        "/usr/bin/c++", "-std=gnu++20", "-O2", "-DNDEBUG=1",
        "-DPRESONUS_HAS_UPSTREAM_CORE=1", "-DCORE_USE_OPENSSL=1", "-pthread",
        "-Ulinux", "-ffunction-sections", "-fdata-sections",
        "-I", APP / "include", "-isystem", ROOT / "third_party/ccl-framework",
    ]
    link = [
        "-Wl,--gc-sections,--start-group", sdk / "lib/libcorelib.a",
        sdk / "lib/libpresonus_core_allocator.a", "-Wl,--end-group", "-ldl", "-lm",
    ]
    mixer = APP / "src/Presonus/Surface/SLMixerEncoder.cpp"
    WORK.mkdir(parents=True, exist_ok=True)
    run([*common, "-c", SOURCE, "-o", OBJECT])
    run([*common, HERE / "Replay.cpp", OBJECT, TABLE_SOURCE, BASE_SOURCE, mixer,
         *link, "-o", EXE])

def symbols():
    expected = json.loads(ELF_FIXTURE.read_text())["original"]["mangled"]
    output = subprocess.check_output(["nm", "--defined-only", OBJECT], text=True)
    match = [line for line in output.splitlines() if line.split()[-1] == expected]
    assert len(match) == 1 and match[0].split()[1] == "T", output
    print(match[0])


def replay(executable, fixture):
    cases = json.loads(fixture.read_text())["cases"]
    for case in cases:
        inputs = case["inputs"]
        original, label = inputs[1], inputs[6]
        expected = []
        for operation, *args in case["trace"]:
            if operation in ("cast", "focus"):
                expected.append(" ".join(map(str, (operation, *args))))
            elif operation == "bind" and original != args[0]:
                original = args[0]
                expected.append("changed focus")
            elif operation == "label" and label != args[0]:
                label = args[0]
                expected.append("changed label")
        expected.append(f'result {case["original_after"]} {case["label_after"]}')
        actual = subprocess.check_output([executable, *map(str, inputs)], text=True)
        assert actual.splitlines() == expected, (case, expected, actual)
    print(f"Portable PageHeader focus: {len(cases)} comparisons with ARM cases")


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "compile":
        compile_replay()
    elif mode == "symbols":
        symbols()
    elif mode == "replay":
        paths = tuple(Path(path).resolve() for path in sys.argv[2:])
        replay(*(paths or (EXE, ELF_FIXTURE)))
    else:
        raise SystemExit("expected compile, symbols or replay")
