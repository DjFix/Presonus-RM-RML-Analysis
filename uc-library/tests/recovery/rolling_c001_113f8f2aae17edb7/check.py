"""Build locally or check a CMake-built callback replay and original symbol."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from native import SYMBOL

TASK = "rolling_c001_113f8f2aae17edb7"
TEST = Path(__file__).resolve().parent
LIBRARY = Path("uc-library")
HEADER = LIBRARY / "include/presonus/mixer/AVBCascadeManager.hpp"
SOURCE = LIBRARY / "src/Presonus/Mixer/AVBCascadeManager.cpp"
ITEM = LIBRARY / "include/presonus/uc/NetworkItem.hpp"
DRIVER = TEST / "Replay.cpp"
CORE = Path("third_party/ccl-framework/core/public")
SCRATCH = Path("temp/recovery-work") / (TASK + "-local")
BUILD = Path("/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01")
SDK = BUILD / "upstream-core/sdk"
FORMATTER = LIBRARY / ".venv/bin/clang-format"
DOMAIN = (
    "Three direct calls with null, the selected item and another live network item. "
    "ARM execution restores the stack, preserves r0–r11 and accesses only its stack "
    "frame. Receiver and argument bytes, selected item and borrowed component "
    "identity remain unchanged. No boundary calls occur through receiver destruction."
)
LIMITS = [
    "Portable void nonstatic nonvirtual declaration. ARM leaves r0 unchanged, "
    "which does not establish the original return type.",
    "The recorded vtable slot and adjusting thunk support member virtual dispatch "
    "in the original, but the original declaring/overriding interface and dispatch "
    "layout remain unresolved. Portable code supplies a direct member call only.",
    "Original receiver initialization, native thunk invocation, ARM class layout, "
    "binary interoperability and hardware behavior remain outside this replay.",
]


def run(command):
    return subprocess.check_output([str(arg) for arg in command], text=True)


def stamp():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def binding(path):
    return {"path": str(path), "sha256": digest(path)}


def local_compile():
    SCRATCH.mkdir(parents=True, exist_ok=True)
    flags = ["c++", "-std=c++17", "-O2", "-fno-lto", "-fno-rtti", "-pthread",
             "-Ulinux", "-Iuc-library/include", "-isystem", SDK / "include/presonus-core-5"]
    obj = SCRATCH / "AVBCascadeManager.o"
    run([*flags, "-c", SOURCE, "-o", obj])
    libs = [SDK / "lib" / name for name in
            ("libcorelib.a", "libpresonus_core_allocator.a", "libpresonus_png.a", "libpresonus_zlib.a")]
    run([*flags, DRIVER, obj, BUILD / "libpresonus_uc.a", *libs, "-lssl", "-lcrypto",
         "-ldl", "-lm", "-o", SCRATCH / "replay"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("format", "compile", "symbols", "replay"))
    parser.add_argument("--exe", type=Path, default=SCRATCH / "replay")
    parser.add_argument("--object", type=Path, default=SCRATCH / "AVBCascadeManager.o")
    parser.add_argument("--fixtures", type=Path, default=TEST / "fixtures.json")
    parser.add_argument("--integration", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    start = stamp()
    run([FORMATTER, "--style=file", "--fallback-style=LLVM", "--dry-run", "--Werror",
         HEADER, SOURCE, DRIVER])
    if args.mode == "format":
        return
    if args.mode == "compile":
        if Path(run(["git", "rev-parse", "--show-toplevel"]).strip()) != Path.cwd():
            raise ValueError("Local build must run at repository root")
        local_compile()
        return
    symbols = {line.split()[-1] for line in run(["nm", "--defined-only", args.object]).splitlines()
               if len(line.split()) >= 3}
    if SYMBOL not in symbols:
        raise ValueError(f"Missing exact production symbol {SYMBOL}")
    if args.mode == "symbols":
        print(SYMBOL)
        return

    native = json.loads(args.fixtures.read_text())
    results = run([args.exe.resolve()]).splitlines()
    expected = ["unchanged" if case["state_unchanged"] else "changed"
                for case in native["cases"]]
    if results != [*expected, "portable receiver lifecycle completed"]:
        raise ValueError(f"Portable replay mismatch: {results}")
    sources = {str(path.relative_to(LIBRARY)): digest(path)
               for path in (HEADER, SOURCE, ITEM)}
    repository_sources = {str(path): digest(path) for path in
                          (CORE / "corestringbuffer.h",)}
    row = dict(original_elf_sha256=native["elf_sha256"], mangled=SYMBOL,
               sources=sources, repository_sources=repository_sources, domain=DOMAIN,
               cpp_compiled=True, mangling_namespace_checked=True, portable_ready=False,
               declaration_uncertainties=LIMITS)
    proof = dict(task_id=TASK, start_utc=start, end_utc=stamp(), argv=sys.argv,
                 cpp_differential_passed=True, compiled_mangled_names_matched=True,
                 format_check_passed=True, formatter=run([FORMATTER, "--version"]).strip(),
                 compiler=run(["c++", "--version"]).splitlines()[0], case_count=len(expected),
                 native=native, portable_rows=results, functions=[row], mangled_names=[SYMBOL],
                 proposed_readiness={"ready": [], "pending": [row]}, validation_domain=DOMAIN,
                 checker=binding(TEST / "check.py"), native_producer=binding(TEST / "native.py"),
                 fixture=binding(args.fixtures), production=binding(args.object),
                 executable=binding(args.exe), driver=binding(DRIVER), limitations=LIMITS,
                 original_function_verified=False, hardware_verified=False)
    if args.integration:
        proof["integration"] = binding(args.integration)
    else:
        proof["local_provider"] = binding(SDK / "lib/libcorelib.a")
    if args.out:
        args.out.write_text(json.dumps(proof, indent=2) + "\n")
    print(f"{TASK}: compared {len(expected)} cases and checked portable receiver lifecycle")


if __name__ == "__main__":
    main()
