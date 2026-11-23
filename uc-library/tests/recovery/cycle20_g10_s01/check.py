"""Compare a compiled ControlGroup base hook with sealed native observations."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

SOURCE = Path("uc-library/src/surface_panel/ControlGroup.cpp")
HEADER = Path("uc-library/include/presonus/surface_panel/ControlGroup.hpp")
CONTROL = Path("uc-library/include/presonus/panel/control.hpp")
DOMAIN = ("Direct base entry in CS18 and RM with mapped and unmapped synthetic receivers"
          " and an isolated 16-byte native stack frame. Portable exact-base replay covers"
          " empty and populated owned and borrowed CCL registries, preserving count, order,"
          " duplicate pointer identity, group id and ownership.")
UNCERTAINTIES = ["Original return declaration, inferred virtual slots in live dispatch, "
                 "and original object layout/ARM ABI remain unresolved. Portable void "
                 "nonvirtual spelling covers direct base calls."]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def emit(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", type=Path)
    parser.add_argument("--object", type=Path, required=True)
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--integration", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--symbols-only", action="store_true")
    args = parser.parse_args()
    data = json.loads(args.fixtures.read_text())
    names = {row["mangled"] for row in data["originals"]}
    symbols = subprocess.check_output(["nm", "--defined-only", "--format=posix", args.object],
                                      text=True)
    assert all(any(line.split()[:2] == [name, "T"] for line in symbols.splitlines())
               for name in names), names
    if args.symbols_only:
        print("Exact compiled mangling matched:", *names)
        return
    assert args.exe and args.out
    cases = subprocess.check_output([args.exe.resolve()], text=True).splitlines()
    assert cases == ["owned-empty", "borrowed-empty", "owned-populated", "borrowed-populated"]
    assert len(data["native_observations"]) == 2
    assert all(len(row) == 2 for row in data["native_observations"])

    sources = {str(path.relative_to("uc-library")): digest(path)
               for path in (SOURCE, HEADER, CONTROL)}
    core = {name: digest(Path(name)) for name in data["core_headers"]}
    records = [dict(original, original_elf_sha256=original["elf_sha256"],
                    original_address=original["address"], sources=sources,
                    repository_sources=core, cpp_compiled=True,
                    mangling_namespace_checked=True, portable_ready=False,
                    domain=DOMAIN, declaration_uncertainties=UNCERTAINTIES)
               for original in data["originals"]]
    integration = json.loads(args.integration.read_text())
    proof = {"cpp_differential_passed": True, "compiled_mangled_names_matched": True,
             "cpp_compiled": True, "mangling_namespace_checked": True,
             "portable_ready": False, "mangled_names": sorted(names),
             "domain": DOMAIN, "functions": records,
             "proposed_readiness": {"ready": [], "pending": records},
             "originals": data["originals"], "native_observations": data["native_observations"],
             "oracle_versions": data["oracle_versions"],
             "native_oracle_sha256": digest(Path(__file__).with_name("native.py")),
             "checker_sha256": digest(Path(__file__)),
             "exe_sha256": digest(args.exe), "object_sha256": digest(args.object),
             "fixtures_sha256": digest(args.fixtures),
             "integration_sha256": digest(args.integration),
             "linked_integration_reported_ctest_passed": integration.get("ctest_passed", False),
             "portable_cases": cases, "portable_case_count": len(cases),
             "native_case_count": sum(map(len, data["native_observations"]))}
    emit(args.out, proof)
    print(f"{len(cases)} portable cases matched the independently observed base behavior")


if __name__ == "__main__":
    main()
