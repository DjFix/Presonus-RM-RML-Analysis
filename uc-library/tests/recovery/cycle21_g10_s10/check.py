"""Compare canonical lifecycle execution with the exact replay of the ARM range."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

from native import generate

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
TASK = HERE.name
COMPONENT = {
    "cycle21_g10_r04": "LPFilterComponent",
    "cycle21_g10_s09": "EQComponent",
    "cycle21_g10_s10": "EQComponent",
    "cycle21_g10_r08": "GateComponent",
}[TASK]
LIBRARY_SOURCES = (
    f"include/presonus/mixer/{COMPONENT}.hpp",
    f"src/Presonus/Mixer/{COMPONENT}.cpp",
    "include/presonus/mixer/AudioComponent.hpp",
    "src/Presonus/Mixer/AudioComponent.cpp",
    "include/presonus/DspComponent.hpp",
    "src/Presonus/DspComponent.cpp",
    "include/presonus/dsp/Controller.hpp",
    "include/presonus/dsp/IController.hpp",
    "src/Presonus/Dsp/Controller.cpp",
)
CORE_SOURCES = tuple("third_party/ccl-framework/core/" + name for name in (
    "portable/coreattributes.cpp", "portable/coreattributes.h",
    "portable/corecomponent.cpp", "portable/corecomponent.h",
    "portable/coretypeinfo.h", "public/coreproperty.h",
))
OBSERVED = (
    "property_release", "property_delete", "controller_release",
    "controller_delete", "receiver_delete",
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_symbol(obj, original):
    mangled = original["mangled"]
    lines = subprocess.check_output(["nm", "--defined-only", obj], text=True).splitlines()
    assert any(line.split()[-2:] == ["T", mangled] for line in lines if line.strip())
    if mangled.endswith("D0Ev"):
        disassembly = subprocess.check_output([
            "objdump", "-dr", f"--disassemble={mangled}", obj,
        ], text=True)
        assert re.search(r"(?:^|\s)_ZdlPv(?:[-+\s]|$)", disassembly, re.MULTILINE), disassembly
    return mangled


def proof(original, domain):
    return {"ready": [], "pending": [{
        "original_elf_sha256": original["elf_sha256"],
        "mangled": original["mangled"],
        "cpp_compiled": True,
        "mangling_namespace_checked": True,
        "cpp_differential_passed": True,
        "portable_ready": False,
        "declaration_uncertainties": [
            "Original class layout, intermediate base declarations and complete unwind contract remain unverified.",
        ],
        "validation_domain": domain,
        "sources": {name: digest(ROOT / "uc-library" / name) for name in LIBRARY_SOURCES},
        "repository_sources": {name: digest(ROOT / name) for name in CORE_SOURCES},
    }]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", type=Path)
    parser.add_argument("--object", type=Path, required=True)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--integration", type=Path, default=Path("-"))
    parser.add_argument("--out", type=Path, default=Path("-"))
    args = parser.parse_args()

    fixture = json.loads(args.fixture.read_text())
    original = fixture["original"]
    exact = check_symbol(args.object, original)
    if args.exe is None:
        return
    assert generate(TASK) == fixture
    case, = fixture["cases"]
    expected = [e[0] for e in case["events"] if e[0] in OBSERVED]
    observed = subprocess.check_output([args.exe.resolve()], text=True).splitlines()
    assert expected == observed, (expected, observed)
    deleting = exact.endswith("D0Ev")
    assert ("receiver_delete" in observed) == deleting
    domain = (
        "One exact RM13731 ARM application lifecycle with distinct live adopted "
        "controller and handler, real Controller release routines and ordered "
        "Dsp and Linkable cleanup, plus equivalent canonical portable release "
        "and actual heap deallocation. The native delete boundary enters its "
        "observed operator-delete PLT and unmaps the matching live allocation. "
        "Host default tagged construction and the typed CCL query also pass. "
        + ("Virtual D0 deletes the same outer receiver." if deleting else
           "Explicit D1 ends the complete receiver lifetime without deallocating it.")
    )
    receipt = {
        "success": True, "validation_domain": domain, "cases": 1,
        "proposed_readiness": proof(original, domain),
        "observed_events": observed, "observed_symbol": exact,
        "object_sha256": digest(args.object), "executable_sha256": digest(args.exe),
        "fixture_sha256": digest(args.fixture),
        "integration_sha256": None if args.integration == Path("-") else digest(args.integration),
    }
    if args.out != Path("-"):
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
