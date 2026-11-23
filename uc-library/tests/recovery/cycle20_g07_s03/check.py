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


ORIGINAL_COUNT = 6
CASE_COUNT = 24
READY = True
DOMAIN = ("Four layouts per ELF/variant covering empty, null-only, single Page, and mixed nested "
          "Page/Element slots. Observe forward virtual child teardown and unsized Book D0 deletion. "
          "D1/D2 retain receiver storage; legacy borrowed inspection still reads its separate records.")
LIMITATIONS = ["The native allocator shim physically unmaps receivers and verifies post-return reads.",
               "Original ARM layout, constructors, unknown derived children, and hardware are outside scope."]


def replay(exe, row, case):
    layout = ["-" if slots is None else "".join("0" if child is None else "1" for child in slots)
              for slots in case["layout"]]
    expected = []
    for name in case["deallocation_order"]:
        parts = name.split(".")
        if len(parts) == 1:
            expected.append(90)
        elif len(parts) == 2:
            expected.append(100 + int(parts[1]))
        else:
            expected.append(200 + 10 * int(parts[1]) + int(parts[2]))
    disposed = case["disposal_unreadable_after_return"]
    assert len(disposed) == len(expected)
    assert (0x40000000 in disposed) == (row["variant"] == 0)
    actual = subprocess.check_output([exe, str(row["variant"]), *layout], text=True).strip()
    assert list(map(int, actual.split())) == expected
    return f'D{row["variant"]} {layout!r} => {actual}'


if __name__ == "__main__":
    main()
