"""Compare compiled Book behavior against exact native fixtures."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).parent
SOURCE_PATHS = tuple(f"{prefix}/{name}.{ext}" for prefix, ext in (
    ("include/presonus/panel", "hpp"), ("src/Presonus/Panel", "cpp"))
    for name in ("Book", "Page", "Element"))
CCL = "third_party/ccl-framework/core/public/corevector.h"
CCL_SHA = "49634ef286112cfa48357391a3cdddbee86e76cfe5e820b6b74c6ec913aeed32"


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
    original = fixture["originals"]
    names = sorted({row["mangled"] for row in original})
    assert len(original) == len(names) * 2 == ORIGINAL_COUNT
    table = subprocess.check_output(["nm", "--defined-only", args.object], text=True)
    matching = [line for line in table.splitlines() if line.split()[-1] in names]
    assert sorted(line.split()[-1] for line in matching) == names, matching
    if args.symbols_only:
        print("\n".join(matching))
        return
    traces = [row["role"] + ": " + replay(args.exe, row, case)
              for row in original for case in row["cases"]]
    assert len(traces) == CASE_COUNT
    assert sha(CCL) == CCL_SHA
    sources = {path: sha(Path("uc-library") / path) for path in SOURCE_PATHS}
    rows = [{"original_elf_sha256": row["elf_sha256"], "mangled": row["mangled"],
             "original_address": row["address"], "cpp_compiled": True, "mangling_namespace_checked": True,
             "portable_ready": READY, "domain": DOMAIN, "sources": sources,
             "repository_sources": {CCL: CCL_SHA}, "declaration_uncertainties": LIMITATIONS}
            for row in original]
    proof = {
        "cpp_differential_passed": True, "compiled_mangled_names_matched": True,
        "portable_ready": READY, "case_count": len(traces), "domain": DOMAIN,
        "limitations": LIMITATIONS, "functions": rows, "mangled_names": names,
        "verified_symbols": matching, "observations": traces, "originals": original,
        "fixture_sha256": sha(args.fixtures), "checker_sha256": sha(__file__),
        "native_producer_sha256": sha(HERE / "native.py"), "replay_source_sha256": sha(HERE / "Replay.cpp"),
        "object_sha256": sha(args.object), "executable_sha256": sha(args.exe),
        "integration_sha256": sha(args.integration) if args.integration != "none" else None,
        "format_version": subprocess.check_output(["uc-library/.venv/bin/clang-format", "--version"], text=True).strip(),
        "proposed_readiness": {"ready": rows if READY else [], "pending": [] if READY else rows},
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(proof, indent=2) + "\n")
    print(f"{HERE.name}: {len(traces)} differential cases passed")


ORIGINAL_COUNT = 2
CASE_COUNT = 16
READY = False
DOMAIN = ("Eight cases per role with zero, one, 31 or 32 prior slots and null or non-null appends. "
          "Check existing slots, exact appended identity and count preservation at capacity.")
LIMITATIONS = ["Original ordinary return declaration unresolved; portable return is void.",
               "Raw registration is portable borrowing. Explicit typed ownership transfer is independent.",
               "Original ARM layout and hardware are outside scope."]


def replay(exe, row, case):
    count = case["count"]
    supplied = str(int(case["pointer_word"] != 0))
    actual = int(subprocess.check_output([exe, str(count), supplied], text=True))
    assert actual == count + case["inserted"]
    return f"count {count}, nonnull {supplied} => {actual}"


if __name__ == "__main__":
    main()
