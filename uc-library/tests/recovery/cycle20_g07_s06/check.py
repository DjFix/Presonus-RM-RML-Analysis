"""Compare the compiled Page/Book operation against exact ARM observations."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).parent
SOURCE_PATHS = (
    "include/presonus/panel/Page.hpp", "src/Presonus/Panel/Page.cpp",
    "include/presonus/panel/Element.hpp", "src/Presonus/Panel/Element.cpp",
    "include/presonus/panel/TextEntryElement.hpp", "src/Presonus/Panel/TextEntryElement.cpp",
)
BOOK_PATHS = ("include/presonus/panel/Book.hpp", "src/Presonus/Panel/Book.cpp")
CORE_PATHS = ("third_party/ccl-framework/core/portable/coreparams.h",
              "third_party/ccl-framework/core/public/corevector.h")


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
    fixture = json.loads(args.fixtures.read_bytes())
    originals = fixture["originals"]
    names = {row["mangled"] for row in originals}
    assert len(originals) == 2 and len(names) == 1
    symbols = subprocess.check_output(["nm", "--defined-only", args.object], text=True)
    matching = [line for line in symbols.splitlines() if line.split()[-1] in names]
    assert len(matching) == 1
    if args.symbols_only:
        print(matching[0])
        return
    traces = [replay(args.exe, case) for row in originals for case in row["cases"]]
    assert len(traces) == COUNT
    paths = SOURCE_PATHS + (BOOK_PATHS if INCLUDE_BOOK else ())
    rows = [{"original_elf_sha256": row["elf_sha256"], "mangled": row["mangled"],
             "original_address": row["address"], "cpp_compiled": True, "mangling_namespace_checked": True,
             "portable_ready": False, "domain": DOMAIN,
             "sources": {path: sha(Path("uc-library") / path) for path in paths},
             "repository_sources": {path: sha(path) for path in CORE_PATHS},
             "declaration_uncertainties": LIMITATIONS} for row in originals]
    proof = {
        "cpp_differential_passed": True, "compiled_mangled_names_matched": True,
        "portable_ready": False, "case_count": len(traces), "domain": DOMAIN,
        "limitations": LIMITATIONS, "functions": rows, "mangled_names": sorted(names),
        "verified_symbols": matching, "observations": traces, "originals": originals,
        "fixture_sha256": sha(args.fixtures), "checker_sha256": sha(__file__),
        "native_producer_sha256": sha(HERE / "native.py"), "replay_source_sha256": sha(HERE / "Replay.cpp"),
        "object_sha256": sha(args.object), "executable_sha256": sha(args.exe),
        "integration_sha256": sha(args.integration) if args.integration != "none" else None,
        "format_version": subprocess.check_output(["uc-library/.venv/bin/clang-format", "--version"], text=True).strip(),
        "proposed_readiness": {"ready": [], "pending": rows},
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(proof, indent=2) + "\n")
    print(f"{HERE.name}: {len(traces)} differential cases passed")

COUNT = 14
INCLUDE_BOOK = False
DOMAIN = ("Seven cases per role with null and live Element selections. Observe virtual old-off "
          "before replacement, new-on after replacement, same-pointer bypass and real Element "
          "activation and dirty state.")
LIMITATIONS = ["Original ordinary return declaration remains unresolved; portable return is void.",
               "The host uses a recording override that delegates to actual Element::activate; "
               "unknown original subclasses and ARM object layout remain outside scope."]


def replay(exe, case):
    actual = subprocess.check_output([exe, *map(str, case["input"])], text=True)
    observed = list(map(int, actual.split()))
    trace = case["ordered_element_activation_with_observed_page_state"]
    expected = [item for event in trace for item in event] + [case["final_active"]] + [
        item for state in case["element_after"] for item in state]
    assert observed == expected, (case, observed)
    return observed


if __name__ == "__main__":
    main()
