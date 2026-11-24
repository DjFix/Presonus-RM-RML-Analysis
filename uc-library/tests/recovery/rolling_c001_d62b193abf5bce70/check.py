"""Compare a linked portable replay to independently observed ARM behavior."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[4]
TEST = Path(__file__).resolve().parent
SOURCE = 'uc-library/src/Presonus/Panel/RackPanelComponent.cpp'
HEADER = 'uc-library/include/presonus/panel/RackPanelComponent.hpp'
CORE = ['third_party/ccl-framework/core/portable/corecomponent.h', 'third_party/ccl-framework/core/portable/corecomponent.cpp']
DOMAIN = 'Three verified original ARM executions with synthetic receiver and input registers and sentinel memory. Compare linked portable operation on three valid receiver/input setups, with sampled receiver and argument state checks. Native reads and writes are confined to frame setup and teardown.'
LIMITATIONS = ['Original return declaration, member/virtual traits, ARM layout/ABI and hardware remain unresolved.']


def sha(path):
    return hashlib.file_digest(path.open("rb"), "sha256").hexdigest()


def run(argv):
    return subprocess.check_output(argv, cwd=ROOT, text=True)


def build(args):
    sdk = args.build / "upstream-core/sdk"
    common = ["c++", "-std=gnu++20", "-Ulinux", "-DCORE_USE_OPENSSL=1",
              "-DPRESONUS_HAS_UPSTREAM_CORE=1", "-Iuc-library/include",
              "-isystem", str(sdk / "include/presonus-core-5"),
              "-isystem", str(sdk / "include/presonus-core-codecs"),
              "-ffunction-sections", "-fdata-sections"]
    flags = ["-fno-rtti"] if SOURCE.endswith("RackPanelComponent.cpp") else []
    if SOURCE.endswith("ServerComponent.cpp"):
        archive = "libpresonus_cs18_components.a"
    else:
        archive = "libpresonus_rm_components.a"
    dependencies = []
    commands = [common + flags + ["-c", SOURCE, "-o", str(args.object)]]
    if SOURCE.endswith(("AvbComponent.cpp", "MixerComponentBase.cpp")):
        # This exact RTTI provider is compiled with its real implementation.
        # The existing RM archive retains its pre-change no-RTTI provider.
        for path in ("UC/ServerComponent.cpp", "AVB/AvbComponentRouting.cpp"):
            obj = args.object.with_name(args.object.stem + "-" + Path(path).stem + ".o")
            dependencies.append(str(obj))
            commands.append(common + ["-c", "uc-library/src/Presonus/" + path, "-o", str(obj)])
    commands += [
        common + flags + [str(TEST / "Replay.cpp"), str(args.object)] + dependencies
        + ["-Wl,--gc-sections", str(args.build / archive)]
        + [str(sdk / "lib" / f"lib{name}.a") for name in
           ("corelib", "presonus_core_allocator", "presonus_png", "presonus_zlib")]
        + ["-lssl", "-lcrypto", str(args.dns), "-ldl",
           str(args.build / "private-glibc29-provider/libpresonus_private_glibc29.a"),
           "-lm", "-pthread", "-o", str(args.exe)]
    ]
    for command in commands:
        run(command)
    print(json.dumps({"commands": commands, "compiler": run(["c++", "--version"])}))


def symbol(path, expected):
    rows = run(["nm", "--defined-only", "--format=posix", str(path)]).splitlines()
    matched = [row for row in rows if row.split()[0] == expected and row.split()[1] in ("T", "W")]
    if len(matched) != 1:
        raise ValueError(f"Expected exactly one source symbol in {path}: {expected}")
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
    output = run([str(args.exe)]).splitlines()
    if output != expected or len(expected) != 3:
        raise ValueError(f"Portable execution differs from ARM observations: {output!r}")
    integration = {}
    if args.integration != "-":
        path = Path(args.integration)
        if json.loads(path.read_text()).get("ctest_passed") is not True:
            raise ValueError("Canonical integration must record passing CTest")
        integration = {"path": str(path), "sha256": sha(path)}
    formatter = "uc-library/.venv/bin/clang-format"
    sources = {str(Path(path).relative_to("uc-library")): sha(ROOT / path)
               for path in (SOURCE, HEADER)}
    row = dict(original_elf_sha256=fixture["elf_sha256"], mangled=fixture["mangled"],
               cpp_compiled=True, mangling_namespace_checked=True,
               portable_ready=False, domain=DOMAIN, sources=sources,
               repository_sources={path: sha(ROOT / path) for path in CORE},
               declaration_uncertainties=LIMITATIONS)
    format_argv = [formatter, "--style=file", "--fallback-style=LLVM", "--dry-run", "--Werror",
                   SOURCE, HEADER, str(TEST / "Replay.cpp")]
    run(format_argv)
    proof = {"cpp_differential_passed": True, "compiled_mangled_names_matched": True,
             "domain": DOMAIN, "functions": [row], "integration": integration,
             "proposed_readiness": {"ready": [], "pending": [row]},
             "native_evidence": fixture, "portable_case_count": len(expected),
             "symbols": matches, "formatted_sources": sources, "format_argv": format_argv,
             "formatter": run([formatter, "--version"]).strip(),
             "fixture_sha256": sha(args.fixture), "oracle_sha256": sha(TEST / "native.py"),
             "checker_sha256": sha(Path(__file__)), "test_sha256": sha(TEST / "Replay.cpp"),
             "executable_sha256": sha(args.exe), "object_sha256": sha(args.object)}
    if args.out != "-":
        Path(args.out).write_text(json.dumps(proof, indent=2) + "\n")
    print(f"Validated {len(expected)} portable cases against sealed ARM observations")


if __name__ == "__main__":
    main()
