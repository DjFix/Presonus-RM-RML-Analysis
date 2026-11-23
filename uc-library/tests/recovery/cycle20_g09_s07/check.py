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
SCRATCH = ROOT / "temp/recovery-work/actual07-g09" / TESTS.name
PROVIDERS = Path("/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling200-02/agent-repos04/channel_filters25/temp/recovery-work/g05-actual07-wave01/archives")
ARCHIVES = {
    "libpresonus_rm_components.a": "1570123244b38933e968d41d98325c46ad44a5214d7b1d382de8093a2f0f0ef6",
    "libcorelib.a": "3c4f0825acb529fda135587b7ff5cb92ca0100bb417a20c034d3fdef80a93e0c",
    "libpresonus_core_allocator.a": "69892fbcec9a50a140462982073c686a67ca4763dfb5dfa190534d022b78a40d",
}
FILES = [
    f"uc-library/include/presonus/mixer/{CLASS_NAME}.hpp",
    f"uc-library/src/Presonus/Mixer/{CLASS_NAME}.cpp",
    str(TESTS / "Replay.cpp"),
]
DOMAIN = (
    "RM 13731 exact FXComponent::mapIDs direct and original FX vtable paths "
    "over seven signed selectors including int32 extrema. Native keeps "
    "receiver bytes unchanged with stack-only writes and returns all-ones r0. "
    "Reverb's separate original table entry is checked without executing its body. "
    "Portable typed CCL receiver reproduces uint32 result bits and unchanged "
    "state and uses a separate test override to check virtual dispatch."
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
    for name, expected in ARCHIVES.items():
        provider = PROVIDERS / name
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
            "reverb_vtable": fixtures["reverb_table"],
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
