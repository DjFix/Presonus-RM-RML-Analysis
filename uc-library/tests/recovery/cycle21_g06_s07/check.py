"""Compare the compiled adapter with the independent native observation."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

TASK = Path(__file__).parent.name
FIXTURE = Path(__file__).with_name("fixtures.json")
SOURCES = ["uc-library/include/presonus/DefaultMeterInterpolator.hpp",
           "uc-library/src/DefaultMeterInterpolator.cpp"]
DOMAIN = ("Deleting variant dispatch through original and portable vtables with "
          "one allocation per side and one observed receiver deallocation.")
UNCERTAINTIES = ["The native constructor and meter breakpoints are out of scope.",
                 "Original ARM object layout and allocator internals remain unresolved."]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe")
    parser.add_argument("--object", required=True)
    parser.add_argument("--integration")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--symbols-only", action="store_true")
    args = parser.parse_args()
    fixture = json.loads(FIXTURE.read_text())
    original = fixture["target"]
    symbols = subprocess.check_output(["nm", "--defined-only", args.object], text=True)
    found = [line for line in symbols.splitlines() if line.split()[-1] == original["mangled"]]
    if len(found) != 1:
        raise SystemExit(f"Missing or duplicate emitted original symbol: {found}")
    deletion = subprocess.check_output(
        ["objdump", "-dr", "--disassemble="+original["mangled"], args.object], text=True)
    if "_ZdlPv-" not in deletion or "_ZdlPvm" in deletion:
        raise SystemExit("Deleting destructor does not relocate to unsized operator delete")
    if args.symbols_only:
        print(found[0])
        return
    cases = fixture["cases"]
    result = subprocess.run([args.exe],  text=True,
                            capture_output=True, check=True)
    observed = [list(map(int, line.split())) for line in result.stdout.splitlines()]
    if observed != [c["observed"] for c in cases]:
        raise SystemExit("Original and portable deallocation observations differ")
    core = ["third_party/ccl-framework/core/public/" + file for file in ("coreinterpolator.h", "coreinterpolator.cpp")]
    origin = {"original_elf_sha256": original["original_elf_sha256"], "mangled": original["mangled"],
              "cpp_compiled": True, "mangling_namespace_checked": True, "portable_ready": False,
              "domain": DOMAIN, "repository_sources": {path: sha(path) for path in core}, "declaration_uncertainties": UNCERTAINTIES,
              "sources": {source.removeprefix("uc-library/"): sha(source) for source in SOURCES}}
    proof = {"differential_passed": True, "domain": DOMAIN, "case_count": len(cases),
             "observations": observed, "original": fixture | {"cases": len(cases)},
             "fixture_sha256": sha(FIXTURE), "checker_sha256": sha(__file__),
             "native_producer_sha256": sha(FIXTURE.with_name("native.py")),
             "replay_source_sha256": sha(FIXTURE.with_name("Replay.cpp")),
             "format_version": subprocess.check_output(
                 ["uc-library/.venv/bin/clang-format", "--version"], text=True).strip(),
             "object_sha256": sha(args.object), "executable_sha256": sha(args.exe),
             "integration_sha256": sha(args.integration) if args.integration != "none" else None,
             "verified_symbol": found[0], "deleting_variant_relocations": deletion, "proposed_readiness": {"ready": [], "pending": [origin]}}
    if args.out.exists():
        previous = args.out.with_name(f"{args.out.stem}.previous-{sha(args.out)}.json")
        if not previous.exists():
            previous.write_bytes(args.out.read_bytes())
    args.out.write_text(json.dumps(proof, indent=2) + "\n")
    print(f"{TASK}: {len(cases)} differential cases passed")


if __name__ == "__main__":
    main()
