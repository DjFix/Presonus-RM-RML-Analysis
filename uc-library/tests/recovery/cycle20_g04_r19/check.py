"""Compare the compiled portable method with independently recorded ARM observations."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from native import SPECS, TASK

DOMAIN = 'Both exact offline firmware roles, ordered consumption of unique raw operator-new preset allocations and null slots followed by backing storage release. Compare six scenarios per role, including already empty, empty with capacity, one allocation, one null and mixed order. Portable observes real unsized deallocation, real pinned Core Vector reset, and idempotent second clear.'
LIMITS = ['The original return declaration and class/ARM ABI layout remain unresolved. Only unique raw operator-new records without destructor obligations and nulls are supported.', 'Native executes the authentic application routine. The exact role-specific unsized-delete and Core resize targets are observed as modeled allocation boundaries with actual unmapping and post-return inaccessible checks.', 'The portable comparison uses actual runtime delete calls and pinned CCL Vector. Borrowed preset rosters and complete native Preset objects are outside the domain.']
SOURCES = ['include/presonus/mixer_state/MixerState.hpp', 'src/Presonus/MixerClientPresetCleanup.cpp']
CORE = ['third_party/ccl-framework/core/public/corevector.h']


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def check_symbols(path, names):
    nm = subprocess.check_output(["nm", "--defined-only", path], text=True)
    rows = [line.split() for line in nm.splitlines()]
    result = {}
    for name in names:
        row, = [row for row in rows if len(row) == 3 and
                row[1] in {"T", "W", "t"} and row[2] == name]
        result[name] = row[0]
    undefined = set(line.split()[-1] for line in
                    subprocess.check_output(["nm", "-u", path], text=True).splitlines()
                    if line.strip())
    assert {"_ZdlPv", "_ZdaPv"} <= undefined
    assert not {"_ZdlPvm", "_ZdaPvm"} & undefined
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--object", type=Path, required=True)
    parser.add_argument("--exe", type=Path)
    parser.add_argument("--integration", default="-")
    parser.add_argument("--out", default="-")
    args = parser.parse_args()
    names = list(dict.fromkeys(spec[3] for spec in SPECS))
    emitted = check_symbols(args.object, names)
    if args.exe is None:
        print(json.dumps(emitted))
        return
    fixture = json.loads(args.fixture.read_text())
    assert fixture["task"] == TASK and len(fixture["originals"]) == len(SPECS)
    proof_rows, observations = [], []
    source_hashes = {path: digest(Path("uc-library") / path) for path in SOURCES}
    provider_hashes = {path: digest(path) for path in CORE}
    for original_cases, spec in zip(fixture["originals"], SPECS):
        original = original_cases["original"]
        fields = ("elf_sha256", "firmware", "role", "mangled", "address", "size", "range_sha256")
        assert tuple(original[key] for key in fields) == spec
        assert original["section"] == ".text" and original["kind"] == "STT_FUNC"
        cases = original_cases["cases"]
        assert cases and all(case["executed"] for case in cases)
        stdin = "".join(case["input"] + "\n" for case in cases)
        replay = subprocess.run([str(args.exe.resolve())], input=stdin,
                                text=True, capture_output=True, check=True)
        actual = replay.stdout.splitlines()
        assert actual == [case["output"] for case in cases], (original, actual)
        proof_rows.append(dict(
            original_elf_sha256=original["elf_sha256"], mangled=original["mangled"],
            cpp_compiled=True, mangling_namespace_checked=True,
            cpp_differential_passed=True, portable_ready=False,
            validation_domain=DOMAIN, declaration_uncertainties=[LIMITS[0]],
            sources=source_hashes, repository_sources=provider_hashes,
        ))
        observations.append(dict(original=original, native_completed_cases=len(cases),
                                 portable_cases=len(actual), portable_outputs=actual,
                                 native_dependencies=original_cases["dependencies"]))
    proof = dict(version=1, task_id=TASK, success=True, validation_domain=DOMAIN,
                 cpp_differential_passed=True, mangling_namespace_checked=True,
                 mangled_names=names, limitations=LIMITS, compiled_symbols=emitted,
                 original_replays=observations,
                 native_completed_cases=sum(row["native_completed_cases"] for row in observations),
                 portable_cases=sum(row["portable_cases"] for row in observations),
                 object_sha256=digest(args.object), executable_sha256=digest(args.exe),
                 fixture_sha256=digest(args.fixture),
                 integration_sha256=digest(args.integration) if args.integration != "-" else None,
                 proposed_readiness={"ready": [], "pending": proof_rows})
    serialized = json.dumps(proof, indent=2) + "\n"
    if args.out == "-":
        print(serialized, end="")
    else:
        Path(args.out).write_text(serialized)


if __name__ == "__main__":
    main()
