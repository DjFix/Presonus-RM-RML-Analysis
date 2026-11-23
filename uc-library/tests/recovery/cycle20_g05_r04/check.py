"""Check a linked portable replay against per-original ARM observations."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def check_symbols(path, mangled):
    values = {}
    for line in subprocess.check_output(["nm", "--defined-only", path], text=True).splitlines():
        tokens = line.split()
        if len(tokens) == 3 and tokens[2] in (mangled, mangled.replace("D0Ev", "D1Ev"),
                                               mangled.replace("D0Ev", "D2Ev")):
            values[tokens[2]] = line
    if mangled not in values:
        raise SystemExit(f"Missing compiled {mangled}")
    record = {"exact": values[mangled]}
    if mangled.endswith("D0Ev"):
        code = subprocess.check_output(["objdump", "-dr", f"--disassemble={mangled}", path],
                                       text=True)
        deletes = re.findall(r"\b_ZdlPv(?:m)?\b", code)
        if deletes != ["_ZdlPv"]:
            raise SystemExit(f"Expected one compiled unsized delete relocation: {mangled}")
        if "SevenSegControl" in mangled and "_ZN8Presonus5Panel7ControlD2Ev" not in code:
            raise SystemExit("Missing compiled typed Control D2 call")
        record["delete"] = deletes[0]
        record["compiler_variants"] = {k: v for k, v in values.items() if k != mangled}
    return record


def expected_lines(original):
    lines = []
    for case in original["observations"]:
        calls = case["calls"]
        if calls:
            if not case["receiver_disposed"] or calls[-1] != "delete":
                raise SystemExit("Original D0 fixture lacks receiver disposal")
            lines.append(" ".join([*calls, "1"]))
        elif case["object_writes"] or case["receiver_disposed"]:
            raise SystemExit("Callback native fixture has nondefault observation")
        else:
            lines.append("no-effect")
    return lines


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", type=Path)
    parser.add_argument("--object", type=Path, required=True)
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--integration")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--symbols-only", action="store_true")
    args = parser.parse_args()
    fixture = json.loads(args.fixtures.read_bytes())
    originals = fixture["originals"]
    symbols = check_symbols(args.object, originals[0]["mangled"])
    if args.symbols_only:
        print(json.dumps(symbols))
        return
    if not all((args.exe, args.integration, args.out)):
        parser.error("Replay requires executable, integration and output")
    result = subprocess.run([args.exe.resolve()], check=True, capture_output=True, text=True)
    lines = result.stdout.splitlines()
    for row in originals:
        if lines != expected_lines(row) or result.stderr:
            raise SystemExit(f"Portable result differs from {row['role']} observation")
    birth = Path(__file__).parent.name.removeprefix("cycle20_g05_")
    if birth == "r04":
        files = ["src/surface_panel/ControlHelpers.cpp", "include/presonus/surface_panel/ControlHelpers.hpp",
                 "src/Presonus/Panel/control.cpp", "include/presonus/panel/control.hpp"]
        core = ["third_party/ccl-framework/core/portable/coreparams.h"]
        domain = ("Three SevenSegControl heap lifetimes with actual typed Control base "
                  "cleanup, three genuine CCL observer removals and owned vs unrelated "
                  "timer isolation. Original two-role D0 observes Control D2 boundary then "
                  "verified delete PLT on the same receiver, disposed in the emulator.")
        uncertainty = []
    elif int(birth[1:]) <= 9:
        files = ["src/Presonus/Panel/ControlRegistrarDelegate.cpp",
                 "include/presonus/surface_panel/ControlHelpers.hpp"]
        if birth in ("s06", "s07"):
            files.append("src/Presonus/Surface/SurfaceRootComponent.cpp")
        core = ["third_party/ccl-framework/core/portable/coreparams.h"]
        domain = ("Three bounded callback cases for each original role and live typed "
                  "portable arguments. Observe no registrar, delegate or control byte "
                  "mutation and no unexpected output. For fader and switch, confirm "
                  "existing SurfaceRoot typed virtual focus dispatch through real CCL.")
        uncertainty = ["Original unencoded return spelling and native delegate ABI unresolved."]
    else:
        files = ["src/Presonus/Mixer/DecayTimeFormatter.cpp",
                 "include/presonus/mixer/DecayTimeFormatter.hpp"]
        files.extend(f"{prefix}/DecayTimeFormatterT{n}.{ext}" for n in range(1, 6)
                     for prefix, ext in (("src/Presonus/Mixer", "cpp"),
                                         ("include/presonus/mixer", "hpp")))
        core = ["third_party/ccl-framework/core/public/coreformatter.h",
                "third_party/ccl-framework/core/public/coreformatter.cpp"]
        domain = ("Three selected typed deleting lifetimes and exactly one host release "
                  "per receiver through the formatter virtual interface. Compare both "
                  "native D0 roles via exact delete PLT and emulated receiver unmapping. "
                  "Check the real CCL registry lookup, stable typed registration and "
                  "canonical print/scan behavior.")
        uncertainty = []
    rows = {"ready": [], "pending": []}
    for row in originals:
        proposal = {"mangled": row["mangled"], "original_elf_sha256": row["elf_sha256"],
                    "cpp_compiled": True, "mangling_namespace_checked": True,
                    "portable_ready": not uncertainty, "domain": domain,
                    "sources": {p: digest(Path("uc-library") / p) for p in files},
                    "repository_sources": {p: digest(p) for p in core}}
        if uncertainty:
            proposal["declaration_uncertainties"] = uncertainty
        rows["pending" if uncertainty else "ready"].append(proposal)
    integration = None if args.integration == "ctest" else {
        "path": args.integration, "sha256": digest(args.integration)}
    proof = {"behavior_validation_passed": True, "validation_domain": domain,
             "integration": integration, "proposed_readiness": rows,
             "fixture": {"path": str(args.fixtures), "sha256": digest(args.fixtures)},
             "object": {"path": str(args.object), "sha256": digest(args.object), **symbols},
             "executable": {"path": str(args.exe), "sha256": digest(args.exe)},
             "observations": lines, "case_count": len(lines)}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(proof, indent=2) + "\n")
    print(f"Matched {len(lines)} portable cases against each of {len(originals)} original roles")


if __name__ == "__main__":
    main()
