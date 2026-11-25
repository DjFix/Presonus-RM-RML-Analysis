"""Compile and compare one PanControl destructor variant against its ARM oracle."""
import argparse
import json
from pathlib import Path
import shlex
import subprocess
import sys

import native

TEST = Path(__file__).resolve().parent.relative_to(native.ROOT)
SOURCE = (Path("uc-library/src/Presonus/PanControl.cpp"),
          Path("uc-library/src/Presonus/PanControlBindings.cpp"),
          Path("uc-library/include/presonus/PanControl.hpp"))
REPLAY = TEST / "Replay.cpp"
FORMATTER = "uc-library/.venv/bin/clang-format"
CXX = ["/usr/bin/c++", "-std=c++17", "-O3", "-DNDEBUG", "-DCORE_USE_OPENSSL=1",
       "-DPRESONUS_HAS_UPSTREAM_CORE=1", "-fno-rtti", "-Wall", "-Wextra",
       "-Wno-multichar", "-Iuc-library/include", "-isystem", "third_party/ccl-framework",
       "-Ulinux", "-pthread", "-ffunction-sections", "-fdata-sections"]
PROJECT = Path("/home/rs/projects/opencs/ai-line-analysis")
BUILD = PROJECT / "temp/core-upstream/root-integration-01"
CORE = BUILD / "upstream-core/sdk/lib"
EXTERNAL = PROJECT / "temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu"
LIBRARIES = [BUILD / "libpresonus_cs18_components.a", CORE / "libcorelib.a",
             CORE / "libpresonus_core_allocator.a", CORE / "libpresonus_png.a",
             CORE / "libpresonus_zlib.a", Path("/usr/lib/x86_64-linux-gnu/libssl.so"),
             Path("/usr/lib/x86_64-linux-gnu/libcrypto.so"), EXTERNAL / "libdns_sd.so",
             BUILD / "private-glibc29-provider/libpresonus_private_glibc29.a"]
WRAPS = ["-Wl,--wrap=" + symbol for symbol in ("_ZdlPv", "_ZdlPvm", native.REMOVE, native.ADD)]
DOMAIN = (
    "Nine cases per independently executed original ARM destructor with absent, ordered full and "
    "partial registrations, replacements, real destruction notifications and absent native registrations "
    "for the host-only non-observing borrow path. Check typed observer argument and surviving CCL "
    "notifications, bitmap release before base cleanup and actual receiver deallocation for D0. "
    "Host D2 runs via a real derived destructor, D1 via explicit complete teardown and D0 via virtual delete."
)
LIMITATIONS = [
    "Native CCL call boundaries model the observer list and dispatch; the portable replay "
    "uses real pinned Parameter, ValueBar bitmap references and Control implementation.",
    "The native _ZdlPv PLT binding is verified and the hook releases guest receiver memory. "
    "Host virtual deletion calls the real allocator. Native allocator internals and "
    "exception paths are outside the domain.",
    "Portable application lifetime adaptation only. No original layout, ARM32 ABI, or "
    "hardware claim. The borrow-only adapter and notification bookkeeping are portable.",
]


def binding(path):
    return dict(path=str(path), sha256=native.digest(Path(path).read_bytes()))


def run(argv, **kwargs):
    argv = list(map(str, argv))
    print(json.dumps(argv), flush=True)
    return subprocess.run(argv, cwd=native.ROOT, text=True, check=True,
                          stdout=subprocess.PIPE, **kwargs).stdout


def formats():
    run([FORMATTER, "--style=file", "--fallback-style=LLVM", "--dry-run", "--Werror",
         *SOURCE, REPLAY])


def compile_local(scratch, exe):
    scratch.mkdir(parents=True, exist_ok=True)
    objects = []
    compiles = []
    for source in [*SOURCE[:2], REPLAY]:
        obj = scratch / (source.stem + ".o")
        depfile = obj.with_suffix(".d")
        flags = (["-fno-lto", "-fno-fast-math", "-ffp-contract=off"]
                 if source == SOURCE[1] else [])
        argv = [*CXX, *flags, "-MD", "-MF", depfile, "-c", source, "-o", obj]
        run(argv)
        deps = shlex.split(depfile.read_text().replace("\\\n", "").split(":", 1)[1])
        compiles.append(dict(argv=list(map(str, argv)), dependencies=[binding(path) for path in deps],
                             product=binding(obj), depfile=binding(depfile)))
        objects.append(obj)
    map_path = scratch / "link.map"
    command = [CXX[0], *objects, *LIBRARIES, *WRAPS, "-Wl,-rpath," + str(EXTERNAL),
               "-pthread", "-ldl", "-lm", "-Wl,--gc-sections", "-Wl,-Map," + str(map_path),
               "-o", exe]
    run(command)
    metadata = dict(compiles=compiles, argv=list(map(str, command)), link_map=binding(map_path),
                    inputs=[binding(path) for path in LIBRARIES], executable=binding(exe),
                    core_provenance=binding(BUILD / "upstream-core/sdk/share/presonus-core-5/provenance.json"))
    (scratch / "build.json").write_text(json.dumps(metadata, indent=2) + "\n")


def symbols(obj, test_obj, exe):
    names = [f"_ZN8Presonus10PanControlD{variant}Ev" for variant in range(3)]
    rows = run(["/usr/bin/nm", "--defined-only", obj]).splitlines()
    found = [row for row in rows if row.split()[-1:] and row.split()[-1] in names]
    assert len(found) == 3 and all(row.split()[-2] == "T" for row in found)
    if test_obj:
        undefined = run(["/usr/bin/nm", "--undefined-only", test_obj])
        assert names[1] in undefined and names[2] in undefined
    linked = run(["/usr/bin/nm", "--defined-only", exe])
    assert all(name in linked for name in names)
    return found


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("format", "compile", "symbols", "replay", "fixture"))
    parser.add_argument("variant", choices=("complete", "base", "deleting"))
    parser.add_argument("--exe", type=Path)
    parser.add_argument("--object", type=Path)
    parser.add_argument("--fixture", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--integration", type=Path)
    args = parser.parse_args()

    task = "sqlite02_pancontrol_" + args.variant + "_destroy"
    scratch = Path("temp/recovery-work") / task
    exe = args.exe or (scratch / "replay")
    obj = args.object or (scratch / "PanControlBindings.o")
    fixture = args.fixture or TEST.with_name(task) / "fixtures.json"
    if args.action == "format":
        formats()
        return
    if args.action == "compile":
        compile_local(scratch, exe)
        return
    if args.action == "symbols":
        print(symbols(obj, None if args.exe else scratch / "Replay.o", exe))
        return
    original = native.generate(task)
    if args.action == "fixture":
        fixture.write_text(json.dumps(original, indent=2) + "\n")
        return

    assert original == json.loads(fixture.read_text())
    cases = original["cases"]
    payload = "".join(" ".join(map(str, row["inputs"])) + "\n" for row in cases)
    lines = run([exe, args.variant], input=payload).splitlines()
    expected = []
    for row in cases:
        events = [value if kind == "remove" else 7 if kind == "base" else 8
                  for kind, value in row["events"] if kind != "base" or value]
        setup = [value + 10 if kind == "add" else value
                 for kind, value in row["setter_events"]]
        expected.append([row["bitmap_refcount"], *events, 0, *setup])
    assert [list(map(int, line.split())) for line in lines] == expected
    print(f"{len(cases)} native and {len(lines)} portable comparisons passed for {task}")
    if args.out is None:
        return
    formats()
    definitions = symbols(obj, None if args.exe else scratch / "Replay.o", exe)
    packet_path = native.PACKETS / task / "CONTEXT.json"
    packet = json.loads(packet_path.read_text())
    providers = {record["path"]: binding(record["path"])["sha256"]
                 for record in packet["task"]["review"]["providers"]}
    for path in ("third_party/ccl-framework/core/portable/gui/corebitmap.h",
                 "third_party/ccl-framework/core/portable/gui/corebitmap.cpp",
                 "third_party/ccl-framework/core/public/corevector.h"):
        providers[path] = binding(path)["sha256"]
    sources = {str(path.relative_to("uc-library")): binding(path)["sha256"] for path in SOURCE}
    identity = original["original"]
    result = dict(original_elf_sha256=identity["elf"], mangled=identity["mangled"],
                  original_address=identity["address"], cpp_compiled=True,
                  mangling_namespace_checked=True, portable_ready=False, domain=DOMAIN,
                  sources=sources, repository_sources=providers, declaration_uncertainties=LIMITATIONS)
    oracle_inputs = {key: value for key, value in original.items() if key != "cases"}
    proof = dict(
        version=1, task_id=task, domain=DOMAIN, limitations=LIMITATIONS,
        cpp_compiled=True, mangling_namespace_checked=True, cpp_differential_passed=True,
        formatting_verified=True, compiled=True, compiled_mangled_names_matched=True,
        fresh_native_execution=True, native_behavior_verified=True, original_declaration_verified=False,
        original_arm_abi_verified=False, hardware_verified=False, portable_ready=False,
        canonical_binding_pending=args.integration is None, functions=[result],
        proposed_readiness=dict(ready=[], pending=[result]), sources=sources, repository_sources=providers,
        command=[sys.executable, "-B", *sys.argv], formatter_version=run([FORMATTER, "--version"]).strip(),
        compiler_version=run([CXX[0], "--version"]).splitlines()[0],
        unicorn_version=__import__("unicorn").__version__, capstone_version=__import__("capstone").__version__,
        packet=binding(packet_path), oracle=binding(TEST / "native.py"), fixture=binding(fixture),
        producer_sha256=binding(__file__)["sha256"], oracle_inputs=oracle_inputs,
        ranges=[identity], native_cases=len(cases), portable_cases=len(lines),
        symbols=definitions, observations=expected, executable=binding(exe), object=binding(obj),
        build=json.loads((scratch / "build.json").read_text()) if not args.exe else None,
        integration=binding(args.integration) if args.integration else None,
    )
    args.out.write_text(json.dumps(proof, indent=2) + "\n")


if __name__ == "__main__":
    main()
