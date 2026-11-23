"""Verify the shared compiled symbol and compare typed replay with each ELF."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from native import MANGLED, ORIGINALS, SHAPES

ROOT = Path(__file__).resolve().parents[4]
SOURCES = ("include/presonus/SLChannel.hpp", "src/Presonus/SLChannel.cpp")
CORE_SOURCES = tuple("third_party/ccl-framework/core/" + path for path in (
    "portable/corecomponent.cpp", "portable/corecomponent.h",
    "portable/coreparams.cpp", "portable/coreparams.h", "public/corevector.h",
))
UNCERTAINTIES = [
    "The exact original ordinary return declaration and vtable layout remain unresolved.",
]
DOMAIN = (
    "Six cases per original, direct and ELF-vtable dispatch for empty, single and "
    "mixed duplicate/null entries. Native receiver/vector/backing/pointee canaries "
    "remain byte-identical with no nonstack writes. Typed portable base preserves "
    "actual CCL vector count, capacity, delta, backing address and entry identity/"
    "order plus both real NumericParam values and receiver class identity."
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", type=Path)
    parser.add_argument("--fixture", type=Path)
    parser.add_argument("--object", type=Path, required=True)
    parser.add_argument("--integration", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    symbols = subprocess.check_output(["nm", "--defined-only", str(args.object)], text=True)
    assert any(row.split()[-2:] == ["T", MANGLED] for row in symbols.splitlines())
    if args.exe is None:
        return

    fixture = json.loads(args.fixture.read_text())
    assert [entry["role"] for entry in fixture["originals"]] == list(ORIGINALS)
    observations = []
    pending = []
    for original in fixture["originals"]:
        role = original["role"]
        assert original["elf_sha256"] == ORIGINALS[role][0]
        assert original["original"]["mangled"] == MANGLED
        cases = original["cases"]
        assert len(cases) == 6 and {(c["route"], c["shape"]) for c in cases} == {
            (route, shape) for route in ("direct", "vtable") for shape in SHAPES
        }
        for case in cases:
            output = subprocess.check_output(
                [str(args.exe.resolve()), case["route"], case["shape"]], text=True,
            ).strip()
            expected = case["receiver_unchanged"] and case["vector_and_pointees_unchanged"]
            assert expected and output == str(int(expected))
            observations.append({"role": role, "route": case["route"], "shape": case["shape"],
                                 "receiver_and_vector_unchanged": True})
        pending.append({
            "original_elf_sha256": original["elf_sha256"], "mangled": MANGLED,
            "cpp_compiled": True, "mangling_namespace_checked": True,
            "cpp_differential_passed": True, "portable_ready": False,
            "declaration_uncertainties": UNCERTAINTIES,
            "validation_domain": DOMAIN,
            "sources": {name: digest(ROOT / "uc-library" / name) for name in SOURCES},
            "repository_sources": {name: digest(ROOT / name) for name in CORE_SOURCES},
        })
    receipt = {
        "success": True, "validation_domain": DOMAIN, "cases": len(observations),
        "native_ranges": [{key: value for key, value in row.items() if key != "cases"}
                          for row in fixture["originals"]],
        "portable_observations": observations, "observed_symbol": MANGLED,
        "fixture_sha256": digest(args.fixture), "executable_sha256": digest(args.exe),
        "object_sha256": digest(args.object), "replay_sha256": digest(Path(__file__)),
        "integration_sha256": (
            digest(args.integration)
            if args.integration and args.integration != Path("-") else None
        ),
        "proposed_readiness": {"ready": [], "pending": pending},
    }
    if args.out and args.out != Path("-"):
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
