"""Compare scoped Page calls against verified original no-effect observations."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).parent
DOMAIN = 'Exact ARM entry with two mapped, zero, and unmapped receiver registers, varied argument registers, sentinel memory and preserved frame state. Static original Page table word checked independently. Host calls use constructed Pages with active or unselected recording Elements and compare receiver and Element state plus callback count.'
LIMITATIONS = ['Portable callback declaration uses a virtual void member. Original unencoded return and exact C++ declaration remain unresolved.', 'Native table word observations and portable differential do not establish original layout, ARM ABI or hardware behavior.']
SOURCE_PATHS = ('include/presonus/panel/Page.hpp', 'src/Presonus/Panel/Page.cpp', 'include/presonus/panel/Element.hpp', 'src/Presonus/Panel/Element.cpp', 'include/presonus/panel/TextEntryElement.hpp')
MODE = 'ordinary'

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
    originals = json.loads(args.fixtures.read_text())
    symbols = subprocess.check_output(["nm", "--defined-only", args.object], text=True)
    matches = []
    for symbol in sorted({row["mangled"] for row in originals}):
        line, = [line for line in symbols.splitlines() if line.split()[-2:] == ["T", symbol]]
        matches.append(line)
    if args.symbols_only:
        print("\n".join(matches))
        return

    sources = {name: sha(Path("uc-library") / name) for name in SOURCE_PATHS}
    rows, traces = [], []
    ready = MODE == "destructor"
    for original in originals:
        for case in original["cases"]:
            actual = subprocess.check_output([args.exe, str(case["seed"])], text=True)
            observed = list(map(int, actual.split()))
            assert observed == case["contract"], (case["seed"], observed, case["contract"])
            traces.append({"elf_sha256": original["elf_sha256"], "seed": case["seed"], "portable_observation": observed})
        rows.append({
            "original_elf_sha256": original["elf_sha256"], "mangled": original["mangled"],
            "original_address": original["address"], "cpp_compiled": True,
            "mangling_namespace_checked": True, "portable_ready": ready, "domain": DOMAIN,
            "declaration_uncertainties": [] if ready else LIMITATIONS, "sources": sources,
            "repository_sources": {},
        })
    version = subprocess.check_output(["uc-library/.venv/bin/clang-format", "--version"], text=True)
    proof = {
        "cpp_differential_passed": True, "compiled_mangled_names_matched": True,
        "portable_ready": ready, "case_count": len(traces), "domain": DOMAIN,
        "limitations": LIMITATIONS, "functions": rows, "mangled_names": sorted({r["mangled"] for r in rows}),
        "verified_symbols": matches, "observations": traces, "originals": originals,
        "fixture_sha256": sha(args.fixtures), "checker_sha256": sha(__file__),
        "native_producer_sha256": sha(HERE / "native.py"), "replay_source_sha256": sha(HERE / "Replay.cpp"),
        "object_sha256": sha(args.object), "executable_sha256": sha(args.exe),
        "integration_sha256": sha(args.integration) if args.integration != "none" else None,
        "format_version": version.strip(),
        "proposed_readiness": {"ready": rows if ready else [], "pending": [] if ready else rows},
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(proof, indent=2) + "\n")
    print(f"{len(traces)} portable executions matched independent original observations")


if __name__ == "__main__":
    main()
