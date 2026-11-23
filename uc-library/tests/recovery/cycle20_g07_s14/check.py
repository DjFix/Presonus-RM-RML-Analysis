"""Compare Linux Page destructor variants with independent ARM observations."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).parent
SOURCES = ("include/presonus/panel/Page.hpp", "src/Presonus/Panel/Page.cpp",
           "include/presonus/panel/Element.hpp", "src/Presonus/Panel/Element.cpp")
DOMAIN = ("Five slot configurations per ELF/variant, covering empty lists, null-only, "
          "one Element and interspersed nulls with multiple Elements. Verify forward "
          "virtual Element teardown, receiver retention for D1/D2, and unsized receiver "
          "delete after children for D0. The host checks default enabled state.")
LIMITATIONS = ["The imported native unsized delete is a memory-unmapping shim at the verified PLT target.",
               "The original constructors are excluded; initializer instructions provide only the enabled default.",
               "The portable source uses typed Element slots and owned name storage. Original ARM layout, "
               "derived behavior and device integration remain unresolved."]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--object", required=True)
    parser.add_argument("--exe")
    parser.add_argument("--fixtures", default=HERE / "fixtures.json", type=Path)
    parser.add_argument("--integration", default="none")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--symbols-only", action="store_true")
    args = parser.parse_args()
    fixture = json.loads(args.fixtures.read_text())
    names = sorted({item["mangled"] for item in fixture["originals"]})
    assert len(fixture["originals"]) == 6 and len(names) == 3
    table = subprocess.check_output(["nm", "--defined-only", args.object], text=True)
    matching = [line for line in table.splitlines() if line.split()[-1] in names]
    assert sorted(line.split()[-1] for line in matching) == names, matching
    if args.symbols_only:
        print("\n".join(matching))
        return
    traces = []
    for row in fixture["originals"]:
        variant = row["variant"]
        for case in row["cases"]:
            slots = "".join("0" if child is None else "1" for child in case["layout"])
            expected = []
            for receiver in case["deallocation_order"]:
                expected.append(90 if receiver == "root" else 10 + int(receiver.split(".")[1]))
            observed = subprocess.check_output([args.exe, str(variant), slots], text=True)
            enabled, *events = map(int, observed.split())
            assert enabled == 1 and events == expected, (row["role"], variant, slots, expected, observed)
            traces.append({"role": row["role"], "variant": variant, "slots": slots, "events": events})
    sources = {path: sha(Path("uc-library") / path) for path in SOURCES}
    rows = [{"original_elf_sha256": row["elf_sha256"], "mangled": row["mangled"],
             "original_address": row["address"], "cpp_compiled": True,
             "mangling_namespace_checked": True, "portable_ready": True,
             "domain": DOMAIN, "sources": sources} for row in fixture["originals"]]
    proof = {
        "cpp_differential_passed": True, "compiled_mangled_names_matched": True,
        "portable_ready": True, "case_count": len(traces), "domain": DOMAIN,
        "limitations": LIMITATIONS, "functions": rows, "mangled_names": names,
        "verified_symbols": matching, "observations": traces,
        "originals": fixture["originals"], "constructor_initializer": fixture["constructor_initializer"],
        "fixture_sha256": sha(args.fixtures), "checker_sha256": sha(__file__),
        "native_producer_sha256": sha(HERE / "native.py"), "replay_source_sha256": sha(HERE / "Replay.cpp"),
        "object_sha256": sha(args.object), "executable_sha256": sha(args.exe),
        "integration_sha256": sha(args.integration) if args.integration != "none" else None,
        "format_version": subprocess.check_output(["uc-library/.venv/bin/clang-format", "--version"], text=True).strip(),
        "proposed_readiness": {"ready": rows, "pending": []},
    }
    args.out.write_text(json.dumps(proof, indent=2) + "\n")
    print(f"{HERE.name}: {len(traces)} differential cases passed")


if __name__ == "__main__":
    main()
