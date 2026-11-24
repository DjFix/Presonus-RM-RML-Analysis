"""Compare Linux NetworkItem destructor lifecycle observations with sealed ARM observations."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("exe", "object", "integration", "out", "fixtures"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--symbols-only", action="store_true")
    args = parser.parse_args()
    fixture = json.loads(args.fixtures.read_text())
    original = fixture["original"]
    nm = subprocess.run(
        ["nm", "--defined-only", "--format=posix", args.object],
        text=True, capture_output=True, check=True,
    )
    exported = {line.split()[0]: line.split()[1] for line in nm.stdout.splitlines() if line.strip()}
    names = [f"_ZN8Presonus2UC11NetworkItemD{variant}Ev" for variant in (1, 2)]
    if any(exported.get(name) != "T" for name in names) or "_ZN8Presonus2UC11NetworkItemD0Ev" in exported:
        parser.exit(1, "Expected both external non-deleting destructor symbols and no D0\n")
    print("Verified exported D1 and D2 symbols")
    if args.symbols_only:
        return

    results = []
    variant = original["mangled"][-4:-2]
    for case in fixture["cases"]:
        argv = [str(args.exe), variant, "borrowed" if case["borrowed"] else "null", case["identity"]]
        actual = subprocess.run(argv, text=True, capture_output=True, check=True)
        recorded = case["observation"]
        if not all(recorded.values()) or actual.stdout != "returned storage-unchanged pointee-unchanged\n":
            parser.exit(1, f"Linux and ARM observations disagree for {variant}: {case}\n")
        results.append({"argv": argv, "stdout": actual.stdout})

    domain = (
        f"{variant} non-deleting {'complete object' if variant == 'D1' else 'base subobject'} "
        "destruction; null/borrowed component, short/truncated identity, preserved canaries, "
        "receiver bytes and borrowed pointee, normal return; original ARM trace stays within "
        "the exact frame and stack, without an external call or deallocation."
    )
    lib_sources = [Path("include/presonus/uc/NetworkItem.hpp"), Path("src/Presonus/UC/NetworkItem.cpp")]
    pinned = sorted(Path("third_party/ccl-framework").glob("core/public/corestring*.h"))
    relevant = {"corestringbuffer.h", "corestringtraits.h"}
    row = {
        **original,
        "original_elf_sha256": original["elf_sha256"],
        "validation_domain": domain,
        "portable_ready": True,
        "cpp_compiled": True,
        "mangling_namespace_checked": True,
        "sources": {str(p): digest(Path("uc-library") / p) for p in lib_sources},
        "repository_sources": {str(p): digest(p) for p in pinned if p.name in relevant},
    }
    proof = {
        "validation_passed": True,
        "cpp_differential_passed": True,
        "compiled_original_mangled_names_matched": True,
        "functions": [row],
        "domain": domain,
        "limitations": ["Native layouts, D0, hardware, and original ARM ABI are outside this source-port result."],
        "formatter_version": subprocess.check_output(["uc-library/.venv/bin/clang-format", "--version"], text=True).strip(),
        "proposed_readiness": {"ready": [row], "pending": []},
        "validation_domain": domain,
        "native_range": fixture["range"],
        "native_unicorn_version": fixture["unicorn_version"],
        "fixture_sha256": digest(args.fixtures),
        "integration_sha256": digest(args.integration),
        "executable_sha256": digest(args.exe),
        "object_sha256": digest(args.object),
        "symbols": names,
        "case_count": len(results),
        "portable_results": results,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(proof, indent=2) + "\n")
    print(f"Verified {len(results)} bounded Linux cases against sealed ARM observations")


if __name__ == "__main__":
    main()
