"""Check exact emission and compare portable state observations with ARM fixtures."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from native import ADDRESS, ELF_SHA, NAME, SLOT, TABLES, WORDS

TASK = "cycle20_g04_s06"
SOURCE_FILES = [
    "include/presonus/mixer/ChannelComponent.hpp",
    "src/Presonus/Mixer/ChannelComponent.cpp",
]
CORE_FILES = [
    "third_party/ccl-framework/core/portable/corecomponent.h",
    "third_party/ccl-framework/core/portable/corecomponent.cpp",
    "third_party/ccl-framework/core/portable/coreparaminfo.h",
    "third_party/ccl-framework/core/portable/coreparams.h",
    "third_party/ccl-framework/core/portable/coreparams.cpp",
]
DOMAIN = (
    "Offline direct and virtual GEQ scaler default calls with five pairs of raw float "
    "words covering signs, ordinary values, subnormal, infinities, and quiet NaN. "
    "ARM executes the exact body directly and through three original primary table "
    "address points. Compare unchanged state against portable ChannelComponent and "
    "inherited dispatch using bound ChannelState and a real pinned CCL NumericParam. "
    "Separately verify one derived override receives both original float words."
)
LIMITS = [
    "The original return declaration, class layout and ARM ABI remain unresolved.",
    "Native virtual entry uses an explicit two-instruction ARM dispatch harness, "
    "original ELF table bytes, and a modeled receiver. Native callers and object "
    "construction are outside the replay.",
    "Portable replay compares selected typed state, parameter and environment fields. "
    "Native InputComponent and OutputComponent table selections are compared with "
    "portable inherited dispatch, without asserting equivalent host subclass layouts.",
]


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify_symbol_and_table(path):
    listing = subprocess.check_output(["nm", "--defined-only", path], text=True)
    names = [line.split() for line in listing.splitlines()]
    vtable = TABLES[0][0]
    assert sum(len(row) == 3 and row[1] in {"T", "W"} and row[2] == NAME
               for row in names) == 1, NAME
    assert sum(len(row) == 3 and row[2] == vtable for row in names) == 1, vtable
    relocations = subprocess.check_output(["objdump", "-r", path], text=True)
    sections = relocations.split("RELOCATION RECORDS FOR [")
    table_sections = [block for block in sections if block.split("]", 1)[0].endswith(vtable)]
    assert len(table_sections) == 1
    assert NAME in table_sections[0], "Portable vtable must reference exact method"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", required=True, type=Path)
    parser.add_argument("--object", required=True, type=Path)
    parser.add_argument("--exe", type=Path)
    parser.add_argument("--integration", default="-")
    parser.add_argument("--out", default="-")
    args = parser.parse_args()
    verify_symbol_and_table(args.object)
    if args.exe is None:
        print(NAME)
        return
    fixture = json.loads(args.fixture.read_text())
    original = fixture["original"]
    assert fixture["elf_sha256"] == ELF_SHA
    assert (original["mangled"], original["address"], original["size"],
            original["section"]) == (NAME, ADDRESS, 16, ".text")
    assert fixture["vtable_slot_from_address_point"] == SLOT
    cases = fixture["cases"]
    expected_inputs = [[route, *words] for route in range(len(TABLES) + 1) for words in WORDS]
    assert [case["inputs"] for case in cases] == expected_inputs
    inputs = "".join(" ".join(map(str, values)) + "\n" for values in expected_inputs)
    run = subprocess.run([str(args.exe.resolve())], text=True, input=inputs,
                         capture_output=True, check=True)
    actual = [list(map(int, line.split())) for line in run.stdout.splitlines()]
    assert len(actual) == len(cases)
    for case, row in zip(cases, actual):
        _, scale_bits, offset_bits = case["inputs"]
        assert row == [int(case["state_unchanged"]), 1, 1, scale_bits, offset_bits], (
            case["inputs"], row)
    pending = dict(original_elf_sha256=ELF_SHA, mangled=NAME, cpp_compiled=True,
                   mangling_namespace_checked=True, cpp_differential_passed=True,
                   portable_ready=False, validation_domain=DOMAIN,
                   declaration_uncertainties=[LIMITS[0]],
                   sources={path: digest(Path("uc-library") / path) for path in SOURCE_FILES},
                   repository_sources={path: digest(path) for path in CORE_FILES})
    proof = dict(version=1, task_id=TASK, success=True, validation_domain=DOMAIN,
                 cpp_differential_passed=True, mangling_namespace_checked=True,
                 mangled_names=[NAME], limitations=LIMITS, original=original,
                 observed_native_vtables=fixture["observed_vtables"],
                 native_completed_cases=len(cases), portable_cases=len(actual),
                 observed_portable_rows=actual, object_sha256=digest(args.object),
                 executable_sha256=digest(args.exe), fixture_sha256=digest(args.fixture),
                 integration_sha256=digest(args.integration) if args.integration != "-" else None,
                 proposed_readiness={"ready": [], "pending": [pending]})
    result = json.dumps(proof, indent=2) + "\n"
    if args.out == "-":
        print(result, end="")
    else:
        Path(args.out).write_text(result)


if __name__ == "__main__":
    main()
