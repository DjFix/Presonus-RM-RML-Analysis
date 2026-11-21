"""Replay CCL child-load and alternate storage cases against a built executable."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

MANGLED = "_ZN8Presonus17LinkableComponent4loadERKN4Core8Portable12InputStorageE"
DOMAIN = ("A real CCL child returns false/true, with optional incoming altmem "
          "and ordinary/ignoreAltMemory storage. Check original base and helper "
          "call order/arguments, propagated result, child observation of the "
          "prior alternate state, and final alternate state.")


ORIGINAL = {'address': 536212,
 'anchor': '99319630c4d369c9821b0e75e5471a89970c55c21b83230c287b22cd85a54e18',
 'firmware': 'RM/RML mixer 13731',
 'mangled': '_ZN8Presonus17LinkableComponent4loadERKN4Core8Portable12InputStorageE',
 'original_elf_sha256': '9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07',
 'role': 'server',
 'section': 12,
 'size': 56}
SOURCES = ['include/presonus/LinkableComponent.hpp', 'src/Presonus/LinkableComponent.cpp']
PROVIDERS = ['third_party/ccl-framework/core/portable/corecomponent.cpp',
 'third_party/ccl-framework/core/portable/corecomponent.h',
 'third_party/ccl-framework/core/portable/coreparams.cpp',
 'third_party/ccl-framework/core/portable/coreparams.h',
 'third_party/ccl-framework/core/portable/coreattributes.cpp',
 'third_party/ccl-framework/core/portable/coreattributes.h',
 'third_party/ccl-framework/core/portable/corestorage.h']
DECLARATION_LIMIT = 'Original ordinary return spelling and inheritance unresolved. Host bool follows pinned CCL Component.'


def readiness_row():
    root = Path(__file__).resolve().parents[4]
    return {**ORIGINAL, "domain": DOMAIN,
            "sources": {p: digest(root / "uc-library" / p) for p in SOURCES},
            "repository_sources": {p: digest(root / p) for p in PROVIDERS},
            "cpp_compiled": True, "mangling_namespace_checked": True,
            "portable_ready": False, "declaration_uncertainties": [DECLARATION_LIMIT]}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_symbols(path):
    output = subprocess.check_output(["nm", "--defined-only", str(path)], text=True)
    matches = [line for line in output.splitlines()
               if line.split()[-1:] == [MANGLED]]
    assert len(matches) == 1, matches
    return matches


def compare(executable, fixtures):
    native = {row["base_result"]: row for row in fixtures["elf_observations"]}
    for child_result, incoming, ignored in fixtures["local_domains"]:
        original = native[child_result]
        helper = "loadAltMemory" in original["events"] and not ignored
        expected = [1, 1, original["return"], int(not helper), int(helper and bool(incoming))]
        observed = subprocess.check_output([str(executable.resolve()), str(child_result),
                                            str(incoming), str(ignored)], text=True)
        assert list(map(int, observed.split())) == expected, (observed, expected)
    return len(fixtures["local_domains"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("exe", "object", "fixtures", "out", "integration"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    symbols = verify_symbols(args.object)
    count = compare(args.exe, json.loads(args.fixtures.read_text()))
    integration = json.loads(args.integration.read_text())
    assert isinstance(integration, dict) and integration
    proof = {"behavior_passed": True, "domain": DOMAIN, "case_count": count,
             "compiled_symbols": symbols,
             "proposed_readiness": {"ready": [], "pending": [readiness_row()]}, "fixture_sha256": digest(args.fixtures),
             "executable_sha256": digest(args.exe), "object_sha256": digest(args.object),
             "integration_sha256": digest(args.integration)}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(proof, indent=2) + "\n")
    print(json.dumps(proof))


if __name__ == "__main__":
    main()
