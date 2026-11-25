"""Compile this local reconstruction and compare its portable replay."""
import argparse
import json
import hashlib
from pathlib import Path
import subprocess

HERE = Path(__file__).parent
TASK = HERE.name
WORK = Path("temp/recovery-work/sqlite-local-check") / TASK
SOURCE = Path("uc-library/src/Presonus/Dsp")
LINK_INPUTS = Path("temp/recovery-work/sqlite-local-check/archives/MANIFEST.json")
IS_SETTER = TASK.endswith("_set_value")


def run(arguments, **kwargs):
    return subprocess.run(arguments, check=True, text=True, **kwargs)


def compile_replay():
    WORK.mkdir(parents=True, exist_ok=True)
    records = json.loads(LINK_INPUTS.read_text())
    archives = [Path(record["snapshot"]) for record in records]
    for path, record in zip(archives, records):
        assert hashlib.sha256(path.read_bytes()).hexdigest() == record["sha256"]
    flags = ["c++", "-std=c++20", "-O2", "-Iuc-library/include", "-Ithird_party/ccl-framework"]
    owner = WORK / "SLReverbController.o"
    commands = [
        [*flags, "-MMD", "-MF", WORK / "SLReverbController.d",
         "-c", SOURCE / "SLReverbController.cpp", "-o", owner],
        [*flags, HERE / "Replay.cpp", owner, *archives, "-pthread", "-ldl", "-o", WORK / "Replay"],
    ]
    for argv in commands:
        print(json.dumps(list(map(str, argv))), flush=True)
        run(argv)
    for path, record in zip(archives, records):
        assert hashlib.sha256(path.read_bytes()).hexdigest() == record["sha256"]


def symbols(fixture, object_path):
    expected = json.loads(fixture.read_text())["original"]["mangled"]
    result = run(["nm", "--defined-only", object_path],
                 capture_output=True).stdout.splitlines()
    matched = [line for line in result if line.split()[-1] == expected]
    assert len(matched) == 1 and matched[0].split()[-2] == "T"
    print(matched[0])


def check_info(executable, cases):
    for case in cases:
        output = run([executable, str(case["index"]), str(case["byte_size"])],
                     capture_output=True).stdout.splitlines()
        assert output == list(map(str, case["output"])), (case, output)
    return len(cases)


def check_set(executable, cases):
    for case in cases:
        expected = bytearray.fromhex(case["input"])
        for offset, data in case["changes"]:
            expected[offset:offset + 4] = bytes.fromhex(data)
        for kind in ("owned", "borrowed"):
            output = run([executable, str(case["index"]), str(case["value_bits"]),
                          case["input"], kind], capture_output=True).stdout.splitlines()
            assert [list(map(int, line.split())) for line in output[:-2]] == case["calls"]
            assert int(output[-2]) == case["value_bits"]
            actual = bytes.fromhex(output[-1])
            assert actual == expected, (kind, case["mode"], case["index"],
                                        [(hex(i), a, b) for i, (a, b) in
                                         enumerate(zip(actual, expected)) if a != b])
    return 2 * len(cases)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["compile", "symbols", "replay", "canonical"])
    parser.add_argument("--executable", "--exe", type=Path, default=WORK / "Replay")
    parser.add_argument("--fixture", type=Path, default=HERE / "fixtures.json")
    parser.add_argument("--object", type=Path, default=WORK / "SLReverbController.o")
    parser.add_argument("--integration", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.action == "compile":
        compile_replay()
    elif args.action == "symbols":
        symbols(args.fixture, args.object)
    else:
        cases = json.loads(args.fixture.read_text())["cases"]
        count = (check_set if IS_SETTER else check_info)(args.executable, cases)
        print(f"PASS {count} portable Controller virtual calls")
        if args.action == "canonical":
            symbols(args.fixture, args.object)
            local = Path(f"uc-library/candidates/{TASK}/worker-proof.json")
            proof = json.loads(local.read_text())
            for name, expected in proof["inputs"].items():
                # Immutable worker dispatch and selection inputs keep their original provenance.
                if name.startswith("temp/"):
                    continue
                assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == expected
            integration_bytes = args.integration.read_bytes()
            assert json.loads(integration_bytes)["platform"].lower().startswith("linux")
            proof["integration_sha256"] = hashlib.sha256(integration_bytes).hexdigest()
            proof["object_sha256"] = hashlib.sha256(args.object.read_bytes()).hexdigest()
            proof["executable_sha256"] = hashlib.sha256(args.executable.read_bytes()).hexdigest()
            proof["portable_executions"] = count
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps(proof, indent=2) + "\n")


if __name__ == "__main__":
    main()
