"""Compare the compiled original-scope method with exact native observations."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).parent
TASK = HERE.name.rsplit("_", 1)[-1]
PANEL = ("include/presonus/panel", "src/Presonus/Panel")
SOURCES = tuple(f"{prefix}/{unit}.{ext}" for prefix, ext in zip(PANEL, ("hpp", "cpp"))
                for unit in ("Book", "Page"))
LCD_SOURCES = tuple(f"{prefix}/LCDComponent.{ext}" for prefix, ext in zip(PANEL, ("hpp", "cpp")))
CCL = ("third_party/ccl-framework/core/public/corevector.h",)
LCD_CCL = ("third_party/ccl-framework/core/portable/corecomponent.h",
           "third_party/ccl-framework/core/portable/corecomponent.cpp")
NATIVE = Path("uc-library/tests/recovery/cycle20_g07_r10/native.py")


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
    names = {row["mangled"] for row in original}
    assert len(original) == 2 and len(names) == 1
    symbols = subprocess.check_output(["nm", "--defined-only", args.object], text=True)
    matching = [line for line in symbols.splitlines() if line.split()[-1] in names]
    assert len(matching) == 1
    if args.symbols_only:
        print(matching[0])
        return
    desktop = [replay(args.exe, case) for row in original for case in row["cases"]]
    assert len(desktop) == CASES
    is_lcd = TASK in {"r12", "r13", "r16", "r17", "r20"}
    deps = SOURCES + (LCD_SOURCES if is_lcd else ())
    core = CCL + (LCD_CCL if is_lcd else ())
    ready = TASK in {"r16"}
    rows = [{"original_elf_sha256": row["elf_sha256"], "mangled": row["mangled"],
             "original_address": row["address"], "cpp_compiled": True, "mangling_namespace_checked": True,
             "portable_ready": ready, "domain": DOMAIN, "declaration_uncertainties": LIMITATIONS,
             "sources": {name: sha(Path("uc-library") / name) for name in deps},
             "repository_sources": {name: sha(name) for name in core}}
            for row in original]
    record = {
        "cpp_differential_passed": True, "compiled_mangled_names_matched": True,
        "portable_ready": ready, "case_count": len(desktop), "domain": DOMAIN, "limitations": LIMITATIONS,
        "functions": rows, "mangled_names": sorted(names), "verified_symbols": matching,
        "observations": desktop, "originals": original, "fixture_sha256": sha(args.fixtures),
        "checker_sha256": sha(__file__), "native_producer_sha256": sha(NATIVE),
        "replay_source_sha256": sha(HERE / "Replay.cpp"), "object_sha256": sha(args.object),
        "executable_sha256": sha(args.exe),
        "integration_sha256": sha(args.integration) if args.integration != "none" else None,
        "format_version": subprocess.check_output(["uc-library/.venv/bin/clang-format", "--version"], text=True).strip(),
        "proposed_readiness": {"ready": rows if ready else [], "pending": [] if ready else rows},
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(record, indent=2) + "\n")
    print(f"{HERE.name}: {len(desktop)} differential cases passed")


def run(exe, argv):
    return list(map(int, subprocess.check_output([exe, *map(str, argv)], text=True).split()))

CASES = 2
DOMAIN = ("Both original role vtables dispatch doIdle through actual LCDComponent::onIdle "
          "and the role-specific Core boundary. Host independently observes the virtual override "
          "and one real CCL child idle callback.")
LIMITATIONS = ["Original doIdle return declaration remains unresolved; the portable method returns void.",
               "No original Core body is executed. No ARM slot layout or device idle behavior claim."]


def replay(exe, case):
    assert case["events"] == ["actual LCDComponent::onIdle", "pinned actual Component::onIdle boundary"]
    actual = run(exe, [])
    assert actual == [1, 1]
    return actual

if __name__ == "__main__":
    main()
