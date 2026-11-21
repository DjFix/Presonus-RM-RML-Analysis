"""Fresh scoped ARM and actual CCL differential check."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from native import ADDRESS, BODY_SHA, OFFSET, SIZE, observe_elf

ROOT = Path(__file__).resolve().parents[4]
ORIGINAL = {'address': 617064,
 'anchor': 'e3b6655556b8ce3c008b62c2866efc79b3c89d675bee60305629b3b52f162de9',
 'firmware': 'CS18AI surface 13840',
 'mangled': '_ZN8Presonus7Surface23AssignEditPageComponent18updateAliasTargetsEv',
 'original_elf_sha256': '304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0',
 'role': 'client',
 'section': 12,
 'size': 964}
SOURCES = ['include/presonus/surface/AssignEditPageComponent.hpp',
 'src/Presonus/Surface/AssignEditPageComponent.cpp',
 'include/presonus/PageComponent.hpp',
 'src/Presonus/PageComponent.cpp',
 'include/presonus/surface/MixerPageComponent.hpp',
 'src/Presonus/Surface/MixerPageComponent.cpp']
PROVIDERS = ['third_party/ccl-framework/core/portable/corecomponent.cpp',
 'third_party/ccl-framework/core/portable/corecomponent.h',
 'third_party/ccl-framework/core/portable/coreparams.cpp',
 'third_party/ccl-framework/core/portable/coreparams.h']
DOMAIN = 'CS18 alias refresh with hidden page, missing mixer/group, main input, return, slave input, absent selection and unrelated selection. Exact ARM name formats, RTTI type identities, group and selected slots, tag lookups and reconnect order. Actual host CCL alias state includes missing alias, non-alias collision, fallback null and preserved targets.'
BOUNDARIES = 'Mixer +0x20 exact getChannelGroup, +0x28 getSlaveMixer, +0x1c getSelectedChannel; page +0x18 findParameter. ARM __dynamic_cast uses Parameter and AliasParam RTTI records; the portable host uses pinned AliasParam::cast on actual CCL objects.'


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
