"""Compile and replay the independent mixer destructor observations."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import re

SOURCE = "uc-library/src/Presonus/Mixer/LimiterComponent.cpp"
HEADER = "uc-library/include/presonus/mixer/LimiterComponent.hpp"
REPLAY = "uc-library/tests/recovery/cycle21_g07_r05/Replay.cpp"
CORE = tuple("third_party/ccl-framework/core/" + path for path in (
    "portable/corecomponent.cpp", "portable/corecomponent.h", "public/coreproperty.h"))
APP = ("uc-library/src/Presonus/Mixer/AudioComponent.cpp",
       "uc-library/src/Presonus/DspComponent.cpp", "uc-library/src/Presonus/Dsp/Controller.cpp",
       "uc-library/src/Presonus/Dsp/ControllerInterface.cpp",
       "uc-library/include/presonus/mixer/AudioComponent.hpp",
       "uc-library/include/presonus/DspComponent.hpp", "uc-library/include/presonus/dsp/Controller.hpp",
       "uc-library/include/presonus/dsp/IController.hpp")
BUILD = Path("temp/core-upstream/root-integration-01")
SDK = BUILD / "upstream-core/sdk"
FORMAT = ["uc-library/.venv/bin/clang-format", "--style=file", "--fallback-style=LLVM",
          "--dry-run", "--Werror", SOURCE, HEADER, REPLAY]
WRAPS = ["-Wl,--wrap=_ZdlPv", "-Wl,--wrap=_ZdlPvm"]
DOMAIN = ("Normal deleting destruction of one heap receiver with owned canonical AudioComponent "
          "and live controller, independent Audio destructor execution and legacy default lifecycle. "
          "Observes property/controller release and actual unsized outer deallocation.")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def commands(exe, obj):
    flags = ["/usr/bin/c++", "-std=c++20", "-O2", "-DNDEBUG", "-Ulinux",
             "-Iuc-library/include", "-isystem", str(SDK / "include/presonus-core-5")]
    units = [p for p in APP if p.endswith(".cpp")]
    objects = [str(Path(obj).parent / (Path(path).stem + ".o")) for path in units]
    archives = (BUILD / "libpresonus_rm_components.a", BUILD / "libpresonus_uc.a",
                SDK / "lib/libcorelib.a", SDK / "lib/libpresonus_core_allocator.a",
                BUILD / "private-glibc29-provider/libpresonus_private_glibc29.a")
    return [flags + ["-fno-sized-deallocation", "-c", SOURCE, "-o", obj],
            *(flags + ["-c", path, "-o", output] for path, output in zip(units, objects)),
            flags + [REPLAY, obj, *objects, *WRAPS, *map(str, archives),
                     "-l:libpng16.so.16", "-l:libz.so.1", "-lm", "-o", exe]]


def operations(case):
    return [event["operation"] for event in case["events"]
            if event["operation"] in {"property release", "controller release", "operator delete"}]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--exe", required=True)
    p.add_argument("--object", required=True)
    p.add_argument("--fixtures", required=True)
    p.add_argument("--integration", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--mode", choices=["compile", "symbols", "replay", "fresh"], default="replay")
    args = p.parse_args()
    fixture = json.loads(Path(args.fixtures).read_text())
    mangled = fixture["mangled"]
    if args.mode == "compile":
        for path in (args.exe, args.object):
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        for command in commands(args.exe, args.object):
            subprocess.run(command, check=True)
        return
    listing = subprocess.check_output(["nm", "--defined-only", args.object], text=True)
    if mangled not in {line.split()[-1] for line in listing.splitlines() if line.split()}:
        raise RuntimeError(f"Compiled symbol missing: {mangled}")
    relocations = subprocess.check_output(
        ["objdump", "-dr", "--disassemble=" + mangled, args.object], text=True)
    deletes = re.findall(r"\b_ZdlPv(?:m)?(?=[-+\s]|$)", relocations)
    if set(deletes) != {"_ZdlPv"}:
        raise RuntimeError(f"Expected exact unsized outer delete relocation: {deletes}")
    exe_symbols = subprocess.check_output(["nm", "--defined-only", args.exe], text=True)
    for dependency in fixture["dependency_ranges"]:
        if not any(line.endswith(" " + dependency["mangled"]) for line in exe_symbols.splitlines()):
            raise RuntimeError(f"Missing real provider {dependency['mangled']}")
    if args.mode == "symbols":
        print(mangled)
        return
    subprocess.run(FORMAT, check=True)
    if args.mode == "fresh":
        repeated = subprocess.check_output(
            ["uc-library/.venv/bin/python", "-B", REPLAY.replace("Replay.cpp", "native.py")],
            text=True, timeout=30)
        if json.loads(repeated) != fixture:
            raise RuntimeError("Fresh ARM observation differs from the sealed fixture")
    observations = {}
    for mode, expected in (("owned", operations(fixture["cases"][0])),
                           ("audio", operations(fixture["cases"][1])),
                           ("default", ["operator delete"])):
        observed = subprocess.check_output([args.exe, mode], text=True, timeout=20).splitlines()
        if observed != expected:
            raise RuntimeError(f"{mode} host lifecycle {observed} differs from {expected}")
        observations[mode] = observed
    sources = {name.removeprefix("uc-library/"): digest(name) for name in (SOURCE, HEADER)}
    row = dict(original_elf_sha256=fixture["elf_sha256"], mangled=mangled, domain=DOMAIN,
               cpp_compiled=True, mangling_namespace_checked=True, portable_ready=True,
               sources=sources, repository_sources={name: digest(name) for name in CORE})
    integration = Path(args.integration)
    proof = dict(passed=True, domain=DOMAIN, native_observation=fixture, native_case_count=len(observations),
                 replay_case_count=len(observations), observed=observations,
                 compiled_symbol=mangled, deleting_destructor_relocation="_ZdlPv",
                 application_providers={path: digest(path) for path in APP}, object_sha256=digest(args.object),
                 replay_sha256=digest(args.exe), fixture_sha256=digest(args.fixtures),
                 formatter_version=subprocess.check_output([FORMAT[0], "--version"], text=True).strip(),
                 integration_sha256=digest(integration) if integration.is_file() else None,
                 proposed_readiness=dict(ready=[row], pending=[]))
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(proof, indent=2) + "\n")
    print(f"{len(observations)} observed host lifecycle cases")


if __name__ == "__main__":
    main()
