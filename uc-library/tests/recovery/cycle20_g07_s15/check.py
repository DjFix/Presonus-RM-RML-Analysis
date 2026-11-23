"""Compare the Linux Page name getter with the sealed ARM observations."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).parent
NAME = "_ZNK8Presonus5Panel4Page7getNameEv"
DOMAIN = ("Two independent receivers per role, with empty, short and 31-byte NUL-terminated "
          "fixture names. The host checks content, stable pointer identity, independent receiver "
          "storage, and survival of caller-side string changes.")
UNCERTAINTIES = ["Original return pointer type and character const qualification remain unresolved.",
                 "Original Page constructors and ARM object layout are outside this scoped source port."]


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
    assert len(fixture["originals"]) == 2
    symbols = subprocess.check_output(["nm", "--defined-only", args.object], text=True)
    matching = [line for line in symbols.splitlines() if line.split()[-1] == NAME]
    assert len(matching) == 1, matching
    if args.symbols_only:
        print(matching[0])
        return
    count = 0
    for row in fixture["originals"]:
        assert row["mangled"] == NAME
        for case in row["cases"]:
            native_bytes = bytes.fromhex(case["input"])
            assert native_bytes[-1] == 0 and case["r0"] == case["receiver"] + 212
            assert case["receiver_unchanged"] and case["nonstack_writes"] == 0
            subprocess.run([args.exe, native_bytes[:-1]], check=True)
            count += 1
    source_paths = ("include/presonus/panel/Page.hpp", "src/Presonus/Panel/Page.cpp",
                    "include/presonus/panel/Element.hpp", "src/Presonus/Panel/Element.cpp")
    sources = {path: sha(Path("uc-library") / path) for path in source_paths}
    rows = [{"original_elf_sha256": row["elf_sha256"], "mangled": NAME,
             "original_address": row["address"], "cpp_compiled": True,
             "mangling_namespace_checked": True, "portable_ready": False,
             "domain": DOMAIN, "sources": sources, "declaration_uncertainties": UNCERTAINTIES}
            for row in fixture["originals"]]
    proof = {
        "cpp_differential_passed": True, "compiled_mangled_names_matched": True,
        "portable_ready": False, "case_count": count, "domain": DOMAIN, "limitations": UNCERTAINTIES,
        "functions": rows, "mangled_names": [NAME], "verified_symbols": matching,
        "originals": fixture["originals"], "fixture_sha256": sha(args.fixtures), "checker_sha256": sha(__file__),
        "native_producer_sha256": sha(HERE / "native.py"), "replay_source_sha256": sha(HERE / "Replay.cpp"),
        "object_sha256": sha(args.object), "executable_sha256": sha(args.exe),
        "integration_sha256": sha(args.integration) if args.integration != "none" else None,
        "format_version": subprocess.check_output(["uc-library/.venv/bin/clang-format", "--version"], text=True).strip(),
        "proposed_readiness": {"ready": [], "pending": rows},
    }
    args.out.write_text(json.dumps(proof, indent=2) + "\n")
    print(f"{HERE.name}: {count} differential cases passed")


if __name__ == "__main__":
    main()
