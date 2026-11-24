"""Compile locally or compare the linked RackPanelComponent replay to ARM observations."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[4]
TEST = Path(__file__).resolve().parent
CPP = Path("src/Presonus/Panel/RackPanelComponent.cpp")
HEADER = Path("include/presonus/panel/RackPanelComponent.hpp")
CORE = tuple(Path("third_party/ccl-framework/core") / path for path in (
    "portable/corecomponent.h", "portable/corecomponent.cpp",
    "portable/coreparams.h", "portable/coreparams.cpp",
    "system/corethread.h", "system/coretime.h",
))
DOMAIN = ("Four calls across two native synthetic receivers and two argument "
          "buffers, compared to two canonical C++ receiver lifecycles with real "
          "CCL parameters and two independent event sentinels. Native writes "
          "are confined to a restored stack frame; sampled portable receiver "
          "state, CCL parameter identity and event sentinel stay unchanged.")
UNCERTAINTIES = ["Original return declaration, static/member and virtual dispatch traits, "
                 "LinkEvent and receiver ARM layout, ARM binary compatibility and hardware."]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(argv):
    return subprocess.check_output(argv, cwd=ROOT, text=True)


def build(args):
    sdk = args.build / "upstream-core/sdk"
    common = ["c++", "-std=gnu++20", "-Ulinux", "-fno-rtti", "-DCORE_USE_OPENSSL=1",
              "-DPRESONUS_HAS_UPSTREAM_CORE=1", "-Iuc-library/include",
              "-isystem", str(sdk / "include/presonus-core-5"),
              "-isystem", str(sdk / "include/presonus-core-codecs")]
    commands = [
        common + ["-c", str(Path("uc-library") / CPP), "-o", str(args.object)],
        common + [str(TEST / "Replay.cpp"), str(args.object),
                  str(args.build / "libpresonus_rm_components.a")]
        + [str(sdk / "lib" / f"lib{name}.a") for name in
           ("corelib", "presonus_core_allocator", "presonus_png", "presonus_zlib")]
        + ["-lssl", "-lcrypto", str(args.dns), "-ldl",
           str(args.build / "private-glibc29-provider/libpresonus_private_glibc29.a"),
           "-lm", "-pthread", "-o", str(args.exe)],
    ]
    for command in commands:
        run(command)
    print(json.dumps({"commands": commands, "compiler": run(["c++", "--version"])}))


def symbol(path, expected):
    rows = run(["nm", "--defined-only", "--format=posix", str(path)]).splitlines()
    matched = [row for row in rows if row.split()[:2] == [expected, "T"]]
    if len(matched) != 1:
        raise ValueError(f"Expected exactly one symbol in {path}: {expected}")
    return matched[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", type=Path, required=True)
    parser.add_argument("--object", type=Path, required=True)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--integration", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--build", type=Path)
    parser.add_argument("--dns", type=Path)
    parser.add_argument("--symbols", action="store_true")
    args = parser.parse_args()
    if args.build:
        build(args)
        return
    fixture = json.loads(args.fixture.read_text())
    matches = {str(path): symbol(path, fixture["mangled"])
               for path in (args.object, args.exe)}
    if args.symbols:
        print(json.dumps(matches))
        return
    expected = [case["portable_observation"] for case in fixture["cases"]]
    if len(expected) != 4 or run([str(args.exe)]).splitlines() != expected:
        raise ValueError("Portable execution differs from sealed ARM observations")
    integration = {}
    if args.integration != "-":
        path = Path(args.integration)
        if json.loads(path.read_text()).get("ctest_passed") is not True:
            raise ValueError("Canonical integration must record passing CTest")
        integration = {"path": str(path), "sha256": sha(path)}
    formatter = "uc-library/.venv/bin/clang-format"
    sources = {str(path): sha(ROOT / "uc-library" / path) for path in (CPP, HEADER)}
    identity = {"original_elf_sha256": fixture["elf_sha256"],
                "mangled": fixture["mangled"]}
    row = dict(identity, cpp_compiled=True, mangling_namespace_checked=True,
               portable_ready=False, domain=DOMAIN, sources=sources,
               repository_sources={str(path): sha(ROOT / path) for path in CORE},
               declaration_uncertainties=UNCERTAINTIES)
    format_argv = [formatter, "--style=file", "--fallback-style=LLVM",
                   "--dry-run", "--Werror", *("uc-library/" + p for p in sources),
                   str(TEST / "Replay.cpp")]
    run(format_argv)
    proof = {"cpp_differential_passed": True, "compiled_mangled_names_matched": True,
             "domain": DOMAIN, "functions": [row], "integration": integration,
             "proposed_readiness": {"ready": [], "pending": [row]},
             "native_evidence": fixture,
             "portable_case_count": len(expected), "symbols": matches,
             "formatted_sources": sources, "format_argv": format_argv,
             "formatter": run([formatter, "--version"]).strip(),
             "fixture_sha256": sha(args.fixture), "oracle_sha256": sha(TEST / "native.py"),
             "checker_sha256": sha(Path(__file__)),
             "test_sha256": sha(TEST / "Replay.cpp"),
             "executable_sha256": sha(args.exe), "object_sha256": sha(args.object)}
    if args.out != "-":
        Path(args.out).write_text(json.dumps(proof, indent=2) + "\n")
    print(f"Validated {len(expected)} portable cases against sealed ARM observations")


if __name__ == "__main__":
    main()
