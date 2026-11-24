"""Locally compile the owned TU or replay it from a canonical CMake build."""
import argparse
from hashlib import sha256
import json
import os
import shutil
from pathlib import Path
import subprocess

DIR = Path("uc-library/tests/recovery/rolling_wheel_presetspagecomponent")
WORK = Path("temp/recovery-work/rolling_wheel_presetspagecomponent")
HEADER = Path("uc-library/include/presonus/surface/PresetsPageComponent.hpp")
SOURCE = Path("uc-library/src/Presonus/Surface/PresetsPageComponent.cpp")
CORE = Path("third_party/ccl-framework/core/portable/gui/coreview.h")
TEST = DIR / "Replay.cpp"
FORMAT = ["uc-library/.venv/bin/clang-format", "--style=file", "--fallback-style=LLVM",
          "--dry-run", "--Werror", str(HEADER), str(SOURCE), str(TEST)]
SYMBOL = "_ZN8Presonus7Surface20PresetsPageComponent12onWheelInputERKN4Core8Portable10WheelEventE"
DOMAIN = ("Ten differential wheel cases over positive, negative, zero and wrapping "
          "delta with both axes, clamp boundaries, visible and hidden lists. "
          "Compares resulting offset, selection and ordered list update trace.")
UNCERTAINTY = ["Original onWheelInput return declaration and virtual dispatch unresolved. "
               "The portable method uses void with the existing component lifecycle. "
               "Original receiver layout and ARM32 ABI remain unverified."]


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def invoke(command):
    command = [str(arg) for arg in command]
    print(json.dumps(command), flush=True)
    subprocess.run(command, check=True, env={**os.environ, "TMPDIR": str(WORK.resolve())})


def compile_local(executable, object_file):
    WORK.mkdir(parents=True, exist_ok=True)
    toolchain = ["/usr/bin/c++", "-std=c++17", "-fno-rtti", "-Ulinux",
                 "-Wno-multichar", "-Iuc-library/include", "-Ithird_party/ccl-framework"]
    archives = Path("temp/provider-baseline08")
    provider_root = Path("/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream")
    sdk = provider_root / "root-integration-01/upstream-core/sdk/lib"
    png, zlib = (sdk / name for name in ("libpresonus_png.a", "libpresonus_zlib.a"))
    role = archives / "libpresonus_cs18_components.a"
    pinned_inputs = {
        png: "99514af041c29b5aa782c14718794453b13841f99b7de584db3f3f89bf68ecc1",
        zlib: "9095c54154b7617d8f283d7858ae45218cad1ba92e54e04f983dc0a7151c6c93",
        role: "ecb1af91c20b8da0daba16e7362e0d1ac9f03b211cb40c2eebcbb05cc951427c",
    }
    for path, expected in pinned_inputs.items():
        if digest(path) != expected:
            raise ValueError(f"Pinned archive changed: {path}")
    invoke([*toolchain, "-c", SOURCE, "-o", object_file])
    member_name = "PresetsPageComponent.cpp.o"
    member = WORK / member_name
    shutil.copyfile(object_file, member)
    local_role = WORK / role.name
    shutil.copyfile(role, local_role)
    invoke(["ar", "r", local_role, member])
    members = subprocess.check_output(["ar", "t", local_role], text=True).splitlines()
    if members.count(member_name) != 1:
        raise ValueError("Expected a single Presets page object in the CS18 archive")
    if subprocess.check_output(["ar", "p", local_role, member_name]) != object_file.read_bytes():
        raise ValueError("CS18 archive member differs from the locally compiled object")
    invoke([*toolchain, TEST, "-Wl,--start-group", local_role,
            archives / "libcorelib.a", archives / "libpresonus_core_allocator.a",
            png, zlib, "-Wl,--end-group", "-lssl", "-lcrypto",
            provider_root / "external-dev/usr/lib/x86_64-linux-gnu/libdns_sd.so",
            "-ldl", provider_root / "root-integration-01/private-glibc29-provider/libpresonus_private_glibc29.a",
            "-lm", "-pthread", "-o", executable])
    dynamic = subprocess.check_output(["readelf", "-d", executable], text=True)
    if "libpng" in dynamic or "libz.so" in dynamic:
        raise ValueError("An unpinned dynamic PNG or zlib dependency was linked")
    provenance = subprocess.check_output(["nm", "--defined-only", executable], text=True)
    linked_provider_symbols = {}
    for archive, symbol in ((png, "png_access_version_number"), (zlib, "zlibVersion")):
        provider_symbols = subprocess.check_output(["nm", "--defined-only", archive], text=True)
        if not any(line.split()[-1:] == [symbol] for line in provider_symbols.splitlines()):
            raise ValueError(f"Pinned provider definition missing from archive: {symbol}")
        linked_provider_symbols[symbol] = any(
            line.split()[-1:] == [symbol] for line in provenance.splitlines())
    print(json.dumps({"pinned_provider_and_baseline_archives": {
        str(path): expected for path, expected in pinned_inputs.items()},
        "role_archive_sha256": digest(local_role),
        "dynamic_png_or_zlib_dependency": False,
        "provider_version_symbols_present_in_replay": linked_provider_symbols}, indent=2))


def check_symbol(object_file):
    listing = subprocess.check_output(["nm", "--defined-only", object_file], text=True)
    rows = [line for line in listing.splitlines() if line.split()[-1:] == [SYMBOL]]
    if len(rows) != 1:
        raise ValueError(f"Expected a single definition of {SYMBOL}")
    print(rows[0])
    return rows[0]


def replay(args):
    row = check_symbol(args.object)
    fixtures = json.loads(args.fixtures.read_text())
    for case in fixtures["cases"]:
        actual = json.loads(subprocess.check_output(
            [args.exe.resolve(), *map(str, case["argv"])], text=True))
        if actual != case["expected"]:
            raise ValueError(f"Wheel case {case['argv']}: {actual} != {case['expected']}")
    print(DOMAIN)
    sources = {str(path.relative_to("uc-library")): digest(path)
               for path in (SOURCE, HEADER)}
    entry = dict(original_elf_sha256=fixtures["elf_sha256"], mangled=SYMBOL,
                 original_address=0xB45D4, domain=DOMAIN, sources=sources,
                 repository_sources={str(CORE): digest(CORE)}, cpp_compiled=True,
                 mangling_namespace_checked=True, portable_ready=False,
                 declaration_uncertainties=UNCERTAINTY)
    proof = dict(replay_passed=True, cpp_compiled=True, mangling_namespace_checked=True,
                 proposed_readiness=dict(ready=[], pending=[entry]), functions=[entry],
                 domain=DOMAIN, fixtures_sha256=digest(args.fixtures),
                 native_producer_sha256=digest(DIR / "native.py"), case_count=len(fixtures["cases"]),
                 checker_sha256=digest(Path(__file__)), object_sha256=digest(args.object),
                 exe_sha256=digest(args.exe), compiled_symbol=row,
                 original_range={key: value for key, value in fixtures.items() if key != "cases"},
                 formatter=subprocess.check_output([FORMAT[0], "--version"], text=True).strip())
    if args.integration:
        proof["integration_sha256"] = digest(args.integration)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(proof, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["format", "compile", "symbols", "replay"])
    parser.add_argument("--exe", type=Path, default=WORK / "replay")
    parser.add_argument("--object", type=Path, default=WORK / "PresetsPageComponent.o")
    parser.add_argument("--fixtures", type=Path, default=DIR / "fixtures.json")
    parser.add_argument("--integration", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.action == "format":
        invoke(FORMAT)
    elif args.action == "compile":
        compile_local(args.exe, args.object)
    elif args.action == "symbols":
        check_symbol(args.object)
    else:
        replay(args)


if __name__ == "__main__":
    main()
