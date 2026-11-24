"""Build the local owner, check mangling, and compare bounded observations."""
import argparse
import json
from pathlib import Path
import subprocess


WORK = Path("temp/recovery-work/sqlite01_slreverb_param_count")
TEST = Path(__file__).parent
PROVIDERS = Path("temp/provider-baseline08")
SOURCE = Path("uc-library/src/Presonus/Dsp")


def run(argv, **kwargs):
    print(" ".join(map(str, argv)), flush=True)
    return subprocess.run(argv, check=True, text=True, **kwargs)


def compile_replay():
    WORK.mkdir(exist_ok=True, parents=True)
    flags = ["c++", "-std=c++20", "-O2", "-Iuc-library/include",
             "-Ithird_party/ccl-framework"]
    owner = WORK / "SLReverbController.o"
    run([*flags, "-c", SOURCE / "SLReverbController.cpp", "-o", owner])
    libs = [
        PROVIDERS / "libpresonus_rm_components.a",
        PROVIDERS / "libcorelib.a",
        PROVIDERS / "libpresonus_core_allocator.a",
        WORK / "libpresonus_zlib.a",
        WORK / "libpresonus_private_glibc29.a",
    ]
    for driver, name in [(TEST / "Replay.cpp", "Replay"),
                         (TEST.parent / "frontier-scale02/frontier02_w03/driver.cpp",
                          "ConstructorReplay")]:
        run([*flags, driver, SOURCE / "ControllerInterface.cpp", owner, *libs,
             "-pthread", "-ldl", "-o", WORK / name])


def symbols():
    expected = "_ZNK8Presonus3Dsp18SLReverbController16getNumParametersEv"
    lines = run(["nm", "--defined-only", WORK / "SLReverbController.o"],
                capture_output=True).stdout.splitlines()
    matches = [line for line in lines if line.split()[-1] == expected]
    assert len(matches) == 1 and matches[0].split()[-2] == "T"
    print(matches[0])


def replay(executable, fixture):
    cases = json.loads(fixture.read_text())["cases"]
    for case in cases:
        values = run([executable, str(case["id"])], capture_output=True).stdout.split()
        observed = list(map(int, values))
        assert observed == [case["r0"], case["r0"]], (case["id"], observed)
    print(f"PASS {len(cases)} cases, {2 * len(cases)} C++ virtual calls; constructor storage and getter boundaries")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["compile", "symbols", "replay"])
    parser.add_argument("--executable", type=Path, default=WORK / "Replay")
    parser.add_argument("--fixture", type=Path, default=TEST / "fixtures.json")
    args = parser.parse_args()
    if args.action == "compile":
        compile_replay()
    elif args.action == "symbols":
        symbols()
    else:
        replay(args.executable, args.fixture)


if __name__ == "__main__":
    main()
