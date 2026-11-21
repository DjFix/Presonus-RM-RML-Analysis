"""Fresh scoped ARM and actual CCL differential check."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from native import ADDRESS, BODY_SHA, OFFSET, SIZE, observe_elf

ROOT = Path(__file__).resolve().parents[4]
ORIGINAL = {'address': 118888,
 'anchor': 'bde153b7fd79f77bf8545861c4aa6ceddcbde4c017b3c9b1d0a21c46c6974ce2',
 'firmware': 'RM/RML mixer 13731',
 'mangled': '_ZN8Presonus5Mixer12AliasMapping7connectEPNS_24MixerClientComponentBaseE',
 'original_elf_sha256': '9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07',
 'role': 'server',
 'section': 12,
 'size': 156}
SOURCES = ['include/presonus/mixer/AliasMapping.hpp',
 'src/Presonus/Mixer/AliasMapping.cpp',
 'include/presonus/mixer/ControlMapping.hpp',
 'src/Presonus/Mixer/ControlMapping.cpp']
PROVIDERS = ['third_party/ccl-framework/core/portable/corecomponent.cpp',
 'third_party/ccl-framework/core/portable/corecomponent.h',
 'third_party/ccl-framework/core/portable/coreparams.cpp',
 'third_party/ccl-framework/core/portable/coreparams.h']
DOMAIN = 'RM native mapping with null mixer, nested path match, and missing path fallback. Compare pinned CCL AliasParam original, enabled state and affected target state for absent, disabled and enabled prior originals.'
BOUNDARIES = 'Exact AliasParam vtable slots +0x20 isEnabled and +0x24 enable. Initial get occurs after optional Component::lookupParameter. CCL lookup and alias provider execute in host replay.'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("exe", "object", "fixtures", "out", "integration"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    original = ORIGINAL["mangled"]
    symbols = subprocess.check_output(["nm", "--defined-only", str(args.object)], text=True)
    matches = [line for line in symbols.splitlines() if line.split()[-1:] == [original]]
    assert len(matches) == 1, matches
    fixtures = json.loads(args.fixtures.read_text())
    assert observe_elf() == fixtures["elf_observations"]
    for case in fixtures["elf_observations"]:
        output = subprocess.check_output([str(args.exe.resolve()), *map(str, case["args"])], text=True)
        received = list(map(int, output.split()))
        assert received == case["expected"], (case["args"], received, case["expected"])
    integration = json.loads(args.integration.read_text())
    assert isinstance(integration, dict) and integration
    uncertainty = "Original ordinary return or complete class declaration, original ownership/layout and ARM interoperability remain unresolved."
    row = {**ORIGINAL, "domain": DOMAIN,
           "sources": {path: digest(ROOT / "uc-library" / path) for path in SOURCES},
           "repository_sources": {path: digest(ROOT / path) for path in PROVIDERS},
           "cpp_compiled": True, "mangling_namespace_checked": True,
           "portable_ready": False, "declaration_uncertainties": [uncertainty]}
    proof = {"behavior_passed": True, "domain": DOMAIN, "boundary_evidence": BOUNDARIES,
             "limitations": [uncertainty, "Isolated original provider boundaries; no hardware or unrestricted reentry covered."],
             "case_count": len(fixtures["elf_observations"]), "compiled_symbols": matches,
             "original_range": {"sha256": BODY_SHA, "address": ADDRESS, "size": SIZE,
                                "file_offset": OFFSET, "section": ".text"},
             "proposed_readiness": {"ready": [], "pending": [row]},
             "fixture_sha256": digest(args.fixtures), "object_sha256": digest(args.object),
             "executable_sha256": digest(args.exe), "integration_sha256": digest(args.integration),
             "producer_sha256": digest(__file__),
             "oracle_producer_sha256": digest(Path(__file__).with_name("native.py"))}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(proof, indent=2) + "\n")
    print(json.dumps({"behavior_passed": True, "cases": len(fixtures["elf_observations"])}))


if __name__ == "__main__":
    main()
