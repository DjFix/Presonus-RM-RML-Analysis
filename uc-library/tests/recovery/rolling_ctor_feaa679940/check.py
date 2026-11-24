"""Replay Linux source-port state and lifecycle against captured native boundaries."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

EXPECTED = {'mangled': '_ZN8Presonus7Surface20PreampsPageComponentC1EPKci', 'address': 582072, 'size': 76, 'section': '.text', 'elf_sha256': '304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0', 'firmware': 'CS18AI surface 13840', 'role': 'client'}
PREFIX = '_ZN8Presonus7Surface20PreampsPageComponent'
LEGACY_NAME = ''
SOURCES = {'include/presonus/surface/PreampsPageComponent.hpp': '72175e8233173e743e38adcea80ad47ecd90de3dc3de1c7c07e899d558467fcb', 'src/Presonus/Surface/PreampsPageComponent.cpp': '547298cc35338fa2ecd970b94137dae47b7ed80c1adb02446869fa944e3e77d0', 'include/presonus/PageComponent.hpp': '4564d19e2cc2b8c13d38697c89943c41947aa1af5f399b0e8079f919ae83e608', 'src/Presonus/PageComponent.cpp': 'a6c2c4de4a3847f05ce87d03a6aa74c746275cf0eb2bdf85e8092c15c8613270'}
CORE = {'third_party/ccl-framework/core/portable/corecomponent.h': '3c9507761a27b802d8221eaead5450aa612b85caa9d77b7ac4eb2a4d74aa24cb', 'third_party/ccl-framework/core/portable/corecomponent.cpp': '79fc17cf36a2946eac7293284ce693072a1875844736e4f1d70c48e6757ce7f6', 'third_party/ccl-framework/core/public/corestringbuffer.h': '46de7c2332457b082b9078b75b32ddb8ca35ce01d063fb9b330ffaa7e7acd55c'}
DOMAIN = 'Offline ARM C1 and C2 over four form/tag pairs, recording PageComponent receiver, both strings, signed tag word and three dispatch writes. Separate D1 and D0 native call-boundary traces. Linux replay checks descriptor, form truncation, tag and destruction of CCL-owned children, including historical source-port construction.'
LIMITATIONS = 'ARM PageComponent, Component destruction and operator delete are intercepted at observed native call boundaries. Linux calls the actual PageComponent and pinned CCL provider. Native dispatch values, original layout, actual native deallocation and hardware remain outside the portable claim. Only the packet-selected original identity is proposed.'

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", type=Path, required=True)
    parser.add_argument("--object", type=Path, required=True)
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--integration", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    fixture = json.loads(args.fixtures.read_text())
    integration = json.loads(args.integration.read_text())
    assert fixture["elf_sha256"] == EXPECTED["elf_sha256"]
    assert integration["platform"] == "linux"
    for path, expected in SOURCES.items():
        assert digest(Path("uc-library") / path) == expected, path
    for path, expected in CORE.items():
        assert digest(path) == expected, path
    nm = subprocess.check_output(["nm", "--defined-only", args.object], text=True)
    symbols = {line.split()[-1] for line in nm.splitlines() if line.split()}
    assert {PREFIX + suffix for suffix in ("C1EPKci", "C2EPKci", "D0Ev", "D1Ev")} <= symbols
    undefined = subprocess.check_output(["nm", "--undefined-only", args.object], text=True)
    assert "_ZN8Presonus13PageComponentC2EPKcS2_i" in undefined
    rows = [row for row in fixture["constructors"] if row["mangled"] == EXPECTED["mangled"]]
    assert len(rows) == 4
    observed = []
    executable = args.exe.resolve()
    for row in rows:
        assert all(row[key] == EXPECTED[key] for key in ("address", "size", "section"))
        call, = row["calls"]
        form, tag = call["form"], row["tag"]
        name = call["descriptor"]
        result = subprocess.check_output([executable, form, str(tag)], text=True).splitlines()
        assert result == [name, form[:31], str(tag), "3"], (row, result)
        observed.append(result)
    legacy = subprocess.check_output([executable], text=True).splitlines()
    assert legacy == [LEGACY_NAME, "", "0", "1"], legacy
    proof = {
        "all_checks_passed": True,
        "domain": DOMAIN,
        "limitations": LIMITATIONS,
        "native_constructor_cases": len(fixture["constructors"]),
        "native_destructor_cases": len(fixture["destructors"]),
        "portable_observations": observed,
        "legacy_observation": legacy,
        "artifact_sha256": {str(path): digest(path) for path in
                            (args.exe, args.object, args.fixtures, args.integration, Path(__file__))},
        "proposed_readiness": {"ready": [{
            **EXPECTED, "original_elf_sha256": EXPECTED["elf_sha256"],
            "cpp_compiled": True, "mangling_namespace_checked": True,
            "portable_ready": True, "domain": DOMAIN, "sources": SOURCES,
            "repository_sources": CORE,
        }], "pending": []},
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(proof, indent=2) + "\n")
    print(DOMAIN)

if __name__ == "__main__":
    main()
