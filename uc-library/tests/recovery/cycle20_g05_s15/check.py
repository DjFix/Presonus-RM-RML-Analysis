"""Check host deleting-destructor, complete companion, and pinned-registry observations."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

DOMAIN = ("Three real portable heap lifetimes freed once by exact unsized delete "
          "through the typed formatter vtable, three complete-destructor cases "
          "leaving placement storage allocated, and two passes through the "
          "actual pinned CCL registry with observed native name order and stable "
          "typed prototypes. Compare inherited print and scan with real base "
          "providers at values below, at, and above 10. Both original ARM roles "
          "execute independently with modeled unsized delete disposal and an "
          "exact hashed D1 companion checked without classification credit.")


def digest(path):
    with Path(path).open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def allocate_tokens(obj, symbol):
    output = subprocess.check_output(["objdump", "-dr", f"--disassemble={symbol}", obj], text=True)
    return re.findall(r"\b_ZdlPv(?:m)?\b", output)


def binary_observation(obj, symbol):
    names = {symbol.replace("D0Ev", variant + "Ev") for variant in ("D0", "D1", "D2")}
    lines = subprocess.check_output(["nm", "--defined-only", obj], text=True).splitlines()
    found = {}
    for line in lines:
        tag = line.split()
        if len(tag) == 3 and tag[-1] in names:
            if tag[1] != "W" or tag[-1] in found:
                raise SystemExit("Expected one compiler-emitted weak symbol per variant")
            found[tag[-1]] = line
    if set(found) != names or allocate_tokens(obj, symbol) != ["_ZdlPv"]:
        raise SystemExit("Expected exact D0 and exactly one unsized delete relocation")
    companions = {name: found[name] for name in sorted(names - {symbol})}
    for name in companions:
        if allocate_tokens(obj, name):
            raise SystemExit("Non-deleting compiler companion calls delete")
    return {"exact": found[symbol], "delete": "_ZdlPv",
            "compiler_companions_no_credit": companions}


def source_files(fixture):
    cls = fixture["class_name"]
    if cls.startswith("DecayTime"):
        group = ["DecayTimeFormatter", *(f"DecayTimeFormatterT{n}" for n in range(6,10))]
    else:
        group = ["EarlyRefFormatter", "PreDelayFormatter",
                 "PreDelayFormatterT2", "EarlyRefFormatterT2"]
    files = [f"{folder}/{name}.{ext}" for name in group for folder, ext in
             (("include/presonus/mixer", "hpp"), ("src/Presonus/Mixer", "cpp"))]
    return {name: digest(Path("uc-library") / name) for name in files}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", type=Path)
    parser.add_argument("--object", required=True, type=Path)
    parser.add_argument("--fixtures", required=True, type=Path)
    parser.add_argument("--integration")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--symbols-only", action="store_true")
    args = parser.parse_args()
    fixture = json.loads(args.fixtures.read_bytes())
    originals = fixture["originals"]
    witness = binary_observation(args.object, originals[0]["mangled"])
    if args.symbols_only:
        print(json.dumps(witness))
        return
    if not all((args.exe, args.integration, args.out)):
        parser.error("Replay requires executable, integration and output")
    result = subprocess.run([args.exe.resolve()], check=True, capture_output=True, text=True)
    expected = ["registry " + name for name in fixture["registration_sequence"]]
    for original, complete in zip(originals, fixture["uncredited_D1"], strict=True):
        if original["elf_sha256"] != complete["elf_sha256"]:
            raise SystemExit("Original roles mixed")
        for row in original["observations"]:
            if row["calls"] != ["delete"] or not row["receiver_disposed"]:
                raise SystemExit("Native deleting observation incomplete")
        for row in complete["observations"]:
            if row["calls"] or row["receiver_disposed"]:
                raise SystemExit("Native complete destructor unexpectedly disposed receiver")
        role_expected = [*expected, *(["delete 1 complete 0"] * len(original["observations"]))]
        if result.stdout.splitlines() != role_expected or result.stderr:
            raise SystemExit(f"Portable behavior differs from {original['role']} fixture")
    core = ("third_party/ccl-framework/core/public/coreformatter.h",
            "third_party/ccl-framework/core/public/coreformatter.cpp")
    rows = [{"mangled": row["mangled"], "original_elf_sha256": row["elf_sha256"],
             "cpp_compiled": True, "mangling_namespace_checked": True, "portable_ready": True,
             "domain": DOMAIN, "sources": source_files(fixture),
             "repository_sources": {name: digest(name) for name in core}}
            for row in originals]
    integration = None if args.integration == "ctest" else {
        "path": args.integration, "sha256": digest(args.integration)}
    proof = {"behavior_validation_passed": True, "validation_domain": DOMAIN,
             "integration": integration, "proposed_readiness": {"ready": rows, "pending": []},
             "fixture": {"path": str(args.fixtures), "sha256": digest(args.fixtures)},
             "executable": {"path": str(args.exe), "sha256": digest(args.exe)},
             "object": {"path": str(args.object), "sha256": digest(args.object), **witness},
             "observations": result.stdout.splitlines()}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(proof, indent=2) + "\n")
    print("Matched both ARM roles, the complete companion, and pinned registry order")


if __name__ == "__main__":
    main()
