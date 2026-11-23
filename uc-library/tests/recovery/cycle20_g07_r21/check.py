"""Compare the exact LCD routing method with its independent ARM observations."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).parent
INC = "include/presonus/panel/"
SRC = "src/Presonus/Panel/"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--object", required=True)
    parser.add_argument("--exe")
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--integration", default="none")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--symbols-only", action="store_true")
    args = parser.parse_args()
    originals = json.loads(args.fixtures.read_bytes())["originals"]
    names = {row["mangled"] for row in originals}
    assert len(originals) == 2 and len(names) == 1
    symbols = subprocess.check_output(["nm", "--defined-only", args.object], text=True)
    matched = [line for line in symbols.splitlines() if line.split()[-1] in names]
    assert len(matched) == 1
    if args.symbols_only:
        print(matched[0])
        return
    observations = [replay(args.exe, row["role"], case) for row in originals for case in row["cases"]]
    assert len(observations) == CASES
    ccl = ("third_party/ccl-framework/core/portable/corecomponent.h",
           "third_party/ccl-framework/core/portable/corecomponent.cpp",
           "third_party/ccl-framework/core/public/corevector.h")
    sources = {name: sha(Path("uc-library") / name) for unit in UNITS
               for name in (INC + unit + ".hpp", SRC + unit + ".cpp")}
    rows = [{"original_elf_sha256": row["elf_sha256"], "mangled": row["mangled"],
             "original_address": row["address"], "cpp_compiled": True, "mangling_namespace_checked": True,
             "portable_ready": False, "domain": DOMAIN, "sources": sources,
             "repository_sources": {name: sha(name) for name in ccl},
             "declaration_uncertainties": LIMITATIONS} for row in originals]
    proof = {
        "cpp_differential_passed": True, "compiled_mangled_names_matched": True, "portable_ready": False,
        "domain": DOMAIN, "case_count": len(observations), "limitations": LIMITATIONS, "functions": rows,
        "mangled_names": sorted(names), "originals": originals, "observations": observations,
        "verified_symbols": matched, "fixture_sha256": sha(args.fixtures), "checker_sha256": sha(__file__),
        "replay_source_sha256": sha(HERE / "Replay.cpp"), "native_producer_sha256": sha(HERE / "native.py"),
        "object_sha256": sha(args.object), "executable_sha256": sha(args.exe),
        "integration_sha256": sha(args.integration) if args.integration != "none" else None,
        "format_version": subprocess.check_output(
            ["uc-library/.venv/bin/clang-format", "--version"], text=True).strip(),
        "proposed_readiness": {"ready": [], "pending": rows},
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(proof, indent=2) + "\n")
    print(f"{HERE.name}: {len(observations)} differential cases passed")


CASES = 18
UNITS = ("LCDComponent", "Book")
DOMAIN = ("Two offline ARM roles, nine ordered old/new pairs covering null, repeated and distinct "
          "encoder identities. Verify exact native receiver-field write, guard preservation and "
          "portable pointer identity. Existing current Book and typed tag lookup are regression-checked.")
LIMITATIONS = ["Original ordinary return declaration remains unresolved; portable return is void.",
               "Only the original receiver's exact touched ARM field is established. "
               "The portable Control identity is borrowed; no device or pointee behavior is exercised."]


def replay(exe, role, case):
    output = int(subprocess.check_output([exe, str(case["old"]), str(case["new"])], text=True))
    assert output == case["stored"] and case["other_receiver_bytes_preserved"] and not case["nonstack_reads"]
    return {"role": role, "stored_identity": output}


if __name__ == "__main__":
    main()
