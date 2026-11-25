"""Compile and compare a local Linux LCDManager source port with ARM fixtures."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
PRODUCTION = ROOT / "uc-library/src/Presonus/Panel"
SCRATCH = ROOT / "temp/recovery-work/lcdmanager-local"
SOURCES = ("include/presonus/panel/LCDManager.hpp", "src/Presonus/Panel/LCDManager.cpp")
COMPONENT_SOURCES = ("include/presonus/panel/LCDComponent.hpp", "src/Presonus/Panel/LCDComponent.cpp")
CORE = "third_party/ccl-framework/core/portable/"
CORE_SOURCES = (CORE + "coresingleton.h", CORE + "coresingleton.cpp")
COMPONENT_CORE = (CORE + "corecomponent.h", CORE + "corecomponent.cpp")
LIMITATIONS = [
    "Portable C++ source behavior only. Original ARM C++ layouts, vtable equivalence, hardware and application shutdown are outside the validation domain.",
    "Native Core idle runs to the verified call boundary; portable replay uses pinned Core Component::onIdle and an observer child. Other native delegate types and loadPage are excluded.",
    "Native D0 reaches verified _ZdlPv and revokes the guest allocation at that boundary. The ARM libc allocator is excluded. The Linux deleting destructor calls real receiver deallocation through virtual delete.",
]
UNCERTAINTY = "The original return declaration of doIdle() is unencoded; ARM call-through and ignored register residue support the portable void operation without establishing that declaration."
DOMAINS = {
    "idle": "Each firmware verifies the native null branch and typed ILCDDelegate slot, receiver adjustment and actual LCDComponent dispatch to the Core idle boundary, once and twice. Linux compares initialized borrowed delegates and observes children of the real pinned CCL component. Existing lookup-only and Book routes are exercised.",
    "D1": "Each firmware checks native complete destruction with a null singleton, another manager, and the target manager. Linux placement destruction tests corresponding conditional reset of the real CCL singleton with a borrowed live delegate, no receiver deallocation and no delegate callback.",
    "D0": "Each firmware checks native deleting destruction with a null singleton, another manager, and the target manager. Linux virtual destruction checks live Core singleton state at actual receiver deallocation, exactly one delete and no borrowed delegate callback.",
}

SYMBOLS = {
    "idle": "_ZN8Presonus5Panel10LCDManager6doIdleEv",
    "D1": "_ZN8Presonus5Panel10LCDManagerD1Ev",
    "D0": "_ZN8Presonus5Panel10LCDManagerD0Ev",
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def capture(argv):
    print(json.dumps([str(arg) for arg in argv]), flush=True)
    return subprocess.check_output(argv, cwd=ROOT, text=True)


def compile_replay(args):
    scratch = SCRATCH / args.variant
    scratch.mkdir(parents=True, exist_ok=True)
    replay_name = "do_idle" if args.variant == "idle" else "complete_destroy"
    replay = Path(__file__).resolve().parent.parent / f"sqlite02_lcdmanager_{replay_name}" / "Replay.cpp"
    flags = ["c++", "-std=c++20", "-O2", "-Ulinux", "-UNDEBUG",
             "-DCORE_USE_OPENSSL=1", "-DPRESONUS_HAS_UPSTREAM_CORE=1",
             "-ffunction-sections", "-fdata-sections", "-I", "uc-library/include",
             "-isystem", args.sdk / "include/presonus-core-5"]
    objects = []
    for source in (PRODUCTION / "LCDManager.cpp", PRODUCTION / "LCDComponent.cpp", replay):
        obj = scratch / f"{source.stem}.o"
        capture([*flags, "-MD", "-c", source, "-o", obj])
        objects.append(obj)
    libraries = [args.sdk / "lib" / name for name in (
        "libcorelib.a", "libpresonus_core_allocator.a")]
    output = capture(["c++", "-Wl,--gc-sections", *objects, *libraries,
                      "-lssl", "-lcrypto", "-ldl", "-lpthread", "-o", args.exe])
    print(output, end="")
    print(json.dumps({str(path): digest(path) for path in libraries}))


def verify_symbols(args):
    output = capture(["nm", "--defined-only", args.object])
    names = [line.split()[-1] for line in output.splitlines() if line.strip()]
    assert names.count(SYMBOLS[args.variant]) == 1
    print(json.dumps({"symbol": SYMBOLS[args.variant], "object_sha256": digest(args.object)}))
    return SYMBOLS[args.variant]


def replay(args):
    assert digest(args.fixtures) == args.fixture_sha256
    data = json.loads(args.fixtures.read_text())
    assert {obs["original"]["role"] for obs in data["observations"]} == {"client", "server"}
    observed = []
    for obs in data["observations"]:
        assert obs["original"]["mangled"] == SYMBOLS[args.variant]
        for case in obs["cases"]:
            prefix = [] if args.variant == "idle" else [args.variant]
            output = json.loads(capture([args.exe.resolve(), *prefix, case["case"]]))
            assert output == case["portable"], (args.variant, case["case"], output)
            observed.append(dict(elf_sha256=obs["original"]["elf"], case=case["case"], observed=output))
    assert len(observed) == 6
    symbol = verify_symbols(args)
    fixture = dict(path=str(args.fixtures), sha256=args.fixture_sha256)
    print(json.dumps(dict(passed=True, case_count=len(observed), fixture=fixture,
                          executable_sha256=digest(args.exe))))
    if args.out is not None:
        write_proof(args, data, observed, fixture, symbol)


def write_proof(args, data, observed, fixture, symbol):
    is_idle = args.variant == "idle"
    base = PRODUCTION.parents[2]
    source_paths = SOURCES + (COMPONENT_SOURCES if is_idle else ())
    core_paths = CORE_SOURCES + (COMPONENT_CORE if is_idle else ())
    sources = {path: digest(base / path) for path in source_paths}
    repository_sources = {path: digest(ROOT / path) for path in core_paths}
    paths = [str(base / path) for path in SOURCES]
    replay = Path(__file__).resolve().parent.parent / (
        "sqlite02_lcdmanager_do_idle" if is_idle else "sqlite02_lcdmanager_complete_destroy"
    ) / "Replay.cpp"
    formatter = ["uc-library/.venv/bin/clang-format"]
    format_argv = [*formatter, "--style=file", "--fallback-style=LLVM", "--dry-run",
                   "--Werror", *paths, str(replay)]
    capture(format_argv)
    formatter_version = capture([*formatter, "--version"]).strip()
    domain = DOMAINS[args.variant]
    ready = not is_idle
    functions = []
    for obs in data["observations"]:
        original = obs["original"]
        row = dict(original_elf_sha256=original["elf"], mangled=original["mangled"],
                   original_address=original["address"], sources=sources,
                   repository_sources=repository_sources, domain=domain,
                   cpp_compiled=True, mangling_namespace_checked=True,
                   behavior_validation_passed=True, portable_ready=ready, success=True)
        if is_idle:
            row["declaration_uncertainties"] = [UNCERTAINTY]
        functions.append(row)
    integration = None
    if args.integration != "none":
        integration_path = Path(args.integration)
        assert json.loads(integration_path.read_text())["ctest_passed"] is True
        integration = dict(path=str(integration_path), sha256=digest(integration_path))
    folder = Path(__file__).resolve().parent
    doc = dict(version=1, task_id=args.fixtures.parent.name, success=True, domain=domain,
               limitations=LIMITATIONS + ([UNCERTAINTY] if is_idle else []), functions=functions,
               proposed_readiness={"ready": functions if ready else [],
                                   "pending": [] if ready else functions},
               cpp_differential_passed=True, portable_ready=ready, cpp_compiled=True,
               mangling_namespace_checked=True, format_check_passed=True,
               behavior_validation_passed=True, formatter_version=formatter_version,
               format_argv=format_argv, fixture=fixture, integration=integration,
               formatted_sources={str(Path(path).relative_to(ROOT)): digest(Path(path))
                                  for path in [*paths, str(replay)]},
               compiled_mangled_names_matched=True, mangled_names=[symbol],
               object=dict(path=str(args.object), sha256=digest(args.object)),
               executable=dict(path=str(args.exe), sha256=digest(args.exe)),
               native_observations=data, portable_observations=observed,
               producers={str(path.relative_to(ROOT)): digest(path)
                          for path in (folder / "native.py", Path(__file__).resolve(), replay)},
               provider_hashes=repository_sources, command=sys.argv)
    args.out.write_text(json.dumps(doc, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("compile", "symbols", "replay"))
    parser.add_argument("--variant", choices=tuple(SYMBOLS), required=True)
    parser.add_argument("--sdk", type=Path)
    parser.add_argument("--exe", type=Path)
    parser.add_argument("--object", type=Path)
    parser.add_argument("--fixtures", type=Path)
    parser.add_argument("--fixture-sha256")
    parser.add_argument("--integration", default="none")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    {"compile": compile_replay, "symbols": verify_symbols, "replay": replay}[args.phase](args)


if __name__ == "__main__":
    main()
