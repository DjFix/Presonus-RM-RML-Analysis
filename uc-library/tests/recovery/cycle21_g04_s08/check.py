"""Fresh exact ARM and actual CCL differential check for the scene callback."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from native import ADDRESS, BODY_SHA, ELF_SHA, MANGLED, OFFSET, SIZE, observe

ROOT = Path(__file__).resolve().parents[4]
SOURCES = (
    "include/presonus/surface/ScenesPageComponent.hpp",
    "src/Presonus/Surface/ScenesPageComponent.cpp",
    "include/presonus/surface/PresetsPageComponent.hpp",
    "src/Presonus/Surface/PresetsPageComponent.cpp",
    "include/presonus/PageComponent.hpp",
    "src/Presonus/PageComponent.cpp",
)
PROVIDERS = tuple("third_party/ccl-framework/core/portable/" + source for source in
                  ("corecomponent.h", "corecomponent.cpp", "coreparams.h", "coreparams.cpp"))
DOMAIN = ("CS18 local scene callback. Exact original ARM, visible and hidden page, "
          "changed/ignored messages, literal fsw_load match/miss, finite negative/"
          "zero/positive CCL values, forwarded preset selection and dirty state "
          "before visibility, and local recall with usable or absent mixer state.")
BOUNDARIES = ("Original direct PresetsPage callback executes in independent "
              "host-provider mode. ARM NumericParam +0x44 getValue and scene "
              "+0x54 PresetsPage recall are bound to verified original vtable words. "
              "ARM libgcc comparison executes directly; recall is captured by a local "
              "no-hardware boundary.")
LIMIT = ("Original class hierarchy, layout and complete declaration remain unresolved. "
         "The portable callback uses existing Presets composition and an explicitly "
         "bound PageComponent. Stable receiver, CCL parameters and provider inputs only.")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("exe", "object", "fixtures", "integration", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    symbols = subprocess.check_output(["nm", "--defined-only", str(args.object)], text=True)
    matches = [line for line in symbols.splitlines() if line.split()[-1:] == [MANGLED]]
    assert len(matches) == 1, matches
    fixtures = json.loads(args.fixtures.read_text())
    assert observe(args.exe) == fixtures
    for case in fixtures["cases"]:
        output = subprocess.check_output(
            [str(args.exe.resolve()), "scene", *map(str, case["args"])], text=True)
        assert list(map(int, output.split())) == case["expected"], (case, output)
    integration = json.loads(args.integration.read_text())
    assert isinstance(integration, dict) and integration
    row = {"original_elf_sha256": ELF_SHA, "mangled": MANGLED, "address": ADDRESS,
           "size": SIZE, "section": 12, "firmware": "CS18AI surface 13840", "role": "client",
           "domain": DOMAIN, "sources": {path: digest(ROOT / "uc-library" / path) for path in SOURCES},
           "repository_sources": {path: digest(ROOT / path) for path in PROVIDERS},
           "cpp_compiled": True, "mangling_namespace_checked": True,
           "portable_ready": False, "declaration_uncertainties": [LIMIT]}
    proof = {"behavior_passed": True, "domain": DOMAIN, "boundary_evidence": BOUNDARIES,
             "limitations": [LIMIT], "case_count": len(fixtures["cases"]),
             "compiled_mangled_names_matched": True, "compiled_symbols": matches,
             "native": fixtures, "original_range": {"sha256": BODY_SHA, "offset": OFFSET, "section": ".text"},
             "proposed_readiness": {"ready": [], "pending": [row]},
             "fixture_sha256": digest(args.fixtures), "object_sha256": digest(args.object),
             "executable_sha256": digest(args.exe), "integration_sha256": digest(args.integration),
             "producer_sha256": digest(__file__), "native_sha256": digest(Path(__file__).with_name("native.py"))}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(proof, indent=2) + "\n")
    print(json.dumps({"behavior_passed": True, "cases": len(fixtures["cases"])}))


if __name__ == "__main__":
    main()
