"""Build and compare the typed GPIO receiver with sealed ARM observations."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[4]
TEST = "uc-library/tests/recovery/rolling_gpio_sort"
SOURCE = "uc-library/src/Presonus/Panel/GPIOControlGroup.cpp"
HEADER = "uc-library/include/presonus/panel/GPIOControlGroup.hpp"
PROVIDERS = [
    "uc-library/include/presonus/surface_panel/ControlGroup.hpp",
    "uc-library/src/surface_panel/ControlGroup.cpp",
    "uc-library/include/presonus/panel/control.hpp",
    "uc-library/src/Presonus/Panel/control.cpp",
]
CORE = ["third_party/ccl-framework/core/public/corevector.h"]
MANGLED = "_ZN8Presonus5Panel16GPIOControlGroup4sortEv"
DOMAIN = (
    "For each assigned ELF and both evidenced constructor variants, compare sort observations "
    "for empty, singleton and unsorted three-entry receiver payloads. On ARM, verify input "
    "forwarding into a stubbed base constructor, derived native slot +12 and stack-only "
    "sort execution with opaque receiver bytes unchanged. In C++, construct the real "
    "derived receiver through ControlGroup(int, int), register real controls via the existing "
    "base API and verify owned storage, group ID, count, pointer order and tag lookups."
)
UNCERTAINTIES = [
    "The ordinary original return declaration remains unresolved. The portable method uses void.",
    "Portable ancestry does not model the native virtual table or ARM object layout and ABI.",
    "The ARM base constructor is intercepted at its original entry; opaque test words "
    "do not identify native registered-control fields. GPIO registration and hardware are out of scope.",
]
FORMAT = ["uc-library/.venv/bin/clang-format", "--style=file", "--fallback-style=LLVM",
          "--dry-run", "--Werror", HEADER, SOURCE, TEST + "/Replay.cpp"]


def run(argv, **options):
    return subprocess.check_output(argv, cwd=ROOT, text=True, **options)


def digest(path):
    with (ROOT / path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def build(args):
    sdk = args.build / "upstream-core/sdk"
    common = ["c++", "-std=gnu++20", "-Ulinux", "-DCORE_USE_OPENSSL=1",
              "-DPRESONUS_HAS_UPSTREAM_CORE=1", "-Iuc-library/include",
              "-isystem", str(sdk / "include/presonus-core-5"),
              "-ffunction-sections", "-fdata-sections"]
    provider_object = args.object.with_name("ControlGroup-provider.o")
    commands = [
        common + ["-c", SOURCE, "-o", str(args.object)],
        common + ["-c", PROVIDERS[1], "-o", str(provider_object)],
        common + [TEST + "/Replay.cpp", str(args.object), str(provider_object),
                  "-Wl,--gc-sections", str(args.build / "libpresonus_uc.a")]
        + [str(sdk / "lib" / f"lib{name}.a") for name in
           ("corelib", "presonus_core_allocator", "presonus_png", "presonus_zlib")]
        + ["-lssl", "-lcrypto", str(args.dns), "-ldl",
           str(args.build / "private-glibc29-provider/libpresonus_private_glibc29.a"),
           "-lm", "-pthread", "-o", str(args.exe)]
    ]
    for command in commands:
        run(command)
    print(json.dumps({"commands": commands, "compiler": run(["c++", "--version"])}))


def symbol(path):
    rows = run(["nm", "--defined-only", "--format=posix", str(path)]).splitlines()
    matches = [row for row in rows if row.split()[:2] in ([MANGLED, "T"], [MANGLED, "W"])]
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one {MANGLED} in {path}")
    return matches[0]


def proof(args, symbols):
    started = datetime.now(timezone.utc).isoformat()
    fixture = json.loads(args.fixture.read_text())
    originals = fixture["originals"]
    if (len(originals) != 2 or {item["role"] for item in originals} != {"server", "client"}
            or any(item["mangled"] != MANGLED or len(item["cases"]) != 6 for item in originals)):
        raise ValueError("Expected two exact role fixtures with six cases each")
    cases = [case for item in originals for case in item["cases"]]
    input_text = "".join(f"{case['group']} {case['auxiliary']} {case['tag_count']}\n" for case in cases)
    actual = [[int(word) for word in line.split()] for line in run([str(args.exe)], input=input_text).splitlines()]
    if actual != [case["expected"] for case in cases]:
        raise ValueError(f"Portable receiver observations differ: {actual!r}")
    run(FORMAT)
    integration = {}
    if args.integration != "-":
        integration_path = Path(args.integration)
        if json.loads(integration_path.read_text())["ctest_passed"] is not True:
            raise ValueError("Expected passing integration CTest")
        integration = {"path": str(integration_path), "sha256": digest(integration_path)}
    sources = {str(Path(path).relative_to("uc-library")): digest(path)
               for path in (SOURCE, HEADER, *PROVIDERS)}
    pending = [
        dict(original_elf_sha256=row["elf_sha256"], mangled=MANGLED,
             cpp_compiled=True, mangling_namespace_checked=True, portable_ready=False,
             validation_domain=DOMAIN, sources=sources, repository_sources={path: digest(path) for path in CORE},
             declaration_uncertainties=UNCERTAINTIES)
        for row in originals
    ]
    receipt = dict(cpp_differential_passed=True, compiled_mangled_names_matched=True,
                   functions=pending, proposed_readiness={"ready": [], "pending": pending},
                   native_observations=fixture, portable_case_count=len(actual), integration=integration,
                   symbols=symbols, executable_sha256=digest(args.exe), object_sha256=digest(args.object),
                   fixture_sha256=digest(args.fixture), checker_sha256=digest(Path(__file__)),
                   oracle_sha256=digest(TEST + "/native.py"), test_sha256=digest(TEST + "/Replay.cpp"),
                   format_argv=FORMAT, formatter=run([FORMAT[0], "--version"]).strip(),
                   formatted_sources={path: digest(path) for path in (SOURCE, HEADER, TEST + "/Replay.cpp")},
                   replay_argv=[str(args.exe)], replay_started_utc=started,
                   replay_finished_utc=datetime.now(timezone.utc).isoformat())
    if args.out != "-":
        Path(args.out).write_text(json.dumps(receipt, indent=2) + "\n")
    print(f"Validated {len(actual)} typed receiver replays against ARM observations")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("build", "symbols", "proof"))
    parser.add_argument("--exe", type=Path, required=True)
    parser.add_argument("--object", type=Path, required=True)
    parser.add_argument("--fixture", type=Path)
    parser.add_argument("--integration", default="-")
    parser.add_argument("--out", default="-")
    parser.add_argument("--build", type=Path)
    parser.add_argument("--dns", type=Path)
    args = parser.parse_args()
    if args.mode == "build":
        build(args)
    else:
        symbols = {str(path): symbol(path) for path in (args.object, args.exe)}
        if args.mode == "symbols":
            print(json.dumps(symbols))
        else:
            proof(args, symbols)


if __name__ == "__main__":
    main()
