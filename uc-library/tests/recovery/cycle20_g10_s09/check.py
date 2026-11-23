"""Compare typed portable results to sealed per-ELF observations."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

TASK = "09"
ROOT = Path(__file__).resolve().parents[4]
DOMAINS = {
    "13": "Absent and finite bounded NumericParam values in both roles, including signed fractional truncation.",
    "14": "Absent and real typed CCL ColorParam values in both roles, including alpha and RGBA ordering.",
    "16": "Absent parent, first/middle/last and absent roster member, with actual pinned CCL child ordering.",
    "19": "Empty, single and ordered mixed bindings. Original calls setParameter(nullptr,0) on each entry. Actual typed Control observer detach retains roster.",
    "20": "Empty, single and mixed null bindings. Actual native Control getter and virtual reset(true) in order. Typed CCL NumericParam defaults and roster preserved.",
    "09": "Direct no-effect static element redraw requests on both boolean values and seeded typed receiver state.",
    "10": "Both C1/C2 in each role, actual parent initialization and three signed geometry cases with fifth integer preserved.",
    "11": "In-memory bitmap rendering via exact native IDisplay fillRect slot. Rectangle forwarded and dirty cleared.",
    "12": "Both C1/C2 in each role with real Offscreen base and bounded empty, short and spaced text copying.",
}
SOURCE_SETS = {
    "channel": ("include/presonus/SLChannel.hpp", "src/Presonus/SLChannel.cpp"),
    "group": ("include/presonus/surface_panel/ControlGroup.hpp", "src/surface_panel/ControlGroup.cpp",
              "include/presonus/panel/control.hpp", "src/Presonus/Panel/control.cpp"),
    "fill": ("include/presonus/panel/FillElement.hpp", "src/Presonus/Panel/FillElement.cpp",
             "include/presonus/panel/Element.hpp", "src/Presonus/Panel/Element.cpp"),
    "static": ("include/presonus/panel/StaticElement.hpp", "src/Presonus/Panel/StaticElement.cpp",
               "include/presonus/panel/Element.hpp", "src/Presonus/Panel/Element.cpp",
               "include/presonus/panel/OffscreenElement.hpp", "src/Presonus/Panel/OffscreenElement.cpp"),
}
FAMILY = "static"
CORE = ("third_party/ccl-framework/core/portable/corecomponent.cpp",
        "third_party/ccl-framework/core/portable/corecomponent.h",
        "third_party/ccl-framework/core/portable/coreparams.cpp",
        "third_party/ccl-framework/core/portable/coreparams.h",
        "third_party/ccl-framework/core/public/corevector.h",
        "third_party/ccl-framework/core/public/gui/corecolor.h") if FAMILY in ("channel", "group") else ()
UNCERTAINTIES = ["Exact ordinary return declaration, full original class layout and ARM interoperability remain unresolved."]
if TASK in ("10", "12"):
    UNCERTAINTIES = ["The source constructor models observed initialized state; original complete class layout and ARM ABI remain unresolved."]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--object", required=True, type=Path)
    parser.add_argument("--exe", type=Path)
    parser.add_argument("--fixture", required=True, type=Path)
    parser.add_argument("--integration", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    fixture = json.loads(args.fixture.read_text())
    assert fixture["task"] == TASK
    symbols = subprocess.check_output(["nm", "--defined-only", str(args.object)], text=True).splitlines()
    definitions = {row.split()[-1] for row in symbols if len(row.split()) == 3 and row.split()[1] in ("T", "W")}
    assert {row["range"]["mangled"] for row in fixture["originals"]} <= definitions
    if args.exe is None:
        return

    observations, pending = [], []
    identities = set()
    for native in fixture["originals"]:
        elf = native["elf_sha256"]
        mangled = native["range"]["mangled"]
        assert (elf, mangled) not in identities
        identities.add((elf, mangled))
        for case in native["cases"]:
            output = subprocess.check_output(
                [str(args.exe.resolve()), *map(str, case["inputs"])], text=True,
            ).strip()
            expected = case["output"]
            observed = ([int(value) for value in output.split()] if isinstance(expected, list)
                        else output if isinstance(expected, str) else int(output))
            assert observed == expected, (case, observed)
            observations.append({"elf_sha256": elf, "mangled": mangled,
                                 "inputs": case["inputs"], "output": observed})
        pending.append({
            "original_elf_sha256": elf, "mangled": mangled,
            "cpp_compiled": True, "mangling_namespace_checked": True,
            "cpp_differential_passed": True, "portable_ready": False,
            "declaration_uncertainties": UNCERTAINTIES, "validation_domain": DOMAINS[TASK],
            "sources": {name: sha(ROOT / "uc-library" / name) for name in SOURCE_SETS[FAMILY]},
            "repository_sources": {name: sha(ROOT / name) for name in CORE},
        })
    data = {
        "success": True, "validation_domain": DOMAINS[TASK], "cases": len(observations),
        "native_ranges": [row["range"] for row in fixture["originals"]],
        "portable_observations": observations, "fixture_sha256": sha(args.fixture),
        "object_sha256": sha(args.object), "executable_sha256": sha(args.exe),
        "replay_sha256": sha(__file__),
        "integration_sha256": sha(args.integration) if args.integration and args.integration != Path("-") else None,
        "proposed_readiness": {"ready": [], "pending": pending},
    }
    if args.out and args.out != Path("-"):
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(data, indent=2) + "\n")
    print(json.dumps(data))


if __name__ == "__main__":
    main()
