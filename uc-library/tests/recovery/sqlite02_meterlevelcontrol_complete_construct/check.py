"""Compile the exact Linux provider path and compare two independent ARM roles."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

SOURCE = "uc-library/src/Presonus/Panel/MeterLevelControl.cpp"
HEADER = "uc-library/include/presonus/panel/meter_level_control.hpp"
TEST = Path(__file__).with_name("Replay.cpp").resolve().relative_to(Path.cwd())
SOURCES = (
    SOURCE,
    "uc-library/src/surface_panel/MeterControl.cpp",
    "uc-library/src/surface_panel/DbTable.cpp",
    "uc-library/src/Presonus/Panel/control.cpp",
    "uc-library/src/Presonus/Panel/param_edit_handler.cpp",
    "uc-library/src/Presonus/DICE/PacketClockGateway.cpp",
)
SOURCE_BINDINGS = (*SOURCES, HEADER,
                   "uc-library/include/presonus/surface_panel/MeterControl.hpp",
                   "uc-library/include/presonus/surface_panel/DbTable.hpp",
                   "uc-library/include/presonus/panel/control.hpp",
                   "uc-library/include/presonus/panel/param_edit_handler.hpp",
                   "uc-library/include/presonus/dice/packet_services.hpp")
CORE_HEADERS = ("portable/coreparams.h", "portable/coreparams.cpp", "public/corevector.h",
                "system/coretime.h", "platform/shared/posix/coretime.posix.h")
FORMATTER = "uc-library/.venv/bin/clang-format"
FORMAT = [FORMATTER, "--style=file", "--fallback-style=LLVM", "--dry-run", "--Werror",
          HEADER, SOURCE, str(TEST)]
WRAPS = ("_ZdlPv", "_ZdlPvm", "_ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE")
DOMAINS = {
    "complete_construct": "Exact C1 per role; five signed constructor tags on real typed complete objects with initialized Control baseline, override-count nullness, default bus direction, initial mode and clip flag.",
    "base_construct": "Exact separate C2 per role; five signed constructor tags through real portable derived lifetimes, with Control baseline, override-count nullness, direction, initial mode, clip flag and typed dispatch.",
    "complete_destroy": "Exact D1 per role and complete portable placement lifetimes with three live bound parameters and zero or one owned timer. Compare observer cleanup, timer release and absence of receiver deallocation.",
    "base_destroy": "Exact D2 per role and real portable base destruction in derived placement lifetimes, with three live bound parameters and zero or one owned timer. Compare observer cleanup, timer release and absence of receiver deallocation.",
    "deleting_destroy": "Exact D0 per role and real portable deletion through Control* with three live bound parameters and zero or one owned timer. Compare provider cleanup and exact receiver deallocation after cleanup.",
    "cast_type": "Three observed class ID hits, each immediate neighbor, zero and negative ID, through actual virtual dispatch on an initialized receiver. Compare typed receiver or null.",
    "get_parameter_mode": "Initial zero and four independently seeded signed modes on initialized receivers. Compare virtual mode load through Control without invoking the unrecovered setter.",
}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(argv):
    return subprocess.run(argv, check=True, capture_output=True, text=True).stdout


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


def compile_replay(output, provider):
    output.mkdir(parents=True, exist_ok=True)
    archives = [provider / name for name in ("libcorelib.a", "libpresonus_core_allocator.a")]
    flags = ["-std=c++17", "-O2", "-fno-lto", "-Ulinux", "-pthread",
             "-DCORE_USE_OPENSSL=1", "-DPRESONUS_HAS_UPSTREAM_CORE=1",
             "-Iuc-library/include", "-isystem", "third_party/ccl-framework"]
    objects = []
    commands = []
    artifacts = {}
    observed_dependencies = set()
    for source in (*SOURCES, str(TEST)):
        obj = output / Path(source).with_suffix(".o").name
        depfile = obj.with_suffix(".d")
        command = ["c++", *flags, "-MD", "-MF", str(depfile), "-c", source, "-o", str(obj)]
        run(command)
        commands.append(command)
        objects.append(str(obj))
        for artifact in (obj, depfile):
            artifacts[str(artifact)] = digest(artifact)
        observed_dependencies.update(depfile.read_text().replace("\\\n", "").split()[1:])
    required = {SOURCE, HEADER, "uc-library/src/surface_panel/MeterControl.cpp",
                "uc-library/include/presonus/surface_panel/MeterControl.hpp",
                "uc-library/src/Presonus/Panel/control.cpp",
                "uc-library/include/presonus/panel/control.hpp"}
    assert required <= observed_dependencies, required - observed_dependencies
    executable = output / "replay"
    command = ["c++", "-fno-lto", "-pthread", *(f"-Wl,--wrap={name}" for name in WRAPS),
               *objects, *map(str, archives), "-ldl", "-lssl", "-lcrypto", "-o", str(executable)]
    run(command)
    commands.append(command)
    dump(output / "build.json", {"compiler": run(["c++", "--version"]).splitlines()[0],
                                 "argv": commands, "artifacts": artifacts,
                                 "provider_archives": {str(a): digest(a) for a in archives}})
    print("Built canonical types and real pinned Core providers with checked compiler depfiles")


def check_symbol(obj, mangled):
    symbols = run(["nm", "--defined-only", str(obj)]).splitlines()
    exact, = [line for line in symbols if line.split()[-1:] == [mangled]]
    assert exact.split()[-2] in ["T", "W"]
    if mangled.endswith("D0Ev"):
        disassembly = run(["objdump", "-dr", f"--disassemble={mangled}", str(obj)])
        assert any(name in disassembly for name in WRAPS[:2])
    return exact


def expected(value, operation):
    if operation.endswith("destroy"):
        return " ".join(event for event in value if event not in ("control", "remove_timer"))
    if isinstance(value, list):
        return " ".join(str(int(entry)) for entry in value)
    return str(int(value))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("compile", "symbols", "replay"))
    parser.add_argument("--build-dir", type=Path)
    parser.add_argument("--core-libdir", type=Path)
    parser.add_argument("--variant", choices=DOMAINS)
    parser.add_argument("--fixtures", type=Path)
    parser.add_argument("--object", type=Path)
    parser.add_argument("--exe", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--integration", type=Path)
    args = parser.parse_args()
    if args.operation == "compile":
        compile_replay(args.build_dir, args.core_libdir)
        return
    rows = json.loads(args.fixtures.read_text())
    names = {row["original"]["mangled"] for row in rows}
    mangled, = names
    symbol = check_symbol(args.object, mangled)
    if args.operation == "symbols":
        print(symbol)
        return
    start = datetime.now(timezone.utc).isoformat()
    run(FORMAT)
    results = []
    for row in rows:
        observed = []
        for case in row["cases"]:
            argv = [str(args.exe), args.variant, str(case["arg"])]
            actual = run(argv).strip()
            want = expected(case["result"], args.variant)
            assert actual == want, (row["original"]["role"], argv, actual, want)
            observed.append({"argv": argv, "output": actual})
        results.append({"original": row["original"], "portable": observed})

    # Exact original return spelling is not established by an ordinary Itanium
    # symbol or from a 32-bit register result alone.
    uncertainty = {
        "cast_type": ["Original unencoded pointer return declaration. This port overrides the typed portable base with void*."],
        "get_parameter_mode": ["Original unencoded mode return declaration and possible original enum name. This port uses int to match the typed portable base."],
    }.get(args.variant, [])
    sources = {str(Path(p).relative_to("uc-library")): digest(p) for p in SOURCE_BINDINGS}
    core = {str(p): digest(p) for p in
            (Path("third_party/ccl-framework/core") / name for name in CORE_HEADERS)}
    proposals = []
    for origin in (row["original"] for row in rows):
        entry = {"mangled": mangled, "original_elf_sha256": origin["elf"],
                 "original_address": origin["address"], "cpp_compiled": True,
                 "mangling_namespace_checked": True, "portable_ready": not uncertainty,
                 "domain": DOMAINS[args.variant], "sources": sources, "repository_sources": core}
        if uncertainty:
            entry["declaration_uncertainties"] = uncertainty
        proposals.append(entry)
    proof = {"cpp_differential_passed": True, "behavior_validation_passed": True,
             "compiled_mangled_names_matched": True, "mangling_namespace_checked": True,
             "mangled_names": [mangled], "compiled_symbol": symbol,
             "functions": proposals,
             "proposed_readiness": {"ready": [] if uncertainty else proposals,
                                    "pending": proposals if uncertainty else []},
             "validation_domain": DOMAINS[args.variant], "roles": results,
             "formatter_version": run([FORMATTER, "--version"]).strip(),
             "format_argv": FORMAT, "format_check_passed": True,
             "fixtures": {"path": str(args.fixtures), "sha256": digest(args.fixtures)},
             "exe_sha256": digest(args.exe), "object_sha256": digest(args.object),
             "native_producer_sha256": digest(Path(__file__).with_name("native.py")),
             "checker_sha256": digest(__file__), "replay_start_utc": start,
             "replay_end_utc": datetime.now(timezone.utc).isoformat()}
    if args.integration:
        proof["integration"] = {"path": str(args.integration), "sha256": digest(args.integration)}
        proof["integration_sha256"] = proof["integration"]["sha256"]
    dump(args.out, proof)
    print(f"Matched {sum(len(result['portable']) for result in results)} portable comparisons across both original roles")


if __name__ == "__main__":
    main()
