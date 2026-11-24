"""Compile and compare the portable onNetworkItemReleased method with original ARM observations."""

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

import native

TASK = "rolling_c001_26fa307bec1ec7d8"
TEST = Path("uc-library/tests/recovery/rolling_c001_26fa307bec1ec7d8")
SCRATCH = Path("temp/recovery-work/rolling_c001_26fa307bec1ec7d8-local")
LIBRARY = Path("uc-library")
SOURCES = (
    LIBRARY / "include/presonus/mixer/NetworkSetupComponent.hpp",
    LIBRARY / "src/Presonus/Mixer/NetworkSetupComponent.cpp",
    TEST / "Replay.cpp",
)
CORE = Path("third_party/ccl-framework/core")
CORE_FILES = (
    CORE / "public/corevector.h",
    CORE / "public/corestringbuffer.h",
    CORE / "portable/corecomponent.h",
        CORE / "portable/corecomponent.h",
    CORE / "system/coredebug.h",
)
FORMATTER = LIBRARY / ".venv/bin/clang-format"
BUILD = Path("/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01")
SDK = BUILD / "upstream-core/sdk"
ARCHIVES = (
    BUILD / "libpresonus_rm_components.a",
    *(SDK / "lib" / f"lib{name}.a" for name in
      ("corelib", "presonus_core_allocator", "presonus_png", "presonus_zlib")),
)
DOMAIN = 'Eight direct invocations across four payload sentinels and null or nonnull NetworkItem arguments. ARM trace checks return control, register preservation from r1 through r11, and writes confined to the stack frame. C++ replay compares payload and selected state sentinels and rejects service calls.'
LIMITATIONS = ['Portable declaration is a nonvirtual void member. Original return spelling, virtual declaration, hierarchy and override details remain unresolved.', 'Native receiver and opaque argument memory use sentinels. Original object layout, dispatch via thunks, ARM ABI interoperability and hardware are outside the replay.']


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def binding(path):
    return {"path": str(path), "sha256": digest(path)}


def run(*argv):
    command = [str(argument) for argument in argv]
    print(" ".join(command), flush=True)
    return subprocess.check_output(command, text=True)


def compile_local(obj, exe):
    SCRATCH.mkdir(parents=True, exist_ok=True)
    flags = (
        "/usr/bin/c++", "-std=c++17", "-O2", "-pthread", "-Ulinux",
        "-DPRESONUS_HAS_UPSTREAM_CORE=1", "-DCORE_USE_OPENSSL=1", "-DNDEBUG=1",
        "-Iuc-library/include", "-isystem", SDK / "include/presonus-core-5",
        "-ffunction-sections", "-fdata-sections",
    )
    run(*flags, "-c", SOURCES[1], "-o", obj)
    run(*flags, SOURCES[2], obj, "-Wl,--gc-sections", "-Wl,--start-group",
        *ARCHIVES, "-Wl,--end-group", "-ldl", "-lm", "-o", exe)


def exact_symbol(obj):
    definitions = run("nm", "--defined-only", obj).splitlines()
    matches = [row for row in definitions if row.split()[-1:] == [native.MANGLED]]
    if len(matches) != 1 or matches[0].split()[-2] not in {"T", "W"}:
        raise ValueError("Exact scoped ELF definition missing from object")
    print(matches[0])
    return matches[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("format", "compile", "symbols", "replay"))
    parser.add_argument("--fixture", type=Path, default=TEST / "fixtures.json")
    parser.add_argument("--exe", type=Path, default=SCRATCH / "Replay")
    parser.add_argument("--object", type=Path, default=SCRATCH / "Owner.o")
    parser.add_argument("--integration", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    start = datetime.now(timezone.utc).isoformat()
    if args.mode in {"format", "replay"}:
        run(FORMATTER, "--style=file", "--fallback-style=LLVM", "--dry-run", "--Werror", *SOURCES)
    if args.mode == "format":
        return
    if args.mode == "compile":
        compile_local(args.object, args.exe)
        return
    symbol = exact_symbol(args.object)
    if args.mode == "symbols":
        return
    fixture = json.loads(args.fixture.read_text())
    if (fixture["mangled"], fixture["elf_sha256"], fixture["range_sha256"]) != (
        native.MANGLED, native.ELF_HASH, native.BODY_HASH
    ):
        raise ValueError("Fixture byte range identity mismatch")
    original = fixture["cases"]
    if [tuple(case[:2]) for case in original] != [
        (tag, null) for tag in range(4) for null in (0, 1)
    ]:
        raise ValueError("Fixture does not cover the declared seed domain")
    if any(case[2:] != [0, 0x31, case[0], 0x79] for case in original):
        raise ValueError("Fixture has an unexpected mutation")
    observed = [list(map(int, line.split())) for line in run(args.exe.resolve()).splitlines()]
    if observed != original:
        raise ValueError("Original ARM and portable C++ observations differ")
    sources = {str(path.relative_to(LIBRARY)): digest(path) for path in SOURCES}
    repository_sources = {str(path): digest(path) for path in CORE_FILES}
    row = {
        "original_elf_sha256": native.ELF_HASH, "mangled": native.MANGLED,
        "original_address": native.ADDRESS, "cpp_compiled": True,
        "mangling_namespace_checked": True, "portable_ready": False,
        "sources": sources, "repository_sources": repository_sources,
        "domain": DOMAIN, "declaration_uncertainties": LIMITATIONS,
    }
    proof = {
        "version": 1, "task_id": TASK, "start_utc": start, "argv": sys.argv,
        "success": True, "format_check_passed": True, "behavior_validation_passed": True,
        **row, "limitations": LIMITATIONS, "functions": [dict(row, success=True)],
        "proposed_readiness": {"ready": [], "pending": [row]},
        "native": {key: value for key, value in fixture.items() if key != "cases"},
        "native_case_count": len(original), "portable_case_count": len(observed),
        "fixture": binding(args.fixture), "object": binding(args.object),
        "executable": binding(args.exe), "symbol": symbol,
        "producers": [binding(TEST / name) for name in ("native.py", "check.py")],
        "formatter_version": run(FORMATTER, "--version").strip(),
        "compiler_version": run("/usr/bin/c++", "--version").splitlines()[0],
        "canonical_binding_pending": args.integration is None,
        "end_utc": datetime.now(timezone.utc).isoformat(),
    }
    if args.integration is None:
        proof["local_archive_bindings"] = [binding(path) for path in ARCHIVES]
    else:
        proof["integration"] = binding(args.integration)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(proof, indent=2) + "\n")
    print(f"PASS {len(observed)} original ARM versus portable C++ observations")


if __name__ == "__main__":
    main()
