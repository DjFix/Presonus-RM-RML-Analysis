"""Build and validate the isolated ARM differential replay."""
import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path

from native import CLASS_NAME, NAME, generate

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parents[3]
TESTS = TESTS.relative_to(ROOT)
SCRATCH = ROOT / "temp/recovery-work/cycle20_g09" / TESTS.name
PROVIDERS = SCRATCH.parent / "providers"
FILES = [
    f"uc-library/include/presonus/mixer/{CLASS_NAME}.hpp",
    f"uc-library/src/Presonus/Mixer/{CLASS_NAME}.cpp",
    str(TESTS / "Replay.cpp"),
]
DOMAIN = (
    "RM 13731 tap executes via its exact direct entry and ELF-backed vtable "
    "slot on four synthetic receiver addresses per route. ARM preserves r0, "
    "receiver bytes and vtable bytes, writes only its stack and makes no calls. "
    "Portable typed receivers replay both routes and check unchanged state. "
    "A test override verifies virtual dispatch. Native r0 is a register "
    "observation and has no typed portable result comparison."
)


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def run(argv, payload=None):
    argv = list(map(str, argv))
    print(json.dumps(argv), flush=True)
    return subprocess.run(
        argv, cwd=ROOT, input=payload, capture_output=True, check=True,
        env={**os.environ, "TMPDIR": str(SCRATCH)},
    ).stdout


def compile_replay(executable, production):
    flags = [
        "/usr/bin/c++", "-std=c++17", "-fno-rtti", "-fno-lto", "-Wno-multichar",
        "-ffunction-sections", "-fdata-sections", "-UNDEBUG",
        "-Iuc-library/include", "-Ithird_party/ccl-framework",
    ]
    driver = SCRATCH / "driver.o"
    run([*flags, "-O3", "-MMD", "-MF", SCRATCH / "production.d",
         "-c", FILES[1], "-o", production])
    run([*flags, "-O0", "-MMD", "-MF", SCRATCH / "driver.d",
         "-c", FILES[2], "-o", driver])
    libraries = []
    if CLASS_NAME == "FXComponent":
        for line in (PROVIDERS / "RECEIPT.txt").read_text().splitlines():
            expected, original = line.split()
            provider = PROVIDERS / Path(original).name
            if digest(provider) != expected:
                raise ValueError(f"Provider archive changed: {provider}")
            libraries.append(provider)
    run([
        "/usr/bin/c++", production, driver, "-Wl,--gc-sections",
        *libraries, "-lz", "-lpthread", "-ldl", "-lm", "-o", executable,
    ])


def check_symbol(production):
    rows = run(["/usr/bin/nm", "--defined-only", production]).decode().splitlines()
    if not any(row.split()[-1:] == [NAME] for row in rows):
        raise ValueError(f"Missing original symbol {NAME}")
    print(NAME)


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
        check_symbol(args.object)
        return
    fixtures = json.loads(args.fixtures.read_text())
    if args.mode in ("native", "canonical"):
        if generate() != fixtures:
            raise ValueError("Fresh ARM observations differ from sealed fixtures")
        print(f"{len(fixtures['cases'])} original ARM observations matched")
        if args.mode == "native":
            return
    cases = fixtures["cases"]
    payload = "".join(f"{route} {seed}\n" for route, seed in (case["input"] for case in cases))
    actual = run([args.exe], payload.encode()).decode().splitlines()
    expected = [str(case["expected"]) for case in cases]
    if actual != expected:
        raise ValueError(f"Portable replay differed: {actual!r} vs {expected!r}")
    print(f"{len(actual)} ARM differential cases passed")
    if args.mode == "canonical":
        if args.out is None or args.integration is None:
            parser.error("canonical requires --integration and --out")
        integration = json.loads(args.integration.read_text())
        if not isinstance(integration, dict) or not integration:
            parser.error("expected nonempty integration receipt")
        check_symbol(args.object)
        receipt = {
            "behavior_validated": True, "domain": DOMAIN,
            "cases": len(cases), "elf_sha256": fixtures["elf_sha256"],
            "ranges": fixtures["ranges"], "vtable": fixtures["vtable"],
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
