"""Compare the compiled portable method with independently recorded ARM observations."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from native import SPECS, TASK

DOMAIN = 'Offline authentic RM C1 and C2 AutoFilterGroupManager construction on an empty or three-channel borrowed local roster with cold and warm category state. Compare observer count, ordered channel identities, real pinned CCL name and notification dispatch. Additional portable checks cover detachment and failed partial registration.'
LIMITS = ['Original ARM class inheritance, layout, exception cleanup semantics and ABI remain unresolved. Host constructor C1/C2 alias, while both original ranges are distinct and independently executed.', 'Native executes the actual named AutoFilterGroupManager C1/C2 and local ServerComponent initialization bodies. Named CCL, allocation, observer construction and category boundaries are modeled in native replay. Portable replay uses the real typed providers.', 'Portable category names already use immutable application literals. The native lazy category cache is observed independently. Roster contract requires live channels with parameter tag 25; portable null rejection and rollback are intentional source behavior.']
SOURCES = ['include/presonus/mixer/AutoFilterGroupManager.hpp', 'src/Presonus/Mixer/AutoFilterGroupManager.cpp']
CORE = ['third_party/ccl-framework/core/portable/corecomponent.h', 'third_party/ccl-framework/core/portable/corecomponent.cpp', 'third_party/ccl-framework/core/portable/coreparams.h', 'third_party/ccl-framework/core/portable/coreparams.cpp', 'third_party/ccl-framework/core/public/corestringbuffer.h', 'third_party/ccl-framework/core/public/corevector.h']


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
    assert len(set(result.values())) == 1, result
    complete = subprocess.check_output(["nm", path], text=True)
    reserved = {"_ZN8Presonus2UC15ServerComponentC1EPKc",
                "_ZN8Presonus2UC15ServerComponentC2EPKc"}
    assert not reserved.intersection(line.split()[-1] for line in complete.splitlines() if line.strip())
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
                 constructor_aliases={"host_C1_C2_alias": True,
                                      "native_C1_C2_alias": False},
                 reserved_server_constructor_symbols_absent=True,
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
