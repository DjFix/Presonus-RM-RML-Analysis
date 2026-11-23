"""Validate a compiled Element object and executable against its sealed native cases."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

TASK = "cycle20_g06_s01"
READY = True
DOMAIN = 'Two sentinel receiver states per exact original. Observe original primary vptr reset, untouched receiver tail and no import for D1/D2, or one same-receiver unsized delete and controlled heap release for D0. Linux completes a stack lifetime, tears down the base of a derived lifetime, and forwards one actual heap free through the real unsized deallocation function.'
LIMITS = 'Original import runtime implementation, derived or secondary original vtables, original object layout, ARM ABI interoperability and hardware are outside the observed domain. The host compiler aliases D1 and D2; exact original ranges are separate and were each executed.'
TEST = Path(__file__).parent
SOURCE_PATHS = ['include/presonus/panel/Element.hpp', 'src/Presonus/Panel/Element.cpp']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def consume_fixture(args):
    assert sha(args.fixtures) == args.fixture_sha256
    fixture = json.loads(args.fixtures.read_text())
    assert fixture["task_id"] == TASK
    return fixture


def symbols(object_path, fixture):
    completed = subprocess.run(["nm", "--defined-only", "--format=posix", object_path],
                               check=True, text=True, capture_output=True)
    entries = {line.split()[0]: line.split()[1:] for line in completed.stdout.splitlines()}
    expected = {row["mangled"] for row in fixture["originals"]}
    assert all(entries[name][0] == "T" for name in expected)
    output = {name: entries[name] for name in sorted(expected)}
    if READY:
        disassembly = subprocess.run(["objdump", "-dr", object_path],
                                     check=True, text=True, capture_output=True).stdout
        d0 = disassembly.split(" <_ZN8Presonus5Panel7ElementD0Ev>:\n", 1)[1].split("\n\n", 1)[0]
        assert re.search(r"\bR_\S+\s+_ZdlPv(?:[+\-\s]|$)", d0), d0
        assert "_ZdlPvm" not in d0
    return output


def compare(portable, fixture):
    if READY:
        expected = {}
        for original in fixture["originals"]:
            for case in original["observations"]:
                observed = int(case["controlled_heap_released"])
                assert len(case["external_calls"]) == observed
                assert expected.setdefault(original["variant"], observed) == observed
        assert portable == [f"D1 {expected['D1']}", f"D2 {expected['D2']} 1", f"D0 {expected['D0']}"]
        return 3
    for original in fixture["originals"]:
        expected = []
        for case in original["observations"]:
            assert not case["non_stack_accesses"]
            assert case["receiver_unchanged"] and case["display_unchanged"]
            expected.append(f"{case['force']} {len(case['external_calls'])} 1")
        assert portable == expected
    return len(portable)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["native", "symbols", "replay"])
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--fixture-sha256", required=True)
    parser.add_argument("--object", type=Path)
    parser.add_argument("--exe", type=Path)
    parser.add_argument("--integration", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    fixture = consume_fixture(args)
    if args.mode == "native":
        replay = subprocess.run([sys.executable, "-B", TEST / "native.py"],
                                check=True, capture_output=True, text=True)
        assert json.loads(replay.stdout) == fixture
        print(f"{TASK} independently reproduced fixtures")
        return

    names = symbols(args.object, fixture)
    if args.mode == "symbols":
        print(json.dumps(names, sort_keys=True))
        return
    result = subprocess.run([args.exe.resolve()], check=True, capture_output=True, text=True)
    portable = result.stdout.splitlines()
    portable_cases = compare(portable, fixture)
    source_hashes = {name: sha(Path("uc-library") / name) for name in SOURCE_PATHS}
    sources = dict(source_hashes)
    rows = []
    for original in fixture["originals"]:
        row = {key: original[key] for key in ("original_elf_sha256", "mangled", "firmware", "role")}
        row.update(original_address=original["address"], cpp_compiled=True,
                   mangling_namespace_checked=True, portable_ready=READY,
                   domain=f"{original['role']} {original['variant']}: {DOMAIN}",
                   sources=sources, repository_sources={})
        if not READY:
            row["declaration_uncertainties"] = ["Original return declaration is unresolved; portable void models the bounded base-call behavior."]
        rows.append(row)
    formatter = ["uc-library/.venv/bin/clang-format", "--style=file", "--fallback-style=LLVM"]
    subprocess.run([*formatter, "--dry-run", "--Werror",
                    *[f"uc-library/{name}" for name in SOURCE_PATHS
                      if name != "include/presonus/surface_panel/IDisplay.hpp"],
                    str(TEST / "Replay.cpp")], check=True)
    formatter_version = subprocess.check_output([formatter[0], "--version"], text=True).strip()
    integrated = json.loads(args.integration.read_text())
    assert integrated["ctest_passed"] is True and integrated["platform"] == "linux"
    proof = {
        "task_id": TASK, "cpp_differential_passed": True,
        "compiled_mangled_names_matched": True, "portable_ready": READY,
        "compiled_symbols": names, "functions": rows, "domain": DOMAIN, "limitations": LIMITS,
        "originals": fixture["originals"], "native_scope": fixture["scope"],
        "native_case_count": sum(len(row["observations"]) for row in fixture["originals"]),
        "portable_case_count": portable_cases, "portable_stdout": portable,
        "sources": source_hashes, "formatter_version": formatter_version,
        "format_check_passed": True, "fixtures_sha256": sha(args.fixtures),
        "object_sha256": sha(args.object), "exe_sha256": sha(args.exe),
        "integration_reference": str(args.integration), "integration_sha256": sha(args.integration),
        "producers": {str(path): sha(path) for path in
                      (Path(__file__), TEST / "Replay.cpp", TEST / "native.py")},
        "proposed_readiness": {"ready": rows if READY else [], "pending": [] if READY else rows},
        "replay_argv": sys.argv,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(proof, indent=2, sort_keys=True) + "\n")
    print(f"{TASK}: {proof['native_case_count']} original and {portable_cases} portable observations passed")


if __name__ == "__main__":
    main()
