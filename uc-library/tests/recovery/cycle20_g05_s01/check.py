"""Compile and compare portable Storm teardown with exact offline ARM traces."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time

from elftools.elf.elffile import ELFFile
from elftools.elf.relocation import RelocationSection
from unicorn import __version__ as unicorn_version

from native import FAT24, FRONT, STORM, TARGETS, observe

ROOT = Path("/home/rs/projects/opencs/ai-line-analysis")
CONTROL = ROOT / "temp/recovery-work/control10x20-after-4fed70d11"
ELF = CONTROL / "packeting/seed-wave02-batch/snapshot/rootfs/RML16AI_Rack_13731/home/root/mixer"
LOCAL = Path("temp/recovery-work/cycle20_g05-local")
FORMATTER = "uc-library/.venv/bin/clang-format"
TEST = Path("uc-library/tests/recovery/cycle20_g05_s01")
SOURCE = "uc-library/src/Presonus/Panel/StormFrontPanelComponent.cpp"
HEADER = "uc-library/include/presonus/panel/StormFrontPanelComponent.hpp"
LIBRARY_DEPS = (
    "uc-library/include/presonus/panel/Fat24FrontPanelComponent.hpp",
    "uc-library/include/presonus/panel/FrontPanelComponent.hpp",
    "uc-library/include/presonus/panel/PanelComponent.hpp",
    "uc-library/src/Presonus/Panel/Fat24FrontPanelComponent.cpp",
    "uc-library/src/Presonus/Panel/FrontPanelLifecycle.cpp",
    "uc-library/src/Presonus/Panel/PanelComponent.cpp",
)
CORE = "third_party/ccl-framework/core/"
CORE_DEPS = (
    "portable/corecomponent.cpp", "portable/corecomponent.h",
    "portable/coreattributes.cpp", "portable/coreparams.cpp",
    "portable/coreparams.h", "public/corevector.h", "public/coreallocator.h",
)
ARCHIVES = {
    "libpresonus_rm_components.a": "bbb430c9fcfa26effde55998e480be463e5d9218eab50383312803139832453f",
    "libcorelib.a": "3c4f0825acb529fda135587b7ff5cb92ca0100bb417a20c034d3fdef80a93e0c",
    "libpresonus_core_allocator.a": "69892fbcec9a50a140462982073c686a67ca4763dfb5dfa190534d022b78a40d",
    "libpresonus_private_glibc29.a": "e14acfad9b5246950768780a5bd372e58cc208be6dd290c29a11e9949356ab20",
}
DOMAIN = (
    "Normal offline Storm teardown on three separately initialized ARM receiver pages, "
    "through exact Fat24 D2 and FrontPanel D2 with explicit downstream boundaries. "
    "Portable teardown uses one, two and eight owned CCL parameters, observes the first "
    "parameter's destruction and preserves borrowed application services. D0 reaches the actual "
    "host unsized operator delete with the complete receiver after base teardown. "
    "Native delete is observed at the original unsized PLT entry using an emulated page release."
)
UNCERTAINTIES = [
    "Original secondary inheritance and interface declarations associated with Storm's receiver "
    "vptr transitions are unresolved. Portable inheritance models the directly observed "
    "Fat24 base teardown only. Original ARM32 layout, ABI, exception paths and hardware are excluded."
]
TASKS = {"D1": "cycle20_g05_s01", "D2": "cycle20_g05_s02", "D0": "cycle20_g05_s03"}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(argv):
    result = subprocess.run(argv, check=True, capture_output=True, text=True)
    return result.stdout


def compile_local(args):
    build = args.object.parent
    build.mkdir(parents=True, exist_ok=True)
    for name, sha in ARCHIVES.items():
        if digest(LOCAL / name) != sha:
            raise ValueError(f"Frozen local archive differs: {name}")
    def member_digest(member):
        data = subprocess.check_output(["ar", "p", LOCAL / next(iter(ARCHIVES)), member])
        return hashlib.sha256(data).hexdigest()
    members = {name: member_digest(name) for name in
               ("Fat24FrontPanelComponent.cpp.o", "FrontPanelLifecycle.cpp.o", "PanelComponent.cpp.o")}
    flags = ["c++", "-std=c++17", "-O3", "-fno-rtti", "-fno-lto", "-Ulinux", "-pthread",
             "-isystem", "third_party/ccl-framework", "-Iuc-library/include"]
    dns = ROOT / "temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu"
    libs = [LOCAL / name for name in ARCHIVES]
    closure = [f"-Wl,-rpath,{dns}", *libs[:-1], "/usr/lib/x86_64-linux-gnu/libpng16.so.16",
               "-lz", "-lssl", "-lcrypto", dns / "libdns_sd.so", "-ldl", libs[-1], "-lm"]
    compile_argv = [*flags, "-fno-sized-deallocation", "-c", SOURCE, "-o", args.object]
    test_argv = [*flags, TEST / "Replay.cpp", args.object, "-Wl,--wrap=_ZdlPv",
                 *closure, "-o", args.exe]
    existing_argv = [*flags, "uc-library/tests/graph_trial08_stormpanel_tests.cpp",
                     args.object, *closure, "-o", build / "ExistingStormReplay"]
    existing_replay = ["uc-library/.venv/bin/python", "-B",
                       "uc-library/tests/recovery/trial08/stormpanel/replay.py",
                       "--executable", build / "ExistingStormReplay",
                       "--fixtures", "uc-library/tests/recovery/trial08/stormpanel/native-fixtures.json"]
    records = []
    for argv in (compile_argv, test_argv, existing_argv, existing_replay):
        started = time.monotonic()
        stdout = run(argv)
        records.append(dict(argv=list(map(str, argv)), duration_s=time.monotonic() - started,
                            stdout=stdout, exit_code=0))
        if stdout:
            print(stdout, end="")
    (build / "compile.json").write_text(json.dumps(dict(commands=records, archive_members=members),
                                                        indent=2) + "\n")


def symbols(path, exe):
    def row(table, name):
        found = [s for s in table.get_symbol_by_name(name) or ()
                 if isinstance(s["st_shndx"], int) and s["st_info"]["type"] == "STT_FUNC"]
        if len(found) != 1:
            raise ValueError(f"Expected one defined compiled function: {name}")
        return found[0]

    compiled = {}
    with path.open("rb") as stream, exe.open("rb") as binary:
        elf = ELFFile(stream)
        table = elf.get_section_by_name(".symtab")
        linked = ELFFile(binary).get_section_by_name(".symtab")
        for name in (FAT24, FRONT):
            row(linked, name)
        for variant in TARGETS:
            name = STORM + variant + "Ev"
            function = row(table, name)
            row(linked, name)
            start = function["st_value"]
            size = function["st_size"]
            relocations = []
            for section in elf.iter_sections():
                if not isinstance(section, RelocationSection) or section["sh_info"] != function["st_shndx"]:
                    continue
                reloc_symbols = elf.get_section(section["sh_link"])
                for entry in section.iter_relocations():
                    if start <= entry["r_offset"] < start + size:
                        symbol = reloc_symbols.get_symbol(entry["r_info_sym"]).name
                        relocations.append([entry["r_offset"] - start, symbol])
            deallocators = [x for _, x in relocations if x.startswith("_Zdl")]
            expected = ["_ZdlPv"] if variant == "D0" else []
            if deallocators != expected:
                raise ValueError(f"{name}: expected {expected}, saw {deallocators}")
            targets = [x for _, x in relocations]
            if FAT24 not in targets and not ({STORM + "D1Ev", STORM + "D2Ev"} & set(targets)
                                             and variant == "D0"):
                raise ValueError(f"{name}: missing base teardown relocation")
            compiled[name] = dict(offset=start, size=size, relocations=relocations)
    return compiled


def replay(args):
    fixture = json.loads(args.fixtures.read_text())
    started = time.monotonic()
    original = observe(ELF, fixture["variant"])
    native_duration = time.monotonic() - started
    if original != fixture:
        raise ValueError("Fresh ARM execution differs from sealed fixture")
    compiled = symbols(args.object, args.exe)
    checks = []
    for case, owned_parameters in zip(original["cases"], (1, 2, 8), strict=True):
        # Normalize the actual FrontPanel entry and actual native delete boundary
        # to, respectively, a host CCL destruction and actual host allocator call.
        expected = [event for symbol, _, _ in case["calls"]
                    if (event := {FRONT: 1, "unsized_delete": 2}.get(symbol))]
        if bool(2 in expected) != case["receiver_released"]:
            raise ValueError("Original delete observation disagrees with modeled allocation state")
        argv = [args.exe, original["variant"], str(owned_parameters)]
        started = time.monotonic()
        count, first, second, borrowed_calls = map(int, run(argv).split())
        elapsed = time.monotonic() - started
        if (count, [first, second][:count], borrowed_calls) != (len(expected), expected, 0):
            raise ValueError(f"Unexpected host destruction/deallocation order: {argv!r}")
        checks.append(dict(argv=list(map(str, argv)), native_events=expected,
                           host_events=[first, second][:count],
                           borrowed_calls=borrowed_calls, duration_s=elapsed))
    sources = {x.removeprefix("uc-library/"): digest(x) for x in (SOURCE, HEADER, *LIBRARY_DEPS)}
    core = {CORE + x: digest(CORE + x) for x in CORE_DEPS}
    row = dict(original_elf_sha256=original["elf_sha256"], mangled=original["mangled"],
               cpp_compiled=True, mangling_namespace_checked=True, portable_ready=False,
               domain=DOMAIN, sources=sources, repository_sources=core,
               declaration_uncertainties=UNCERTAINTIES)
    format_version = run([FORMATTER, "--version"]).strip()
    proof = dict(
        passed=True, task=TASKS[original["variant"]], domain=DOMAIN,
        cpp_differential_passed=True, compiled_mangled_names_matched=True,
        mangled_names=[original["mangled"]], functions=[{**row, "success": True,
                                                         "native_cases": len(checks),
                                                         "cpp_cases": len(checks)}],
        proposed_readiness=dict(ready=[], pending=[row]), repository_sources=core,
        format_version=format_version, formatter=format_version,
        compiler=run(["c++", "--version"]).splitlines()[0], unicorn_version=unicorn_version,
        binary_sha256=digest(args.exe), object_sha256=digest(args.object),
        fixture_sha256=digest(args.fixtures), native_producer_sha256=digest(TEST / "native.py"),
        checker_sha256=digest(TEST / "check.py"), replay_source_sha256=digest(TEST / "Replay.cpp"),
        integration=str(args.integration), integration_sha256=digest(args.integration),
        native_elf=str(ELF), exact_native=original, native_duration_s=native_duration,
        replay_executions=checks, compiled_symbols=compiled,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(proof, indent=2) + "\n")
    print(f"{proof['task']}: {len(checks)} independent native and portable lifecycle cases passed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("format", "compile", "symbols", "replay"))
    parser.add_argument("--exe", type=Path, default=LOCAL / "Replay")
    parser.add_argument("--object", type=Path, default=LOCAL / "Storm.o")
    parser.add_argument("--fixtures", type=Path)
    parser.add_argument("--integration", type=Path, default=Path("uc-library/validation/integration.json"))
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.mode == "format":
        print(run([FORMATTER, "--version"]), end="")
        run([FORMATTER, "--style=file", "--fallback-style=LLVM", "--dry-run", "--Werror",
             SOURCE, HEADER, TEST / "Replay.cpp"])
    elif args.mode == "compile":
        compile_local(args)
    elif args.mode == "symbols":
        print(json.dumps(symbols(args.object, args.exe), indent=2))
    elif args.fixtures is not None and args.out is not None:
        replay(args)
    else:
        parser.error("replay requires --fixtures and --out")


if __name__ == "__main__":
    main()
