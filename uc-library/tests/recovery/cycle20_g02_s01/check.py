"""Build or replay the bounded local reconstruction in its assigned checkout."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import struct
import time

TASK = "cycle20_g02_s01"
DOMAIN = "CS18 startup meter factory: all 13 original finite dB inputs and binary32 knots, ARM powf and Linux libm rounding, named pinned CCL creator, bidirectional knot lookup, and standalone inherited constructor."
TARGET = "_Z18__initMeterControlv"
ROOT = Path(__file__).resolve().parents[4]
BASE = Path("uc-library/tests/recovery") / TASK
SCRATCH = Path("temp/recovery-work/cycle20_g02/s01")
SOURCE = Path("uc-library/src/DefaultMeterInterpolator.cpp")
HEADER = Path("uc-library/include/presonus/DefaultMeterInterpolator.hpp")
SDK = Path("temp/core-upstream/root-integration-01/upstream-core/sdk")
CPP = ["g++", "-std=c++20", "-O2", "-fno-rtti", "-fno-lto", "-Iuc-library/include",
       "-I" + str(SDK / "include/presonus-core-5")]
FORMATTER = "uc-library/.venv/bin/clang-format"
FIXTURES = BASE / "fixtures.json"
OBJECT = SCRATCH / "production.o"
EXE = SCRATCH / "replay"
PINNED = ['third_party/ccl-framework/core/public/coreinterpolator.h', 'third_party/ccl-framework/core/public/coreinterpolator.cpp', 'third_party/ccl-framework/core/public/corevector.h']


def run(argv, **opts):
    return subprocess.run([str(arg) for arg in argv], cwd=ROOT, text=True,
                          check=True, **opts)


def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def format_sources():
    run([FORMATTER, "--style=file", "--fallback-style=LLVM", "--dry-run", "--Werror",
         SOURCE, HEADER, BASE / "Replay.cpp"])


def compile_replay():
    (ROOT / SCRATCH).mkdir(parents=True, exist_ok=True)
    run([*CPP, "-c", SOURCE, "-o", OBJECT])
    run([*CPP, BASE / "Replay.cpp", OBJECT, SDK / "lib/libcorelib.a",
         SDK / "lib/libpresonus_core_allocator.a", *[], "-o", EXE])


def verify_symbols(obj):
    symbols = {}
    for line in run(["nm", "-P", obj], capture_output=True).stdout.splitlines():
        name, kind, *_ = line.split()
        symbols[name] = kind
    creator = "_ZN4Core19InterpolatorFactory18createInterpolatorI24DefaultMeterInterpolatorEEPNS_12InterpolatorEv"
    provider = "_ZN4Core19InterpolatorFactory3addEPKcPFPNS_12InterpolatorEvE"
    assert symbols[TARGET] == "T" and symbols[creator] in ("T", "W") and symbols[provider] == "U"
    return symbols


def observe_cpp(exe, fixture):
    assert fixture["mangled"] == TARGET
    output = run([ROOT / exe], capture_output=True,
                 input=" ".join(map(str, fixture["inputs"]))).stdout
    rows = [list(map(int, line.split())) for line in output.splitlines()]
    assert len(rows) == len(fixture["points"]) == len(fixture["inputs"]) == 13
    _, _, step, cutoff, _, multiplier, base, _, _ = fixture["literals"]
    expected_calls = fixture["calls"]
    report = []
    for index, (decibels, point, row) in enumerate(zip(fixture["inputs"], fixture["points"], rows)):
        exponent, host_power, amplitude, level, forward, reverse = row
        assert expected_calls[5*index:5*index+5] == [
            ["fcmplt", decibels, cutoff], ["fmul", decibels, multiplier],
            ["powf", base, exponent], ["i2f", index],
            ["fmul", struct.unpack("<I", struct.pack("<f", index))[0], step],
        ]
        assert [amplitude, level] == point
        assert [reverse, forward] == point
        assert abs(host_power - amplitude) <= 1
        report.append(dict(index=index, db_bits=decibels, exponent_bits=exponent,
                           host_powf_bits=host_power, arm_powf_bits=amplitude,
                           host_minus_arm_ulp=host_power-amplitude, level_bits=level))
    return report


def replay(exe, obj, fixtures, integration, out):
    start = time.monotonic()
    verify_symbols(obj)
    observed = observe_cpp(exe, json.loads((ROOT / fixtures).read_text()))
    proof = {
        "task_id": TASK, "passed": True, "cpp_differential_passed": True,
        "compiled_mangled_names_matched": True, "portable_ready": False,
        "mangled_names": [TARGET], "domain": DOMAIN, "cases": observed,
        "formatter_version": run([FORMATTER, "--version"], capture_output=True).stdout.strip(),
        "sources": {str(path.relative_to("uc-library")): sha(path) for path in (SOURCE, HEADER)},
        "repository_sources": {path: sha(path) for path in PINNED},
        "fixture_sha256": sha(fixtures), "replay_executable_sha256": sha(exe),
        "compiled_object_sha256": sha(obj), "replay_producer_sha256": sha(BASE / "check.py"),
        "elapsed_seconds": time.monotonic() - start,
    }
    if integration and (ROOT / integration).is_file():
        proof["integration"] = str(integration)
        proof["integration_sha256"] = sha(integration)
    output = ROOT / out
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(proof, indent=2) + "\n")
    print(f"{TASK}: {len(observed)} bounded comparisons passed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("format", "compile", "symbols", "replay"))
    parser.add_argument("--exe", type=Path, default=EXE)
    parser.add_argument("--object", type=Path, default=OBJECT)
    parser.add_argument("--fixtures", type=Path, default=FIXTURES)
    parser.add_argument("--integration", type=Path)
    parser.add_argument("--out", type=Path, default=SCRATCH / "fresh-proof.json")
    options = parser.parse_args()
    if options.operation == "format":
        format_sources()
    elif options.operation == "compile":
        compile_replay()
    elif options.operation == "symbols":
        verify_symbols(options.object)
        print(f"{TASK}: exact compiled symbol matched")
    else:
        replay(options.exe, options.object, options.fixtures, options.integration, options.out)
