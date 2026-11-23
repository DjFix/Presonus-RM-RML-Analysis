"""Check exact portable symbol and typed roster results against ARM observations."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
MANGLED = "_ZNK8Presonus5Panel14PanelComponent9isInGroupEiRKN4Core8Portable9ParameterE"
RESERVED = "_ZNK8Presonus5Panel16ControlRegistrar9findGroupEi"
ELF = "9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07"
SOURCES = (
    "include/presonus/panel/PanelComponent.hpp",
    "src/Presonus/Panel/PanelComponent.cpp",
    "include/presonus/panel/control.hpp",
    "include/presonus/panel/registrar_group_registry.hpp",
    "include/presonus/surface_panel/ControlGroup.hpp",
    "include/presonus/surface_panel/ControlHelpers.hpp",
    "src/Presonus/Panel/ControlRegistrarAccess.cpp",
    "src/Presonus/Panel/control.cpp",
    "src/surface_panel/ControlGroup.cpp",
)
CORE = tuple("third_party/ccl-framework/core/" + relative for relative in (
    "portable/coreparams.h",
    "portable/coreparams.cpp",
    "portable/corecomponent.h",
    "portable/corecomponent.cpp",
    "public/corevector.h",
))
DOMAIN = (
    "Twelve valid borrowed typed roster cases against actual RM ARM caller, "
    "findGroup, group count/at and control parameter getter. Covers empty roster, "
    "empty selected group, cold/warm missing-group zero-count sentinel, first/"
    "middle/last identity hits, null control parameter, same-valued distinct "
    "parameters, duplicate group IDs with first-match selection, a negative ID "
    "and absent identities. Portable bound registrar and controls use pinned CCL "
    "vectors and NumericParam; the native guard/atexit edges are fixture stubs."
)
UNCERTAINTIES = [
    "Native returns 0 or 1 in the replay domain; the exact source return declaration is unresolved.",
    "Original receiver/registrar layout, ownership and ARM interoperability are unresolved.",
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replay(exe, fixture):
    assert fixture["elf_sha256"] == ELF
    assert fixture["ranges"]["predicate"]["mangled"] == MANGLED
    assert fixture["ranges"]["findGroup"]["mangled"] == RESERVED
    assert len(fixture["cases"]) == 12
    observations = []
    for case in fixture["cases"]:
        assert case["input_state_unchanged"]
        groups = case["groups"]
        items = [case["query"], case["parameter"], len(groups)]
        for group, parameters in groups:
            items += [group, len(parameters)]
            items += [-1 if param is None else param for param in parameters]
        output = subprocess.check_output(
            [str(exe.resolve())], input=" ".join(map(str, items)), text=True,
        ).strip()
        assert output == str(int(case["member"])), (case, output)
        observations.append({"query": case["query"], "member": output == "1"})
    return observations


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", type=Path)
    parser.add_argument("--fixture", type=Path)
    parser.add_argument("--object", type=Path, required=True)
    parser.add_argument("--integration", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    symbols = subprocess.check_output(["nm", str(args.object)], text=True).splitlines()
    assert any(row.split()[-2:] == ["T", MANGLED] for row in symbols)
    assert all(row.split()[-1] != RESERVED for row in symbols if row.split())
    if args.exe is None:
        return

    fixture = json.loads(args.fixture.read_text())
    observations = replay(args.exe, fixture)
    proof = {
        "success": True, "validation_domain": DOMAIN, "cases": len(observations),
        "observed_symbol": MANGLED, "native_ranges": fixture["ranges"],
        "portable_observations": observations,
        "fixture_sha256": sha(args.fixture), "object_sha256": sha(args.object),
        "executable_sha256": sha(args.exe), "replay_sha256": sha(Path(__file__)),
        "integration_sha256": (
            sha(args.integration)
            if args.integration and args.integration != Path("-") else None
        ),
        "proposed_readiness": {"ready": [], "pending": [{
            "original_elf_sha256": ELF, "mangled": MANGLED,
            "cpp_compiled": True, "mangling_namespace_checked": True,
            "cpp_differential_passed": True, "portable_ready": False,
            "declaration_uncertainties": UNCERTAINTIES,
            "validation_domain": DOMAIN,
            "sources": {name: sha(ROOT / "uc-library" / name) for name in SOURCES},
            "repository_sources": {name: sha(ROOT / name) for name in CORE},
        }]},
    }
    if args.out and args.out != Path("-"):
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(proof, indent=2) + "\n")
    print(json.dumps(proof))


if __name__ == "__main__":
    main()
