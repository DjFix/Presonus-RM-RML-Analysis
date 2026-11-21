"""Replay the compiled FX source port against independent native observations."""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import subprocess

TASK = Path(__file__).parent.name
LABEL = TASK.endswith("s01")
FIXTURE = Path(__file__).with_name("fixtures.json")
SOURCES = ["include/presonus/mixer/FXComponent.hpp", "src/Presonus/Mixer/FXComponent.cpp",
           "include/presonus/mixer/DelayComponent.hpp"]
CORE = ["portable/corecomponent.h", "portable/corecomponent.cpp",
        "portable/coreparams.h", "portable/coreparams.cpp", "portable/coreparaminfo.h"]
CORE += (["public/corestringtraits.h", "public/corestringbuffer.h"]
         if LABEL else ["public/coreinterpolator.h", "public/coreinterpolator.cpp",
                        "public/corevector.h", "portable/coretypeinfo.h"])
DOMAIN = ("Seven offline RM 13731 cases comparing native ordered type reads, edited display write, "
          "and recall prompt final text against pinned CCL lookup, numeric and string parameters."
          if LABEL else
          "Eighty-three offline RM 13731 cases: all 78 initialized range triples, numeric/other/null "
          "receiver, missing factory with preallocated/growing vector, growth allocation failure, "
          "normalized argument, order, ownership and resulting pinned CCL ranges.")
UNCERTAINTIES = ["Original unencoded return spelling and ARM receiver/parameter layout are unresolved."]
LIMITATIONS = (
    ["Native parameter lookup and virtual parameter methods use explicit controlled boundary fixtures.",
     "The displayed parameter is a borrowed portable binding; live hardware and controller notifications are excluded."]
    if LABEL else
    ["Original startup initializer and FX type identity query execute. Original RTTI, factory, vector resize, "
     "numeric/interpolator and lifetime methods are controlled boundaries; portable CCL performs actual operations.",
     "Out-of-range slot/type, hardware, and firmware provider binary ABI are outside the validation domain."])


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
    if not args.exe or not args.integration or not args.out:
        parser.error("--exe, --integration, and --out are required for replay")
    fresh = args.integration != "none"
    if fresh:
        integration = json.loads(Path(args.integration).read_text())
        if integration.get("platform") != "linux" or integration.get("ctest_passed") is not True:
            raise SystemExit("Expected a passing Linux canonical integration receipt")
    cases = fixture["cases"]
    rows = (" ".join(map(str, c["input"])) for c in cases)
    run = subprocess.run([args.exe], input="\n".join(rows)+"\n", text=True,
                         capture_output=True)
    if run.returncode:
        raise SystemExit(f"Replay exited {run.returncode}: {run.stderr}\n{run.stdout}")
    tokens = [shlex.split(line) for line in run.stdout.splitlines()]
    observed = [([*map(float, row[:-1]), row[-1]] if LABEL else list(map(int, row)))
                for row in tokens]
    expected = [case["observed"] for case in cases]
    if observed != expected:
        mismatches = [(case["input"], native, host) for case, native, host in zip(cases, expected, observed)
                      if native != host]
        raise SystemExit(f"FX observation mismatch, expected {len(expected)} cases, observed "
                         f"{len(observed)}: {mismatches[:5]}")
    proposal = {"original_elf_sha256": original["original_elf_sha256"], "mangled": original["mangled"],
                "cpp_compiled": True, "mangling_namespace_checked": True, "portable_ready": False,
                "differential_passed": True, "domain": DOMAIN,
                "declaration_uncertainties": UNCERTAINTIES,
                "sources": {source: sha("uc-library/" + source) for source in SOURCES},
                "repository_sources": {"third_party/ccl-framework/core/" + name:
                                       sha("third_party/ccl-framework/core/" + name) for name in CORE}}
    proof = {"differential_passed": True, "fresh_checker_passed": fresh, "domain": DOMAIN,
             "case_count": len(cases), "observations": observed,
             "original": fixture | {"cases": len(cases)},
             "limitations": LIMITATIONS,
             "fixture_sha256": sha(FIXTURE), "checker_sha256": sha(__file__),
             "native_producer_sha256": sha(FIXTURE.with_name("native.py")),
             "replay_source_sha256": sha(FIXTURE.with_name("Replay.cpp")),
             "format_version": subprocess.check_output(
                 ["uc-library/.venv/bin/clang-format", "--version"], text=True).strip(),
             "object_sha256": sha(args.object), "executable_sha256": sha(args.exe),
             "integration_sha256": sha(args.integration) if fresh else None,
             "verified_symbol": found[0], "proposed_readiness": {"ready": [], "pending": [proposal]}}
    if args.out.exists():
        previous = args.out.with_name(f"{args.out.stem}.previous-{sha(args.out)}.json")
        if not previous.exists():
            previous.write_bytes(args.out.read_bytes())
    args.out.write_text(json.dumps(proof, indent=2) + "\n")
    print(f"{TASK}: {len(cases)} FX cases passed; fresh_checker_passed={fresh}")


if __name__ == "__main__":
    main()
