"""Compare the compiled FrontPanel callbacks with sealed original ARM observations."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

LIB = Path("uc-library")
PANEL = LIB / "src/Presonus/Panel"
HEADERS = LIB / "include/presonus/panel"
TEST = Path("uc-library/tests/recovery/cycle20_g05_s05")
SYMBOL = "_ZN8Presonus5Panel19FrontPanelComponent12presetStoredERKNS0_15PresetComponentEi"
DOMAIN = ("Five signed slot values including both int32 limits on real portable "
          "FrontPanel, Fat24 and Storm defaults. Compare object and panel-state "
          "bytes, external calls and unexpected logging with offline RM ARM entry "
          "executions from three verified native primary slots. Native object "
          "pages and stack are synthetic; return register is outside the comparison.")
UNCERTAINTY = "Original unencoded return declaration, native layout and ARM ABI remain unresolved."
CLASSES = ("FrontPanelComponent", "Fat24FrontPanelComponent", "StormFrontPanelComponent",
           "PresetComponent")
UNITS = [*(PANEL / f"{name}.cpp" for name in CLASSES),
         PANEL / "FrontPanelLifecycle.cpp", TEST / "Replay.cpp"]
SOURCES = [*UNITS[:-1], *(HEADERS / f"{name}.hpp" for name in CLASSES)]
COMPILE = ["/usr/bin/c++", "-O2", "-g0", "-std=c++17", "-fno-rtti", "-DNDEBUG=1",
           "-DPRESONUS_HAS_UPSTREAM_CORE=1", "-DCORE_USE_OPENSSL=1", "-Ulinux",
           "-pthread", "-Wno-multichar", "-ffunction-sections", "-fdata-sections",
           "-Iuc-library/include", "-Ithird_party/ccl-framework"]
ARCHIVES = ("libpresonus_rm_components.a", "libcorelib.a",
            "libpresonus_core_allocator.a", "libpresonus_private_glibc29.a")


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def build(work, overlay):
    objects = []
    commands = []
    for source in UNITS:
        obj = work / (source.stem + ".o")
        objects.append(str(obj))
        commands.append([*COMPILE[:1], "-I" + str(overlay), *COMPILE[1:], "-MMD", "-MF", str(obj.with_suffix(".d")),
                         "-c", str(source), "-o", str(obj)])
    receipt = json.loads((work / "archives/copy-receipt.json").read_bytes())
    archives = [work / "archives" / name for name in ARCHIVES]
    for archive in archives:
        recorded, = (row for row in receipt["archives"].values()
                     if Path(row["copy"]).name == archive.name)
        if digest(archive) != recorded["copy_sha256"]:
            raise SystemExit(f"Stale scoped archive copy: {archive}")
    commands.append(["/usr/bin/c++", "-Wl,--gc-sections", f"-Wl,-Map,{work / 'replay.map'}",
                     *objects, "-Wl,--start-group", *map(str, archives), "-Wl,--end-group",
                     "-pthread", "-ldl", "-lz", "-o", str(work / "replay")])
    for command in commands:
        subprocess.run(command, check=True)
    for name in ("FrontPanelLifecycle", *CLASSES[1:3]):
        obj = work / (name + ".o")
        command = ["objdump", "-r", str(obj)]
        if SYMBOL not in subprocess.check_output(command, text=True):
            raise SystemExit(f"Missing inherited callback relocation in {name}")
        commands.append(command)
    (work / "local-build-argv.json").write_text(json.dumps(commands, indent=2) + "\n")


def check_symbol(path):
    lines = subprocess.check_output(["nm", "--defined-only", path], text=True).splitlines()
    matches = [line for line in lines if line.split()[-1:] == [SYMBOL]]
    if len(matches) != 1 or matches[0].split()[-2] != "T":
        raise SystemExit("Expected one global text definition of the exact callback")
    return matches[0]


def replay(args):
    matched = check_symbol(args.object)
    result = subprocess.run([args.exe.resolve()], capture_output=True, text=True, check=True)
    fixture = json.loads(args.fixtures.read_bytes())
    if fixture["mangled"] != SYMBOL:
        raise SystemExit("Fixture identity differs")
    expected = [f"{row['owner']} {row['index']} {int(row['panel_changed'])} "
                f"{int(row['preset_changed'])} {row['external_calls']}" for row in fixture["cases"]]
    if len(expected) != 15 or result.stdout.splitlines() != expected or result.stderr:
        raise SystemExit("Portable outputs or diagnostics differ from sealed ARM observations")
    proposal = {
        "mangled": SYMBOL, "original_elf_sha256": fixture["elf_sha256"],
        "cpp_compiled": True, "mangling_namespace_checked": True,
        "portable_ready": False, "declaration_uncertainties": [UNCERTAINTY],
        "domain": DOMAIN, "sources": {str(p.relative_to(LIB)): digest(p) for p in SOURCES},
        "repository_sources": {p: digest(p) for p in (
            "third_party/ccl-framework/core/portable/corecomponent.h",
            "third_party/ccl-framework/core/public/corevector.h")},
    }
    integration = None if args.integration == "ctest" else {
        "path": args.integration, "sha256": digest(args.integration)}
    proof = {
        "behavior_validation_passed": True, "validation_domain": DOMAIN,
        "integration": integration,
        "fixture": {"path": str(args.fixtures), "sha256": digest(args.fixtures)},
        "executable": {"path": str(args.exe), "sha256": digest(args.exe)},
        "object": {"path": str(args.object), "sha256": digest(args.object), "nm": matched},
        "case_count": len(expected), "observations": expected,
        "proposed_readiness": {"ready": [], "pending": [proposal]},
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(proof, indent=2) + "\n")
    print(f"Matched {len(expected)} portable callback cases to sealed ARM fixtures")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-local", type=Path)
    parser.add_argument("--provider-overlay", type=Path)
    parser.add_argument("--symbols-only", type=Path)
    parser.add_argument("--exe", type=Path)
    parser.add_argument("--object", type=Path)
    parser.add_argument("--fixtures", type=Path)
    parser.add_argument("--integration")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.build_local:
        if not args.provider_overlay:
            parser.error("Local build requires the sealed provider overlay")
        build(args.build_local, args.provider_overlay)
    elif args.symbols_only:
        print(check_symbol(args.symbols_only))
    elif all((args.exe, args.object, args.fixtures, args.integration, args.out)):
        replay(args)
    else:
        parser.error("Supply local build, symbol check, or all replay arguments")


if __name__ == "__main__":
    main()
