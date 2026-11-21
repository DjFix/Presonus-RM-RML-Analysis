"""Verify exact original branches and replay current CCL-bound production code."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

from native import generate

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
TASK = HERE.name[-2:]
SOURCES = [
    "include/presonus/surface_panel/ControlHelpers.hpp",
    "src/Presonus/Surface/SurfaceRootComponent.cpp",
]
CORE = [
    "portable/corecomponent.h", "portable/corecomponent.cpp",
    "portable/coreparams.h", "portable/coreparams.cpp",
]
DOMAINS = {
    "05": "Nine original cases with mapping absent and all low-three-bit combinations of the actual CCL-backed Mapping provider. Exact original calls observe screen tag 31, lookup order, 1.0 edit-before-observe order, and the no-hardware-effects branches. Real CCL observes final page value and observer identity/order.",
    "06": "Exact ARM application jump-table routing for all tags 2–38, adjacent values and signed extremes. Each of six native route identities uses the corresponding admitted callback in the portable replay with independently distinguishable local CCL values and observer effects. Physical registrar paths remain outside this domain.",
    "07": "Four exact native input states, including initial singleton guard and absent/present surface section, observing real receiver/slot, remove/build/save order, literal key and dirty bit. Separately run pinned real SettingFile, AttributesBuilder, OutputStorage and Component::save against storable and transient parameters, replacing stale surface data and preserving an unrelated section. Independently flush and restore a file in isolated project test scratch.",
}
if TASK == "05":
    SOURCES += ["include/presonus/surface/MappingComponent.hpp",
                "src/Presonus/Surface/MappingComponent.cpp"]
if TASK == "07":
    CORE += ["portable/corepersistence.h", "portable/corepersistence.cpp",
             "portable/coreattributes.h", "portable/coreattributes.cpp",
             "portable/corestorage.h", "portable/corefile.h"]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replay(exe, cases):
    for case in cases:
        if TASK == "05":
            result = subprocess.check_output([
                str(exe), str(int(case["present"])), str(case["flags"]),
            ], text=True).splitlines()
            primitive = [e for e in case["events"] if e[0] in ("set", "add")]
            if primitive:
                assert primitive == [["set", 31, 0x3F800000, 1], ["add", 31]]
                assert result == ["set 1 1 0", "state 1 1 0"], (case, result)
            else:
                assert result == ["state 0 0 0"], (case, result)
        elif TASK == "06":
            routes = {
                "util": "1 0 0 1 1 1 1 1 1 1 1",
                "diagnostics": "1 1 0 1 0 1 1 1 1 1 1",
                "calibrate": "1 1 1 1 1 0 1 1 1 1 0",
                "fader": "1 1 1 1 1 1 0 1 1 1 1",
                "audio": "1 1 1 0 1 1 1 0 1 1 1",
                "touchscreen": "0 1 1 1 1 1 1 1 0 0 1",
                None: "1 1 1 1 1 1 1 1 1 1 1",
            }
            route = case["events"][0][0] if case["events"] else None
            host = subprocess.check_output([str(exe), str(case["tag"])], text=True)
            states = [line for line in host.splitlines() if line.startswith("state ")]
            assert states == ["state " + routes[route]], (case, states)
        else:
            scratch = ROOT / "temp/test-work"
            scratch.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix="cycle21_g10_s07-", dir=scratch) as directory:
                result = subprocess.check_output([
                    str(exe), str(int(case["present"])), str(int(case["dirty"])),
                ], cwd=directory, text=True).splitlines()
                assert Path(directory, "ui-settings.json").is_file()
            assert result == [f"dirty {bool(case['final_flags'] & 4):d}", "42 0 0 5",
                              "42 0 0 5", "stored 1"], (case, result)
            events = [row[0] for row in case["events"]]
            assert events[-4:] == ["remove_all", "builder", "save", "destroy_builder_vector"]
            assert ("make_attributes" in events) is not case["present"]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--object", type=Path, required=True)
    p.add_argument("--fixture", type=Path, required=True)
    p.add_argument("--exe", type=Path)
    p.add_argument("--integration", type=Path, default=Path("-"))
    p.add_argument("--out", type=Path, default=Path("-"))
    a = p.parse_args()
    fixture = json.loads(a.fixture.read_text())
    original = fixture["original"]
    mangled = original["mangled"]
    symbols = subprocess.check_output(["nm", "--defined-only", a.object], text=True)
    assert any(row.split()[-2:] == ["T", mangled] for row in symbols.splitlines() if row)
    if a.exe is None:
        return
    assert generate() == fixture
    replay(a.exe.resolve(), fixture["cases"])
    domain = DOMAINS[TASK]
    core = ["third_party/ccl-framework/core/" + name for name in CORE]
    row = {
        "original_elf_sha256": original["original_elf_sha256"], "mangled": mangled,
        "cpp_compiled": True, "mangling_namespace_checked": True,
        "cpp_differential_passed": True, "portable_ready": False,
        "validation_domain": domain,
        "declaration_uncertainties": ["Original ordinary return declaration and complete class layout remain unverified."],
        "sources": {name: digest(ROOT / "uc-library" / name) for name in SOURCES},
        "repository_sources": {name: digest(ROOT / name) for name in core},
    }
    proof = {
        "success": True, "validation_domain": domain, "cases": len(fixture["cases"]),
        "proposed_readiness": {"ready": [], "pending": [row]},
        "observed_symbol": mangled, "object_sha256": digest(a.object),
        "fixture_sha256": digest(a.fixture), "executable_sha256": digest(a.exe),
        "integration_sha256": None if a.integration == Path("-") else digest(a.integration),
    }
    if a.out != Path("-"):
        a.out.parent.mkdir(exist_ok=True, parents=True)
        a.out.write_text(json.dumps(proof, indent=2) + "\n")
    print(json.dumps(proof))


if __name__ == "__main__":
    main()
