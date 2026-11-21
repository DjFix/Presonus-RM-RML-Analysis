"""Compare the compiled adapter with the independent native observation."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

TASK = Path(__file__).parent.name
FIXTURE = Path(__file__).with_name("fixtures.json")
SOURCES = ["uc-library/include/presonus/MeterScaleControl.hpp",
           "uc-library/src/Presonus/MeterScaleControl.cpp"]
DOMAIN = ("Seven offline meter scale cases compare native and pinned CCL paint operations, "
          "labels, rectangles, lines and colors with/without fonts and a nonlinear scale.")
UNCERTAINTIES = ["Original virtual return spelling is unresolved; the pinned Control override uses void.",
                 "Native old CCL layout and hardware rendering remain unresolved."]


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
    if args.symbols_only:
        print(found[0])
        return
    cases = fixture["cases"]
    rows = (" ".join(map(str, c["input"])) for c in cases)
    result = subprocess.run([args.exe], input="\n".join(rows)+"\n", text=True,
                            capture_output=True, check=True)
    observed = [list(map(int, line.split())) for line in result.stdout.splitlines()]
    if observed != [c["observed"] for c in cases]:
        raise SystemExit("Original and portable draw commands differ")
    core = ["third_party/ccl-framework/core/portable/gui/" + file for file in ("corecontrols.h", "corecontrols.cpp", "coregraphics.h", "coregraphics.cpp", "coreview.h", "coreview.cpp", "coreviewshared.h", "corefont.h", "corefont.cpp")] + ["third_party/ccl-framework/core/public/" + file for file in ("coreinterpolator.h", "coreinterpolator.cpp", "corestringbuffer.h", "corestringtraits.h")]
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
             "verified_symbol": found[0], "proposed_readiness": {"ready": [], "pending": [origin]}}
    if args.out.exists():
        previous = args.out.with_name(f"{args.out.stem}.previous-{sha(args.out)}.json")
        if not previous.exists():
            previous.write_bytes(args.out.read_bytes())
    args.out.write_text(json.dumps(proof, indent=2) + "\n")
    print(f"{TASK}: {len(cases)} differential cases passed")


if __name__ == "__main__":
    main()
