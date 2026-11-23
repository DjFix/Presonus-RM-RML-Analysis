"""Check actual tagged formatter D0 release and genuine CCL registration."""
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
PARENT = CLASS_NAME[:-2]
BASE_FILES = [f"uc-library/include/presonus/mixer/{PARENT}.hpp",
              f"uc-library/src/Presonus/Mixer/{PARENT}.cpp"]
CCL = Path("third_party/ccl-framework/core")
DOMAIN = (
    f"{CLASS_NAME} exact RM 13731 and CS18 13840 deleting destructor, three "
    "seeded receivers per role with original unsized delete writing the base "
    "vptr first and unmapping the same modeled receiver. Separate D1 preserves "
    "storage. Actual ARM initializer establishes names and relative order. "
    "Portable typed object uses inherited application print and pinned CCL "
    "scan and registry. Portable D0 reaches unsized delete and releases its "
    "mmap-backed testing allocation; D1 leaves storage alive."
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
        "/usr/bin/c++", "-std=c++17", "-fno-lto", "-fno-sized-deallocation",
        "-ffunction-sections", "-fdata-sections",
        "-Iuc-library/include", "-Ithird_party/ccl-framework",
    ]
    objects = []
    for name, source in (
        ("production", FILES[1]), ("driver", FILES[2]), ("base", BASE_FILES[1]),
        ("registry", CCL / "public/coreformatter.cpp"),
        ("allocator", CCL / "malloc/coremalloc.cpp"),
    ):
        obj = production if name == "production" else SCRATCH / (name + ".o")
        run([*flags, "-O0" if name == "driver" else "-O2", "-MMD", "-MF",
             SCRATCH / (name + ".d"), "-c", source, "-o", obj])
        objects.append(obj)
    run(["/usr/bin/c++", *objects, "-Wl,--gc-sections,--wrap=_ZdlPv,--wrap=_Znwm", "-o", executable])


def check_symbols(production):
    targets = {target["original_mangled"] for target in TARGETS}
    prefix = f"_ZN8Presonus5Mixer{len(CLASS_NAME)}{CLASS_NAME}"
    companions = {prefix + variant + "Ev" for variant in ("D0", "D1", "D2")}
    lines = run(["/usr/bin/nm", "--defined-only", production]).decode().splitlines()
    symbols = {row.split()[-1]: row for row in lines if row.split()}
    missing = (targets | companions) - symbols.keys()
    if missing:
        raise ValueError(f"Expected symbols missing: {sorted(missing)}")
    if f"_ZNK8Presonus5Mixer{len(CLASS_NAME)}{CLASS_NAME}4scanERN4Core9Formatter4DataE" in symbols:
        raise ValueError("Unexpected app scan override")
    original, = targets
    disassembly = run(["/usr/bin/objdump", "-dr",
                       f"--disassemble={original}", production]).decode()
    active = disassembly.split(f"<{original}>:", 1)[1]
    # In the out-of-line D0, verify the target relocation of the actual
    # branch (a tail call is possible); avoid matching diagnostic text.
    import re
    if not re.search(r"R_\S+\s+_ZdlPv(?:[-+]|\s|$)", active):
        raise ValueError("Deleting destructor does not reference unsized operator delete")
    if re.search(r"R_\S+\s+_ZdlPvm(?:[-+]|\s|$)", active):
        raise ValueError("Unexpected sized deallocation in D0")
    checked = {name: symbols[name] for name in sorted(targets | companions)}
    print(json.dumps(checked), flush=True)
    return {"symbols": checked, "deleting_destructor_disassembly": active.strip()}


def replay(executable, fixtures):
    rows = [(original["name"], case["seed"])
            for original in fixtures["originals"] for case in original["variants"]["D0"]["cases"]]
    payload = "".join(f"{name} {seed}\n" for name, seed in rows).encode()
    observed = run([executable], payload).decode().splitlines()
    expected = [f"{name} {seed} 1 0" for name, seed in rows]
    if observed != expected:
        raise ValueError(f"Portable registry or disposal mismatch: {observed!r} != {expected!r}")
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
        count = sum(len(row["variants"]["D0"]["cases"]) for row in fixtures["originals"])
        print(f"{count} original ARM observations matched")
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
            "originals": [{key: row[key] for key in ("elf_sha256", "original_mangled", "range")}
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
