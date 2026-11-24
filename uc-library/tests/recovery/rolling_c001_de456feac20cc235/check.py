"""Compare the linked portable replay against independently observed ARM results."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess
from datetime import datetime, timezone

SYMBOL = "_ZN8Presonus5Panel12MeterControl6castToEi"
DOMAIN = ("Both literal hits, their immediate neighbors and signed int boundaries "
          "at two distinct receiver addresses. Compare receiver identity or null, "
          "and check portable per-instance state preservation.")


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def run(argv, **kwargs):
    return subprocess.run(argv, check=True, text=True, capture_output=True, **kwargs).stdout


def symbols(object_file):
    table = run(["nm", "--defined-only", str(object_file)])
    matches = [line for line in table.splitlines() if line.split()[-1:] == [SYMBOL]]
    assert len(matches) == 1 and matches[0].split()[-2] in ("T", "W"), matches
    return matches[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", type=Path)
    parser.add_argument("--object", required=True, type=Path)
    parser.add_argument("--fixtures", type=Path)
    parser.add_argument("--integration", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    entry = symbols(args.object)
    if args.exe is None:
        print(entry)
        return
    source = Path(__file__).resolve().parents[3]
    source_paths = ("include/presonus/surface_panel/MeterControl.hpp",
                    "src/surface_panel/MeterControl.cpp",
                    "include/presonus/surface_panel/DbTable.hpp",
                    "src/surface_panel/DbTable.cpp")
    fmt = str(source / ".venv/bin/clang-format")
    format_argv = [fmt, "--style=file", "--fallback-style=LLVM", "--dry-run", "--Werror",
                   *(str(source / path) for path in source_paths[:2]),
                   str(Path(__file__).with_name("Replay.cpp"))]
    run(format_argv)
    start = datetime.now(timezone.utc).isoformat()
    role_receipts, pending = [], []
    for role in json.loads(args.fixtures.read_text())["roles"]:
        inputs = "".join(f"{case['class_id']}\n" for case in role["cases"])
        expected = [[str(int(value["r0"] == value["receiver"]))
                     for value in case["native"]] for case in role["cases"]]
        actual = run([str(args.exe.resolve())], input=inputs).splitlines()
        assert [line.split() for line in actual] == expected, role["original"]
        original = role["original"].copy()
        original["original_elf_sha256"] = original.pop("elf_sha256")
        pending.append({
            **original, "cpp_compiled": True, "mangling_namespace_checked": True,
            "portable_ready": False, "validation_domain": DOMAIN,
            "sources": {path: digest(source / path) for path in source_paths},
            "declaration_uncertainties": [
                "Original pointer result type is unresolved. The source port uses void*.",
                "Original member declaration, inheritance and virtual/override traits remain unresolved. The port uses a nonvirtual instance method."
            ],
        })
        role_receipts.append({key: role[key] for key in
                              ("original", "path", "file_offset", "section_name", "range_sha256")}
                             | {"portable_cases": sum(map(len, expected))})
    assert {role["original"]["role"] for role in role_receipts} == {"client", "server"}
    proof = {
        "cpp_differential_passed": True, "compiled_mangled_names_matched": True,
        "mangled_names": [SYMBOL], "compiled_symbol": entry,
        "proposed_readiness": {"ready": [], "pending": pending},
        "roles": role_receipts, "formatter_version": run([fmt, "--version"]).strip(),
        "format_argv": format_argv, "format_check_passed": True,
        "fixture_sha256": digest(args.fixtures),
        "native_producer_sha256": digest(Path(__file__).with_name("native.py")),
        "checker_sha256": digest(Path(__file__)),
        "exe_sha256": digest(args.exe), "object_sha256": digest(args.object),
        "integration_sha256": digest(args.integration) if args.integration else None,
        "replay_start_utc": start, "replay_end_utc": datetime.now(timezone.utc).isoformat(),
    }
    args.out.write_text(json.dumps(proof, indent=2) + "\n")
    print(f"PASS: {sum(row['portable_cases'] for row in role_receipts)} differential comparisons")


if __name__ == "__main__":
    main()
