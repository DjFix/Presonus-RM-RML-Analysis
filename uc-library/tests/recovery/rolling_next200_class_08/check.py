"""Compile local artifacts or replay the sealed observations on a built target."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

import native

TEST = Path(__file__).parent
SCRATCH = Path("temp/recovery-work/rolling_next200_class_08")
BASELINE = Path("temp/provider-baseline08")
HEADER = "include/presonus/panel/temperature_control.hpp"
SOURCE = "src/Presonus/Panel/TemperatureControl.cpp"
BASE_HEADER = "include/presonus/panel/control.hpp"
CORE = Path("third_party/ccl-framework")
PROVIDER_SOURCES = (
    "core/portable/coreparams.cpp",
    "core/portable/coreattributes.cpp",
    "core/platform/shared/posix/coreatomicstack.posix.cpp",
)
DOMAIN = ("24 original ARM executions over six signed int inputs, two receiver "
          "sentinels and two parameter-state labels, with exact instruction and "
          "stack-write traces, restored SP/FP and preserved R0/R1/LR and "
          "receiver bytes. 48 portable executions exercise both qualified "
          "and virtual calls with null or genuine pinned CCL-backed parameter "
          "bindings, and compare observable receiver state and parameter value.")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def command(argv):
    return subprocess.run(argv, check=True, text=True, capture_output=True)


def compile_local():
    common = ["c++", "-std=c++17", "-O2", "-frtti", "-fno-lto", "-fno-fast-math",
              "-ffp-contract=off", "-pthread", "-Ulinux", "-DCORE_USE_OPENSSL=1",
              "-DPRESONUS_HAS_UPSTREAM_CORE=1", "-Iuc-library/include",
              "-isystem", str(CORE)]
    provenance = json.loads((BASELINE / "PROVENANCE.json").read_text())
    for row in provenance["files"]:
        native.require(sha(row["local"]) == row["sha256"], "Local archive changed")

    obj = SCRATCH / "TemperatureControl.cpp.o"
    subprocess.run(common + ["-c", f"uc-library/{SOURCE}", "-o", obj], check=True)
    libs = [BASELINE / name for name in ("libpresonus_uc.a", "libcorelib.a",
                                        "libpresonus_core_allocator.a")]
    subprocess.run(common + [TEST / "Replay.cpp", obj] +
                   [CORE / source for source in PROVIDER_SOURCES] +
                   libs + ["-ldl", "-lm", "-o", SCRATCH / "replay"], check=True)


def verify_symbol(obj):
    lines = command(["nm", "--defined-only", obj]).stdout.splitlines()
    matching = [line.strip() for line in lines if line.split()[-1] == native.MANGLED]
    native.require(len(matching) == 1 and matching[0].split()[1] == "T",
                   "Expected one exact global implementation symbol")
    return matching[0]


def replay(args):
    fixture = json.loads(args.fixtures.read_text())
    native.require((fixture["elf_sha256"], fixture["mangled"], fixture["address"],
                    fixture["size"], fixture["section"], fixture["range_sha256"]) ==
                   (native.ELF_SHA, native.MANGLED, native.ADDRESS, native.SIZE,
                    native.SECTION, native.BODY_SHA), "Unexpected fixture identity")
    native.require(len(fixture["cases"]) == 24, "Unexpected fixture case count")
    rows = [(item, dispatch) for item in fixture["cases"] for dispatch in (0, 1)]
    inputs = "".join(f"{row['value']} {row['seed']} {int(row['bound'])} {dispatch}\n"
                     for row, dispatch in rows)
    expected = [str(int(row["unchanged"])) for row, _ in rows]
    result = subprocess.run([args.exe.resolve()], check=True, input=inputs, text=True,
                            capture_output=True)
    native.require(result.stdout.splitlines() == expected, "Portable behavior differs")
    sources = {source: sha(Path("uc-library") / source)
               for source in (HEADER, SOURCE, BASE_HEADER)}
    core_sources = [*PROVIDER_SOURCES, "core/portable/coreparams.h",
                    "core/public/corevector.h"]
    row = {"original_elf_sha256": native.ELF_SHA, "mangled": native.MANGLED,
           "original_address": native.ADDRESS, "cpp_compiled": True,
           "mangling_namespace_checked": True, "portable_ready": False,
           "domain": DOMAIN, "sources": sources,
           "repository_sources": {str(CORE / k): sha(CORE / k) for k in core_sources},
           "declaration_uncertainties": ["Ordinary original return declaration is "
                                         "unresolved. The source override uses void."]}
    integration = None
    if args.integration not in ("local", "ctest"):
        proof = Path(args.integration)
        native.require(json.loads(proof.read_text()).get("ctest_passed") is True,
                       "Canonical integration CTest proof did not pass")
        integration = {"path": str(proof), "sha256": sha(proof)}

    receipt = {
        "passed": True, "domain": DOMAIN, "original_native_cases": len(fixture["cases"]),
        "portable_cases": len(rows), "original_range": {
            key: fixture[key] for key in ("elf_sha256", "mangled", "address", "size",
                                          "section", "file_offset", "range_sha256", "unicorn")
        }, "fixture_sha256": sha(args.fixtures), "object_sha256": sha(args.object),
        "executable_sha256": sha(args.exe), "symbol": verify_symbol(args.object),
        "formatter": command(["uc-library/.venv/bin/clang-format", "--version"]).stdout.strip(),
        "integration_mode": args.integration, "integration": integration, "producers": {
            str(TEST / name): sha(TEST / name) for name in ("native.py", "check.py", "Replay.cpp")
        },
        "proposed_readiness": {"ready": [], "pending": [row]},
    }
    args.out.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"passed": True, "domain": DOMAIN, "cases": len(rows)}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compile-local", action="store_true")
    parser.add_argument("--symbols-only", action="store_true")
    for option in ("exe", "object", "fixtures", "out"):
        parser.add_argument("--" + option, type=Path)
    parser.add_argument("--integration")
    args = parser.parse_args()
    if args.compile_local:
        compile_local()
    elif args.symbols_only:
        print(verify_symbol(args.object))
    else:
        replay(args)


if __name__ == "__main__":
    main()
