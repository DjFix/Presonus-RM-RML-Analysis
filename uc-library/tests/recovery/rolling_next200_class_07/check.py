"""Check the portable executable and exact production-object definition."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from native import ELF_SHA, MANGLED, require

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SOURCES = (
    "include/presonus/panel/SharedMemoryComm.hpp",
    "src/Presonus/Panel/SharedMemoryComm.cpp",
)
DOMAIN = ("Two independently observed ARM receiver and stack sentinel states, "
          "compared with the portable method on two live empty receivers. "
          "Receiver bytes remain unchanged and native writes stay in the 16-byte stack frame.")
UNCERTAINTIES = [
    "The original return declaration remains unresolved. Preserved r0 is not return-type evidence.",
    "The ELF table slot does not establish the original virtual declaration or dispatch contract."
]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def symbols(obj):
    argv = ["nm", "--defined-only", str(obj)]
    listing = subprocess.check_output(argv, text=True)
    matches = [line for line in listing.splitlines()
               if line.split()[-1:] == [MANGLED] and line.split()[-2:-1] == ["T"]]
    require(len(matches) == 1, "Missing unique original compiled mangled name")
    return {"argv": argv, "sha256": digest(obj), "symbol": matches[0]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", type=Path)
    parser.add_argument("--object", required=True, type=Path)
    parser.add_argument("--fixture", type=Path, default=HERE / "fixtures.json")
    parser.add_argument("--fixture-sha256")
    parser.add_argument("--integration", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    symbol = symbols(args.object)
    if args.exe is None:
        print(json.dumps(symbol))
        return

    fixture_hash = digest(args.fixture)
    require(fixture_hash == args.fixture_sha256, "Fixture hash mismatch")
    fixtures = json.loads(args.fixture.read_text())
    require((fixtures["elf_sha256"], fixtures["mangled"]) == (ELF_SHA, MANGLED),
            "Fixture original identity mismatch")
    require(len(fixtures["cases"]) == 2, "Expected two independent native cases")
    expected = "".join(f"{case['fill']} {int(case['receiver_unchanged'])}\n"
                       for case in fixtures["cases"])
    observed = subprocess.check_output([str(args.exe.resolve())], text=True)
    require(observed == expected, "Portable observations differ from the native fixtures")
    sources = {path: digest(ROOT / "uc-library" / path) for path in SOURCES}
    row = {"original_elf_sha256": ELF_SHA, "mangled": MANGLED,
           "original_address": fixtures["address"], "original_size": fixtures["size"],
           "domain": DOMAIN, "sources": sources, "repository_sources": {},
           "cpp_compiled": True, "mangling_namespace_checked": True,
           "portable_ready": False, "original_function_verified": False,
           "hardware_verified": False, "declaration_uncertainties": UNCERTAINTIES}
    integration_sha = None
    if args.integration is not None and str(args.integration) != "-":
        integration_sha = digest(args.integration)
        require(json.loads(args.integration.read_text())["ctest_passed"] is True,
                "Integration receipt did not pass CTest")
    proof = {"original_elf_sha256": ELF_SHA, "mangled_names": [MANGLED],
             "functions": [row], "domain": DOMAIN, "sources": sources,
             "cpp_differential_passed": True, "compiled_mangled_names_matched": True,
             "cpp_compiled": True, "mangling_namespace_checked": True,
             "portable_ready": False, "integration_sha256": integration_sha,
             "native_observations": fixtures, "portable_cases": len(fixtures["cases"]),
             "portable_stdout": observed, "compiled_object": symbol,
             "executable_sha256": digest(args.exe), "fixture_sha256": fixture_hash,
             "checker_sha256": digest(Path(__file__)),
             "native_producer_sha256": digest(HERE / "native.py"),
             "replay_source_sha256": digest(HERE / "Replay.cpp"),
             "formatter_version": subprocess.check_output(
                 [str(ROOT / "uc-library/.venv/bin/clang-format"), "--version"],
                 text=True).strip(),
             "proposed_readiness": {"ready": [], "pending": [row]}}
    if args.out is not None and str(args.out) != "-":
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(proof, indent=2) + "\n")
    print(json.dumps({"cpp_differential_passed": True,
                      "domain": DOMAIN, "cases": len(fixtures["cases"])}))


if __name__ == "__main__":
    main()
