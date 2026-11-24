"""Compile and compare the portable touch decoder against ARM observations."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

TASK = "r_independent_54c3a29f1c"
LIBRARY = Path("uc-library")
TEST = LIBRARY / "tests/recovery" / TASK
HEADER = LIBRARY / "include/presonus/surface/DisplayManager.hpp"
SOURCE = LIBRARY / "src/Presonus/TouchInputEvent.cpp"
UART = LIBRARY / "src/Presonus/UARTMessageHandler.cpp"
UART_HEADERS = [LIBRARY / "include/presonus/panel" / name
                for name in ("uart_message.hpp", "uart_message_handler.hpp")]
DRIVER = TEST / "Replay.cpp"
SCRATCH = Path("temp/recovery-work") / (TASK + "-local")
BUILD = Path("/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01")
SDK = BUILD / "upstream-core/sdk"
FORMATTER = LIBRARY / ".venv/bin/clang-format"
SYMBOL = "_ZN8Presonus15TouchInputEvent7fromMsgER16Touchscreen_Type"
CORE = Path("third_party/ccl-framework/core")
CORE_HEADERS = ["portable/gui/coreview.h", "public/corevector.h",
                "portable/coretypeinfo.h", "public/corestringbuffer.h"]
DOMAIN = (
    "Per ELF, 1024 direct ARM invocations diverge across all 256 packed status "
    "values, all 256 tags and selected paired low coordinate bytes. Compare four "
    "receiver fields, frame preservation, native input/receiver sentinels and "
    "exact native memory footprints. Portable U, z and T tags use live UART "
    "dispatch through one touchscreen callback. Other tags use direct calls."
)
LIMITS = [
    "The original return type is unresolved. Portable fromMsg is a void member.",
    "Touchscreen_Type remains opaque. The bound UART record supplies four readable "
    "bytes of live storage. Native struct and class layouts and ARM binary "
    "interoperability remain unresolved.",
    "Native execution covers the isolated method and its ARM stack frame. Portable "
    "UART exercises the existing dispatcher with an observer and does not establish "
    "native dispatch, hardware behavior or overlapped input and receiver semantics.",
]


def run(argv, data=None):
    return subprocess.check_output([str(arg) for arg in argv], input=data, text=True)


def stamp():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bind(path):
    return {"path": str(path), "sha256": digest(path)}


def local_compile():
    if Path(run(["git", "rev-parse", "--show-toplevel"]).strip()) != Path.cwd():
        raise ValueError("Local build must run at the assigned repository root")
    SCRATCH.mkdir(parents=True, exist_ok=True)
    flags = ["c++", "-std=c++17", "-O2", "-fno-rtti", "-Ulinux", "-Iuc-library/include",
             "-isystem", SDK / "include/presonus-core-5"]
    obj = SCRATCH / "TouchInputEvent.o"
    run([*flags, "-c", SOURCE, "-o", obj])
    libs = [SDK / "lib" / name for name in
            ("libcorelib.a", "libpresonus_core_allocator.a", "libpresonus_png.a", "libpresonus_zlib.a")]
    run([*flags, DRIVER, UART, obj, *libs, "-lssl", "-lcrypto", "-lpthread",
         "-ldl", "-lm", "-o", SCRATCH / "replay"])


def compare(executable, original):
    cases = original["cases"]
    frames = [frame for frame, _ in cases]
    if len(cases) != 1024 or {frame[0] for frame in frames} != set(range(256)):
        raise ValueError("Missing tag cases")
    for tag in (0x55, 0x7a, 0x54):
        if {frame[3] for frame in frames if frame[0] == tag} != set(range(256)):
            raise ValueError("Missing packed status cases")
    data = "".join(" ".join(map(str, frame)) + "\n" for frame in frames)
    actual = [list(map(int, line.split())) for line in run([executable.resolve()], data).splitlines()]
    if actual != [observed for _, observed in cases]:
        raise ValueError(f"Portable comparison failed for {original['elf_sha256']}")
    return len(actual)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("format", "compile", "symbols", "replay"))
    parser.add_argument("--exe", type=Path, default=SCRATCH / "replay")
    parser.add_argument("--object", type=Path, default=SCRATCH / "TouchInputEvent.o")
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
        local_compile()
        return
    symbols = [line.split()[-1] for line in run(["nm", "--defined-only", args.object]).splitlines()
               if len(line.split()) >= 3]
    if symbols.count(SYMBOL) != 1:
        raise ValueError(f"Expected one exact production symbol {SYMBOL}")
    if args.mode == "symbols":
        print(SYMBOL)
        return

    fixture = json.loads(args.fixtures.read_text())
    sources = {str(path.relative_to(LIBRARY)): digest(path)
               for path in (HEADER, SOURCE, UART, *UART_HEADERS)}
    repository_sources = {str(CORE / name): digest(CORE / name) for name in CORE_HEADERS}
    rows = []
    for original in fixture["originals"]:
        if original["mangled"] != SYMBOL:
            raise ValueError("Fixture symbol differs from production symbol")
        count = compare(args.exe, original)
        native = {key: val for key, val in original.items() if key != "cases"}
        rows.append(dict(original_elf_sha256=original["elf_sha256"], mangled=SYMBOL,
                         domain=DOMAIN, sources=sources, repository_sources=repository_sources,
                         cpp_compiled=True, mangling_namespace_checked=True, portable_ready=False,
                         declaration_uncertainties=LIMITS, native=native,
                         native_case_count=count, portable_case_count=count))
    proof = dict(task_id=TASK, start_utc=start, end_utc=stamp(), argv=sys.argv,
                 cpp_differential_passed=True, compiled_mangled_names_matched=True,
                 format_check_passed=True, formatter=run([FORMATTER, "--version"]).strip(),
                 compiler=run(["c++", "--version"]).splitlines()[0], validation_domain=DOMAIN,
                 unicorn=fixture["unicorn"], proposed_readiness={"ready": [], "pending": rows},
                 checker=bind(TEST / "check.py"), native_producer=bind(TEST / "native.py"),
                 fixture=bind(args.fixtures), production=bind(args.object), executable=bind(args.exe),
                 driver=bind(DRIVER), limitations=LIMITS, original_function_verified=False,
                 hardware_verified=False)
    if args.integration:
        proof["integration"] = bind(args.integration)
    else:
        proof["local_provider"] = bind(SDK / "lib/libcorelib.a")
    if args.out:
        args.out.write_text(json.dumps(proof, indent=2) + "\n")
    print(f"{TASK}: compared {sum(row['portable_case_count'] for row in rows)} cases across both ELFs")


if __name__ == "__main__":
    main()
