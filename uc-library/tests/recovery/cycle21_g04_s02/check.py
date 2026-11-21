"""Replay numeric, string and color transfers with actual CCL parameters."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

MANGLED = "_ZN8Presonus17LinkableComponent10syncParamsERN4Core8Portable9ParameterES4_b"
DOMAIN = ("ARM dispatch hooks compare numeric get/set, string to/from with "
          "256-byte buffer, color cast/get/set and rejected destination cast. "
          "Real CCL host parameters compare value and edit notification for "
          "each case, including untouched numeric destination on mismatch.")

ORIGINAL = {'address': 534092,
 'anchor': '5436fd4011eed22dd7a3a5db5a085bda6d9d7f8176a6803776e5851b589ad43b',
 'firmware': 'RM/RML mixer 13731',
 'mangled': '_ZN8Presonus17LinkableComponent10syncParamsERN4Core8Portable9ParameterES4_b',
 'original_elf_sha256': '9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07',
 'role': 'server',
 'section': 12,
 'size': 264}
SOURCES = ['include/presonus/LinkableComponent.hpp', 'src/Presonus/LinkableComponent.cpp']
PROVIDERS = ['third_party/ccl-framework/core/portable/corecomponent.cpp',
 'third_party/ccl-framework/core/portable/corecomponent.h',
 'third_party/ccl-framework/core/portable/coreparams.cpp',
 'third_party/ccl-framework/core/portable/coreparams.h',
 'third_party/ccl-framework/core/portable/coreparaminfo.h']
DECLARATION_LIMIT = 'Original ordinary return spelling unresolved. Portable non-static void interface is provisional.'


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
    for row in fixtures["elf_observations"]:
        expected = list(map(str, row["copied"])) if row["copied"] else ["-2", "0"]
        observed = subprocess.check_output([str(executable.resolve()), row["mode"],
                                            str(row["edit"])], text=True).split()
        assert observed == expected, (row, observed, expected)
    return len(fixtures["elf_observations"])

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
