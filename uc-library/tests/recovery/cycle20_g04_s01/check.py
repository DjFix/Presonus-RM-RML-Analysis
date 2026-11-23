"""Check the exact symbol and compare the portable CCL child/observer replay."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

TASK = "cycle20_g04_s01"
MANGLED = "_ZN8Presonus5Mixer18FilterGroupManager6notifyERKNS_2UC17MessageAttributesE"
ELF_HASH = "9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07"
DOMAIN = (
    "Stable four-child offline CCL tree with null, empty, case-mismatching and "
    "matching message IDs, signed in-domain reorder indices including first/last "
    "and same-index moves. Compare child identity order against ARM application "
    "execution with modeled child providers, plus actual CCL names, parentage "
    "and synchronous parameter callbacks. Observe invalid-old ARM calls up to "
    "the null removeChild boundary and check the separate portable safety guard."
)
LIMITS = [
    "Original ordinary return declaration, virtual dispatch interface, class layout, ARM ABI and hardware are unresolved.",
    "Native getID, strcmp, getInt, valid remove/insert, and reset use named boundary models. The fallback itself executes all four original instructions.",
    "Native invalid-old execution stops at the null child offered to removeChild. The portable guard is an explicit adaptation for pinned CCL's live-child precondition. No native invalid-old continuation or invalid-destination equivalence is claimed.",
    "Original reset internals are outside the new ARM replay. The portable replay uses the current canonical implementation and real pinned CCL children and parameter observers.",
]
SOURCE_FILES = [
    "include/presonus/mixer/FilterGroupManager.hpp",
    "src/Presonus/Mixer/FilterGroupManager.cpp",
]
CORE_FILES = [
    "third_party/ccl-framework/core/portable/coreattributes.h",
    "third_party/ccl-framework/core/portable/coreattributes.cpp",
    "third_party/ccl-framework/core/portable/corecomponent.h",
    "third_party/ccl-framework/core/portable/corecomponent.cpp",
    "third_party/ccl-framework/core/portable/coreparams.h",
    "third_party/ccl-framework/core/portable/coreparams.cpp",
    "third_party/ccl-framework/core/public/corevector.h",
    "third_party/ccl-framework/core/public/corestringbuffer.h",
]
INITIAL_NAMES = ["ch1", "fixed", "ch30", "ch4"]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check_symbol(obj):
    output = subprocess.check_output(["nm", "--defined-only", str(obj)], text=True)
    definitions = [line.split() for line in output.splitlines()]
    assert sum(len(row) == 3 and row[1] == "T" and row[2] == MANGLED
               for row in definitions) == 1, MANGLED


def expected_output(case):
    order = case["order"]
    names = INITIAL_NAMES.copy()
    changed = []
    if any(event[0] == "resetChannelNames" for event in case["trace"]):
        for index, child in enumerate(order, start=1):
            desired = f"ch{index}"
            if names[child].startswith("ch") and names[child] != desired:
                names[child] = desired
                changed.append(child)
    snapshot = ",".join(f"{child}:{names[child]}" for child in order)
    events = [f"{child}:{param}:{snapshot}" for child in changed for param in (0, 1)]
    return "|".join([snapshot, *events])


def replay(exe, cases):
    inputs = "".join(
        f"{int(message is not None)} {json.dumps(message or '')} {old} {new}\n"
        for message, old, new in (case["input"] for case in cases)
    )
    run = subprocess.run([str(exe.resolve())], input=inputs, check=True,
                         capture_output=True, text=True)
    rows = run.stdout.splitlines()
    assert len(rows) == len(cases), run
    for case, actual in zip(cases, rows):
        expected = expected_output(case)
        assert actual == expected, (case["input"], expected, actual)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", required=True, type=Path)
    parser.add_argument("--exe", type=Path)
    parser.add_argument("--object", required=True, type=Path)
    parser.add_argument("--integration", default="-")
    parser.add_argument("--out", default="-")
    args = parser.parse_args()
    obj = args.object
    check_symbol(obj)
    if args.exe is None:
        print(MANGLED)
        return
    fixture = json.loads(args.fixture.read_text())
    assert fixture["elf_sha256"] == ELF_HASH and fixture["ranges"][0]["mangled"] == MANGLED
    cases = fixture["cases"]
    rows = replay(args.exe, cases)
    passed_native = sum(case["original_completed"] for case in cases)
    pending = dict(
        original_elf_sha256=ELF_HASH, mangled=MANGLED, cpp_compiled=True,
        mangling_namespace_checked=True, cpp_differential_passed=True,
        portable_ready=False, validation_domain=DOMAIN,
        declaration_uncertainties=[LIMITS[0]],
        sources={path: digest(Path("uc-library") / path) for path in SOURCE_FILES},
        repository_sources={path: digest(path) for path in CORE_FILES},
    )
    result = dict(
        version=1, task_id=TASK, success=True, validation_domain=DOMAIN,
        cpp_differential_passed=True, mangling_namespace_checked=True,
        mangled_names=[MANGLED], limitations=LIMITS,
        native_completed_cases=passed_native, native_provider_boundary_cases=len(cases) - passed_native,
        portable_cases=len(rows), observed_portable_rows=rows,
        observed_symbol=MANGLED, object_sha256=digest(obj),
        fixture_sha256=digest(args.fixture), executable_sha256=digest(args.exe),
        integration_sha256=digest(args.integration) if args.integration != "-" else None,
        proposed_readiness={"ready": [], "pending": [pending]},
    )
    if args.out == "-":
        print(json.dumps(result, indent=2))
    else:
        Path(args.out).write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
