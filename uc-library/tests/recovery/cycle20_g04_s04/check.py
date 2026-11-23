"""Compare the compiled portable callback against the sealed original observations."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from native import ELF_SHA, TARGETS

TASK = Path(__file__).parent.name
MANGLED, ADDRESS = TARGETS[TASK]
SOURCE = "src/Presonus/Mixer/MixerComponentBase.cpp"
PRIMARY = "include/presonus/mixer/MixerComponentBase.hpp"
DELEGATE = "include/presonus/mixer/MixerComponentBaseDelegate.hpp"
CORE = "third_party/ccl-framework/core/public/coreproperty.h"
DOMAINS = {
    "cycle20_g04_s02": "Direct property callback on an offline portable mixer. "
    "Compare three property tags, size and two payload words with original ARM. "
    "The original secondary thunk is range-checked observation only.",
    "cycle20_g04_s03": "False and true through the typed delegate observer "
    "interface. Compare the default receiver marker with ARM and separately "
    "verify that one local derived override receives each exact Boolean.",
    "cycle20_g04_s04": "Null and two live offline channel identities through "
    "the mixer delegate fan-out. Compare the default receiver marker with ARM "
    "and separately check single-call pointer identity on the derived observer.",
}
LIMITS = [
    "The original static return declaration, class layout and ARM ABI remain unresolved.",
    "ARM runs the exact standalone default callback to return, with guarded "
    "modeled receiver and argument memory and no providers or hardware.",
    "The host uses the existing source-port class model; the property direct "
    "entry point does not establish a native vtable or thunk layout.",
]


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def assert_symbol(path):
    listing = subprocess.check_output(["nm", "--defined-only", path], text=True)
    rows = [line.split() for line in listing.splitlines()]
    assert sum(len(row) == 3 and row[1] in {"T", "W"} and row[2] == MANGLED
               for row in rows) == 1, MANGLED


def replay(exe, cases):
    inputs = "".join(" ".join(map(str, case["inputs"])) + "\n" for case in cases)
    process = subprocess.run([str(exe.resolve())], input=inputs, text=True,
                             capture_output=True, check=True)
    actual = [list(map(int, row.split())) for row in process.stdout.splitlines()]
    assert len(actual) == len(cases), process.stdout
    for case, row in zip(cases, actual):
        assert case["outside_stack_accesses"] == 0
        projected = case["projected"]
        if TASK.endswith("03"):
            projected = [*projected, 1, case["inputs"][0]]
        elif TASK.endswith("04"):
            projected = [*projected, 1, 1]
        assert row == projected, (case["inputs"], row, projected)
    return actual


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", required=True, type=Path)
    parser.add_argument("--object", required=True, type=Path)
    parser.add_argument("--exe", type=Path)
    parser.add_argument("--integration", default="-")
    parser.add_argument("--out", default="-")
    args = parser.parse_args()
    assert_symbol(args.object)
    if args.exe is None:
        print(MANGLED)
        return
    fixture = json.loads(args.fixture.read_text())
    original = fixture["original"]
    assert fixture["elf_sha256"] == ELF_SHA
    assert (original["mangled"], original["address"], original["size"],
            original["section"]) == (MANGLED, ADDRESS, 16, ".text")
    cases = fixture["cases"]
    assert len(cases) == (2 if TASK.endswith("03") else 3)
    actual = replay(args.exe, cases)
    sources = [SOURCE, PRIMARY]
    if not TASK.endswith("02"):
        sources.append(DELEGATE)
    row = dict(original_elf_sha256=ELF_SHA, mangled=MANGLED, cpp_compiled=True,
               mangling_namespace_checked=True, cpp_differential_passed=True,
               portable_ready=False, validation_domain=DOMAINS[TASK],
               declaration_uncertainties=[LIMITS[0]],
               sources={path: digest(Path("uc-library") / path) for path in sources},
               repository_sources={CORE: digest(CORE)})
    proof = dict(version=1, task_id=TASK, success=True,
                 validation_domain=DOMAINS[TASK], limitations=LIMITS,
                 cpp_differential_passed=True, mangling_namespace_checked=True,
                 mangled_names=[MANGLED], observed_symbol=MANGLED, original=original,
                 native_completed_cases=len(cases), portable_cases=len(actual),
                 observed_portable_rows=actual,
                 observed_native_ranges=[original, *fixture["observation_only_ranges"]],
                 object_sha256=digest(args.object), fixture_sha256=digest(args.fixture),
                 executable_sha256=digest(args.exe),
                 integration_sha256=digest(args.integration) if args.integration != "-" else None,
                 proposed_readiness={"ready": [], "pending": [row]})
    result = json.dumps(proof, indent=2) + "\n"
    if args.out == "-":
        print(result, end="")
    else:
        Path(args.out).write_text(result)


if __name__ == "__main__":
    main()
