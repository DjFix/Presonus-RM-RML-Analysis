"""Check the source port against the sealed original ARM observations."""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess

TASK = "rolling_next200_class_09"
TEST = Path("uc-library/tests/recovery") / TASK
SCRATCH = Path("temp/recovery-work") / (TASK + "-local")
SOURCES = (
    Path("uc-library/include/presonus/mixer/NetworkSetupComponent.hpp"),
    Path("uc-library/src/Presonus/Mixer/NetworkSetupComponent.cpp"),
    TEST / "Replay.cpp",
)
CORE = Path("third_party/ccl-framework/core")
CORE_FILES = (
    CORE / "portable/corecomponent.h", CORE / "portable/corecomponent.cpp",
    CORE / "public/corevector.h", CORE / "public/corestringbuffer.h",
)
FORMAT = "uc-library/.venv/bin/clang-format"
BUILD = Path("/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01")
SDK = BUILD / "upstream-core/sdk"
ARCHIVES = [
    BUILD / "libpresonus_rm_components.a",
    *(SDK / "lib" / f"lib{name}.a" for name in
      ("corelib", "presonus_core_allocator", "presonus_png", "presonus_zlib")),
]
MANGLED = "_ZN8Presonus5Mixer21NetworkSetupComponent15onServerChangedEPNS_2UC11NetworkItemE"
DOMAIN = (
    "Two independently emulated original ARM cases with a writable stack, "
    "synthetic receiver/item sentinel pages and null or nonnull item pointer. "
    "The exact original body preserved receiver/item memory, SP, FP and its two "
    "incoming arguments, with memory accesses confined to the stack frame. "
    "The C++ replay exercised empty and populated source-port selection state "
    "using pinned CCL and a fail-on-use application service boundary."
)
LIMITATIONS = [
    "Original return declaration unresolved. Portable callback uses void.",
    "Direct body behavior only. Original virtual dispatch, thunk, inheritance, "
    "layout, constructors, destructors, ARM interoperability and hardware are outside scope.",
]


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def run(*argv):
    argv = list(map(str, argv))
    print(" ".join(argv), flush=True)
    return subprocess.check_output(argv, text=True)


def compile_local(exe, obj):
    SCRATCH.mkdir(parents=True, exist_ok=True)
    common = [
        "/usr/bin/c++", "-std=c++17", "-O2", "-fno-rtti", "-pthread", "-Ulinux",
        "-DPRESONUS_HAS_UPSTREAM_CORE=1", "-DCORE_USE_OPENSSL=1", "-DNDEBUG=1",
        "-Iuc-library/include", "-isystem", SDK / "include/presonus-core-5",
    ]
    run(*common, "-ffunction-sections", "-fdata-sections", "-c", SOURCES[1], "-o", obj)
    run(*common, SOURCES[2], obj, "-Wl,--gc-sections", "-Wl,--start-group",
        *ARCHIVES, "-Wl,--end-group", "-ldl", "-lm", "-o", exe)


def binding(path):
    return {"path": str(path), "sha256": digest(path)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("format", "compile", "symbols", "replay"))
    parser.add_argument("--exe", type=Path, default=SCRATCH / "Replay")
    parser.add_argument("--object", type=Path, default=SCRATCH / "NetworkSetupComponent.o")
    parser.add_argument("--fixture", type=Path, default=TEST / "fixtures.json")
    parser.add_argument("--integration", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    started = datetime.now(timezone.utc).isoformat()
    if args.mode in ("format", "replay"):
        run(FORMAT, "--style=file", "--fallback-style=LLVM", "--dry-run", "--Werror", *SOURCES)
    if args.mode == "format":
        return
    if args.mode == "compile":
        compile_local(args.exe, args.object)
        return
    definitions = [row.split() for row in run("nm", "--defined-only", args.object).splitlines()]
    symbol, = [row for row in definitions if row and row[-1] == MANGLED]
    assert symbol[-2] in ("T", "W")
    print(" ".join(symbol))
    if args.mode == "symbols":
        return
    original = json.loads(args.fixture.read_text())
    assert original["mangled"] == MANGLED
    assert {case["has_item"] for case in original["cases"]} == {True, False}
    observed = []
    for case in original["cases"]:
        mode = "item" if case["has_item"] else "null"
        actual = json.loads(run(args.exe.resolve(), mode))
        expected = {key: case[key] for key in ("receiver_unchanged", "item_unchanged")}
        if actual != expected or not all(actual.values()):
            raise ValueError(f"{mode} comparison failed: {actual} != {expected}")
        observed.append({"mode": mode, **actual})
    sources = {str(path.relative_to("uc-library")): digest(path) for path in SOURCES}
    repository_sources = {str(path): digest(path) for path in CORE_FILES}
    row = dict(
        original_elf_sha256=original["elf_sha256"], mangled=MANGLED,
        original_address=original["address"], sources=sources, repository_sources=repository_sources,
        cpp_compiled=True, mangling_namespace_checked=True, portable_ready=False,
        domain=DOMAIN, declaration_uncertainties=LIMITATIONS[:1],
    )
    proof = dict(
        version=1, task_id=TASK, domain=DOMAIN, limitations=LIMITATIONS,
        start_utc=started, end_utc=datetime.now(timezone.utc).isoformat(),
        format_check_passed=True, cpp_compiled=True, mangling_namespace_checked=True,
        portable_ready=False, behavior_validation_passed=True,
        sources=sources, repository_sources=repository_sources,
        native=original, portable_observations=observed, case_count=len(observed),
        fixture=binding(args.fixture), executable=binding(args.exe),
        object=binding(args.object), symbols=" ".join(symbol),
        producers=[binding(TEST / name) for name in ("check.py", "native.py")],
        versions={
            "formatter": run(FORMAT, "--version").strip(),
            "compiler": run("/usr/bin/c++", "--version").splitlines()[0],
        },
        proposed_readiness={"ready": [], "pending": [row]},
        canonical_binding_pending=args.integration is None,
    )
    if args.integration is not None:
        proof["integration"] = binding(args.integration)
    else:
        proof["local_archive_bindings"] = [binding(path) for path in ARCHIVES]
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(proof, indent=2) + "\n")
    print(f"PASS {len(observed)} original ARM versus C++ callback cases")


if __name__ == "__main__":
    main()
