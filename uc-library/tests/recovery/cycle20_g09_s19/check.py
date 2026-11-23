"""Check one paired mixer formatter using genuine CCL source and ARM fixtures."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

from native import CLASS_NAME, TARGETS, generate

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parents[3]
TESTS = TESTS.relative_to(ROOT)
SCRATCH = ROOT / "temp/recovery-work/actual07-g09" / TESTS.name
FILES = [
    f"uc-library/include/presonus/mixer/{CLASS_NAME}.hpp",
    f"uc-library/src/Presonus/Mixer/{CLASS_NAME}.cpp",
    str(TESTS / "Replay.cpp"),
]
DOMAIN = (
    f"{CLASS_NAME}::print exact RM 13731 and CS18 13840 native entries, "
    "paired per-role finite values and truncation, with Data value bits, "
    "full 64-byte output including guard bytes, and unchanged Data context. "
    "Native provider boundary models cover only the recorded named "
    "CCL CString, C runtime and ARM soft-float operations. Portable replay "
    "uses actual pinned Core::Formatter::Data and CString128 source and "
    "checks the inherited CCL scan. Original plain return and original class "
    "layout remain independently unresolved."
)


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def run(argv, payload=None):
    argv = list(map(str, argv))
    print(json.dumps(argv), flush=True)
    return subprocess.run(
        argv, cwd=ROOT, input=payload, capture_output=True, check=True,
        env={**os.environ, "TMPDIR": str(SCRATCH), "LC_ALL": "C"},
    ).stdout


def compile_replay(executable, production):
    flags = [
        "/usr/bin/c++", "-std=c++17", "-ffp-contract=off", "-fno-lto",
        "-Iuc-library/include", "-Ithird_party/ccl-framework",
    ]
    driver = SCRATCH / "driver.o"
    run([*flags, "-O2", "-MMD", "-MF", SCRATCH / "production.d",
         "-c", FILES[1], "-o", production])
    run([*flags, "-O0", "-MMD", "-MF", SCRATCH / "driver.d",
         "-c", FILES[2], "-o", driver])
    run(["/usr/bin/c++", production, driver, "-o", executable])


def check_symbols(production):
    targets = {target["mangled"] for target in TARGETS}
    prefix = f"_ZN8Presonus5Mixer{len(CLASS_NAME)}{CLASS_NAME}"
    companions = {prefix + variant + "Ev" for variant in ("D0", "D1", "D2")}
    lines = run(["/usr/bin/nm", "--defined-only", production]).decode().splitlines()
    symbols = {row.split()[-1]: row for row in lines if row.split()}
    missing = (targets | companions) - symbols.keys()
    if missing:
        raise ValueError(f"Expected symbols missing: {sorted(missing)}")
    if f"_ZNK8Presonus5Mixer{len(CLASS_NAME)}{CLASS_NAME}4scanERN4Core9Formatter4DataE" in symbols:
        raise ValueError("Unexpected app scan override")
    checked = {name: symbols[name] for name in sorted(targets | companions)}
    print(json.dumps(checked), flush=True)
    return checked


def replay(executable, fixtures):
    rows = [case for original in fixtures["originals"] for case in original["cases"]]
    payload = "".join(
        f"{case['input_value']} {case['style']} {case['capacity']}\n" for case in rows
    ).encode()
    observed = run([executable], payload).decode().splitlines()
    expected = [
        f"{case['value_after']} {case['output_hex']}"
        + "d9" * (64 - case["capacity"])
        for case in rows
    ]
    if observed != expected:
        for index, (actual, wanted) in enumerate(zip(observed, expected)):
            if actual != wanted:
                raise ValueError(f"Case {index} {rows[index]}: {actual!r} != {wanted!r}")
        raise ValueError(f"Incorrect row count: {len(observed)} vs {len(expected)}")
    print(f"{len(rows)} paired ARM differential cases passed")
    return len(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["format", "compile", "symbols", "native", "replay", "canonical"])
    parser.add_argument("--exe", type=Path, default=SCRATCH / "replay")
    parser.add_argument("--object", type=Path, default=SCRATCH / "production.o")
    parser.add_argument("--fixtures", type=Path, default=TESTS / "fixtures.json")
    parser.add_argument("--integration", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.mode in ("format", "compile"):
        SCRATCH.mkdir(parents=True, exist_ok=True)
    if args.mode == "format":
        run(["uc-library/.venv/bin/clang-format", "--style=file",
             "--fallback-style=LLVM", "--dry-run", "--Werror", *FILES])
        return
    if args.mode == "compile":
        compile_replay(args.exe, args.object)
        return
    if args.mode == "symbols":
        check_symbols(args.object)
        return
    fixtures = json.loads(args.fixtures.read_text())
    if args.mode == "native":
        if generate() != fixtures:
            raise ValueError("Fresh ARM observations differ from sealed fixtures")
        print(f"{sum(row['iterations'] for row in fixtures['originals'])} original ARM observations matched")
        return
    count = replay(args.exe, fixtures)
    if args.mode == "canonical":
        if args.out is None or args.integration is None:
            parser.error("canonical requires --integration and --out")
        integration = json.loads(args.integration.read_text())
        if not isinstance(integration, dict) or not integration:
            parser.error("expected nonempty integration receipt")
        receipt = {
            "behavior_validated": True, "domain": DOMAIN, "cases": count,
            "originals": [{key: row[key] for key in ("elf_sha256", "original_mangled",
                         "address", "size", "section", "file_offset", "range_sha256")}
                          for row in fixtures["originals"]],
            "compiled_symbols": check_symbols(args.object),
            "fixtures_sha256": digest(args.fixtures),
            "executable_sha256": digest(args.exe),
            "object_sha256": digest(args.object),
            "integration_sha256": digest(args.integration),
        }
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as failure:
        if failure.stdout:
            print(failure.stdout.decode(errors="replace"))
        if failure.stderr:
            print(failure.stderr.decode(errors="replace"))
        raise
