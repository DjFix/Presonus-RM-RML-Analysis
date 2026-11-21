"""Replay one MappingComponent constructor variant against its native observation."""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import subprocess

TASK = Path(__file__).parent.name
COMPLETE = TASK.endswith("s09")
FIXTURE = Path(__file__).with_name("fixtures.json")
HEADER = "include/presonus/surface/MappingComponent.hpp"
SOURCE = "src/Presonus/Surface/MappingComponent.cpp"
CORE = ["portable/corecomponent.h", "portable/corecomponent.cpp",
        "portable/coreattributes.h", "portable/coreattributes.cpp",
        "portable/coreparams.h", "portable/coreparams.cpp", "portable/coreparaminfo.h"]
DOMAIN = ("Exact CS18 13840 constructor variant, three isolated cases covering 16 numeric "
          "descriptors, normal and null parameter-insertion boundaries, actual native/host "
          "DelayTimer state, initialized portable CCL state and separate host-only unwind.")
UNCERTAINTIES = ["Original ARM layout, unrecovered virtual overrides and legacy Attributes member roles remain unresolved."]
LIMITATIONS = ["Native C1/C2 are distinct occurrences, each executed separately. Host compiler "
               "emits two aliases and each replay calls its designated symbol.",
               "Original Component, Attributes, ParamList and libc calls use controlled fixture boundaries. "
               "Host executes real CCL types and canonical DelayTimer. ARM exception paths are outside scope."]


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
    symbols = subprocess.check_output(["objdump", "-t", args.object], text=True)
    variants = {}
    for variant in ("C1","C2"):
        name = "_ZN8Presonus7Surface16MappingComponent" + variant + "Ev"
        found = [line.split() for line in symbols.splitlines() if line.split() and line.split()[-1] == name]
        if len(found) != 1:
            raise SystemExit(f"Missing emitted constructor variant {name}: {found}")
        variants[name] = found[0]
    if variants[list(variants)[0]][:-1] != variants[list(variants)[1]][:-1]:
        raise SystemExit("Expected a shared host constructor entry/section/range")
    if args.symbols_only:
        print(" ".join(variants[original["mangled"]]))
        return
    if not args.exe or not args.integration or not args.out:
        parser.error("--exe, --integration, and --out are required for replay")
    fresh = args.integration != "none"
    if fresh:
        integration = json.loads(Path(args.integration).read_text())
        if integration.get("platform") != "linux" or integration.get("ctest_passed") is not True:
            raise SystemExit("Expected a passing Linux integration receipt")
    cases = fixture["cases"]
    rows = "\n".join(str(case["missing_tag"]) for case in cases) + "\n"
    run = subprocess.run([args.exe], input=rows, text=True, capture_output=True)
    if run.returncode:
        raise SystemExit(f"Replay exited {run.returncode}: {run.stderr}\n{run.stdout}")
    observed = []
    current = {"descriptors":[],"initial_values":[],"timers":[]}
    count = None
    cleanup = []
    for row in map(shlex.split,run.stdout.splitlines()):
        kind, *values = row
        if kind == "D":
            current["descriptors"].append([int(values[0]),values[1],*map(float,values[2:])])
        elif kind == "N":
            current["component_name"] = values[0]
        elif kind == "T":
            current["timers"].append(list(map(int,values)))
        elif kind == "V":
            current["initial_values"].append(list(map(float,values)))
        elif kind == "END":
            observed.append(current)
            current = {"descriptors":[],"initial_values":[],"timers":[]}
        elif kind == "C":
            count = int(values[0])
        elif kind == "X":
            cleanup = list(map(int,values))
        else:
            raise SystemExit(f"Unknown replay record: {row}")
    expected = [{k:case[k] for k in ("descriptors","initial_values","timers","component_name")}
                for case in cases]
    if observed != expected:
        raise SystemExit(f"Mapping constructor observations differ:\n{observed}\n{expected}")
    if count != (len(cases)+1 if COMPLETE else 0) or cleanup != [2,3,4,4,4,5]:
        raise SystemExit(f"Missing complete constructor hook or actual host unwind: {count}, {cleanup}")
    proposal = {"original_elf_sha256": original["original_elf_sha256"], "mangled": original["mangled"],
                "cpp_compiled": True, "mangling_namespace_checked": True, "portable_ready": False,
                "differential_passed": True, "domain": DOMAIN,
                "declaration_uncertainties": UNCERTAINTIES,
                "sources": {p: sha("uc-library/" + p) for p in (HEADER,SOURCE)},
                "repository_sources": {"third_party/ccl-framework/core/" + name:
                                       sha("third_party/ccl-framework/core/" + name) for name in CORE}}
    proof = {"differential_passed": True, "fresh_checker_passed": fresh, "domain": DOMAIN,
             "case_count": len(cases), "observations": observed,
             "observed_host_unwind": cleanup, "host_ctor_variants": variants,
             "host_direct_C1_calls": count,
             "original": fixture | {"cases":len(cases)}, "limitations": LIMITATIONS,
             "fixture_sha256": sha(FIXTURE), "checker_sha256": sha(__file__),
             "native_producer_sha256": sha(FIXTURE.with_name("native.py")),
             "replay_source_sha256": sha(FIXTURE.with_name("Replay.cpp")),
             "format_version": subprocess.check_output(
                 ["uc-library/.venv/bin/clang-format","--version"], text=True).strip(),
             "object_sha256": sha(args.object), "executable_sha256": sha(args.exe),
             "integration_sha256": sha(args.integration) if fresh else None,
             "verified_symbol": variants[original["mangled"]],
             "proposed_readiness": {"ready":[],"pending":[proposal]}}
    if args.out.exists():
        previous = args.out.with_name(f"{args.out.stem}.previous-{sha(args.out)}.json")
        if not previous.exists():
            previous.write_bytes(args.out.read_bytes())
    args.out.write_text(json.dumps(proof,indent=2)+"\n")
    print(f"{TASK}: {len(cases)} constructor cases passed; fresh_checker_passed={fresh}")


if __name__ == "__main__":
    main()
