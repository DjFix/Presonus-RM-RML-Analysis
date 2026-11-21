"""Replay alias registration, tag indexing and connection teardown with CCL."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

MANGLED = "_ZN8Presonus21MappablePageComponent8addAliasEiPKc"
DOMAIN = ("Positive and negative native tags, successful cast and storage, "
          "growth/no growth, and native-only provider/cast/resize failures. "
          "Host CCL replay of successful registration preserves parameter ownership, "
          "name/tag lookup, and observes borrowed collection membership via "
          "connect followed by disconnectMappables.")

ORIGINAL = {'address': 380568,
 'anchor': '6377bea0f243723222b8770abd54961a82ff3ff3331c68ed8ba115218624ec47',
 'firmware': 'CS18AI surface 13840',
 'mangled': '_ZN8Presonus21MappablePageComponent8addAliasEiPKc',
 'original_elf_sha256': '304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0',
 'role': 'client',
 'section': 12,
 'size': 148}
SOURCES = ['include/presonus/MappablePageComponent.hpp', 'src/Presonus/MappablePageComponent.cpp']
PROVIDERS = ['third_party/ccl-framework/core/portable/corecomponent.cpp',
 'third_party/ccl-framework/core/portable/corecomponent.h',
 'third_party/ccl-framework/core/portable/coreparams.cpp',
 'third_party/ccl-framework/core/portable/coreparams.h',
 'third_party/ccl-framework/core/portable/coreparaminfo.h',
 'third_party/ccl-framework/core/public/corevector.h']
DECLARATION_LIMIT = 'Original ordinary return spelling unresolved. Portable void interface is provisional.'


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
    count = 0
    for row in fixtures["elf_observations"]:
        if row["boundary"] != "ok":
            assert not row["stored_alias"] and row["collected"] == 0, row
            continue
        size = row["initial_param_count"]
        expected = [row["used_tag"], size + 1, 1, 1, int(row["stored_alias"])]
        observed = subprocess.check_output([str(executable.resolve()), str(row["tag"]),
                                            str(size)], text=True).split()
        assert list(map(int, observed)) == expected, (row, observed, expected)
        count += 1
    return count

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
