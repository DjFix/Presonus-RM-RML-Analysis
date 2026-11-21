"""Fresh exact RM ARM and pinned-provider differential for linkAsMaster."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from native import ADDRESS, ELF_SHA, MANGLED, SIZE, observe

ROOT = Path(__file__).resolve().parents[4]
SOURCES = ("include/presonus/LinkableComponent.hpp", "src/Presonus/LinkableComponent.cpp")
PROVIDERS = (
    "third_party/ccl-framework/core/portable/corecomponent.cpp",
    "third_party/ccl-framework/core/portable/corecomponent.h",
    "third_party/ccl-framework/core/portable/coreparams.cpp",
    "third_party/ccl-framework/core/portable/coreparams.h",
    "third_party/ccl-framework/core/portable/coreparaminfo.h",
    "third_party/ccl-framework/core/portable/coreattributes.h",
    "third_party/ccl-framework/core/portable/coreattributes.cpp",
    "third_party/ccl-framework/core/system/corethread.h",
    "third_party/ccl-framework/core/platform/shared/posix/corethread.posix.cpp",
)
DOMAIN = ("RM stable acyclic borrowed child graphs through three levels, exact "
          "ARM partner and slave writes, enabled/disabled and already-linked "
          "branches, matching and absent/failed child queries, linkable tags "
          "with present or missing destination, CCL edit notifications and "
          "alternate attribute replacement under the shared recursive lock.")
BOUNDARY = ("Original virtual castTo and findChild slots verified. Child "
            "selection compares genuine pinned CCL names on the existing "
            "borrowed Linkable collection. ARM enters and leaves the exact "
            "recursive body. Independent real syncParams and copyToAltMemory "
            "run as a separate provider probe under the actual recursive lock.")
LIMIT = ("Original complete declaration, storage/layout, ARM ABI, exceptional "
         "ARM unwind, reentrant mutation, cycles, concurrent updates and "
         "hardware behavior are outside the verified domain.")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("exe", "object", "fixtures", "integration", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    a = parser.parse_args()
    symbols = subprocess.check_output(["nm", "--defined-only", str(a.object)], text=True)
    matches = [line for line in symbols.splitlines() if line.split()[-1:] == [MANGLED]]
    assert len(matches) == 1, matches
    fixtures = json.loads(a.fixtures.read_text())
    assert observe(a.exe) == fixtures
    for case in fixtures["cases"]:
        output = subprocess.check_output(
            [str(a.exe.resolve()), "target", str(case["scenario"])], text=True)
        queries, state = output.split("|")
        assert list(map(int, queries.split())) == case["queries"], case
        assert list(map(int, state.split())) == case["expected"], (case, output)
    integration = json.loads(a.integration.read_text())
    assert isinstance(integration, dict) and integration
    row = {"original_elf_sha256": ELF_SHA, "firmware": "RM/RML mixer 13731",
           "mangled": MANGLED, "address": ADDRESS, "size": SIZE, "section": 12,
           "role": "server", "domain": DOMAIN, "cpp_compiled": True,
           "mangling_namespace_checked": True, "portable_ready": False,
           "sources": {path: sha(ROOT / "uc-library" / path) for path in SOURCES},
           "repository_sources": {path: sha(ROOT / path) for path in PROVIDERS},
           "declaration_uncertainties": [LIMIT]}
    receipt = {"behavior_passed": True, "domain": DOMAIN, "boundary_evidence": BOUNDARY,
               "limitations": [LIMIT], "case_count": len(fixtures["cases"]), "native": fixtures,
               "compiled_symbols": matches, "proposed_readiness": {"ready": [], "pending": [row]},
               "fixture_sha256": sha(a.fixtures), "integration_sha256": sha(a.integration),
               "object_sha256": sha(a.object), "executable_sha256": sha(a.exe),
               "producer_sha256": sha(__file__), "oracle_sha256": sha(Path(__file__).with_name("native.py"))}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"behavior_passed": True, "cases": len(fixtures["cases"])}))


if __name__ == "__main__":
    main()
