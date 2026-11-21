"""Compile and replay the independent Solo callbacks."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

SOURCE = "uc-library/src/Presonus/Surface/SoloPageComponent.cpp"
HEADER = "uc-library/include/presonus/surface/SoloPageComponent.hpp"
REPLAY = "uc-library/tests/recovery/cycle21_g07_s02/Replay.cpp"
CORE = tuple("third_party/ccl-framework/core/portable/" + name for name in (
    "corecomponent.cpp", "corecomponent.h", "coreparams.cpp", "coreparams.h", "coreparaminfo.h",
))
APP = ("uc-library/include/presonus/MixerClientComponentBase.hpp",
       "uc-library/include/presonus/mixer_state/MixerState.hpp",
       "uc-library/src/Presonus/MixerClientComponentBase.cpp")
SDK = Path("temp/core-upstream/root-integration-01/upstream-core/sdk")
FORMAT = ["uc-library/.venv/bin/clang-format", "--style=file", "--fallback-style=LLVM",
          "--dry-run", "--Werror", SOURCE, HEADER, REPLAY]
WRAPS = []
DOMAIN = ("Local CCL channel group trees with missing mixer, groups or per-channel solo, "
          "and message/tag checks around exact ARM positive threshold. Valid receiver state "
          "and real parameter default resets, ordered observer calls and absent paths.")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def commands(exe, obj):
    flags = ["/usr/bin/c++", "-std=c++20", "-O2", "-DNDEBUG", "-Ulinux",
             "-Iuc-library/include", "-isystem", str(SDK / "include/presonus-core-5")]
    provider = str(Path(obj).parent / "MixerClientComponentBase.o")
    archives = (SDK.parent.parent / "libpresonus_cs18_components.a",
                SDK.parent.parent / "libpresonus_uc.a", SDK / "lib/libcorelib.a",
                SDK / "lib/libpresonus_core_allocator.a")
    return [flags + ["-fno-sized-deallocation", "-c", SOURCE, "-o", obj],
            flags + ["-c", APP[-1], "-o", provider],
            flags + [REPLAY, obj, provider, *map(str, archives),
                     "-l:libpng16.so.16", "-l:libz.so.1", "-o", exe]]


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
    observations = []
    for case in fixture["cases"]:
        message = case["message"] if case["message"] is not None else -1
        observed = subprocess.check_output(
            [args.exe, str(case["mode"]), str(message), str(case["tag"]), str(case["value_bits"])],
            text=True, timeout=20).splitlines()
        expected = [f"{name} {value}" for name, value in case["trace"]
                    if name in ("group", "line", "aux", "button")]
        if case["mode"] == 2:
            reset_names = {event[0] for event in case["trace"]}
            expected.append(f"state {1 if 'line' in reset_names else 3} {1 if 'aux' in reset_names else 3}")
        if observed != expected:
            raise RuntimeError(f"Actual Solo calls and parameter states {observed} differ from {expected}")
        observations.append(observed)
    sources = {name.removeprefix("uc-library/"): digest(name) for name in (SOURCE, HEADER)}
    row = dict(original_elf_sha256=fixture["elf_sha256"], mangled=mangled, domain=DOMAIN,
               cpp_compiled=True, mangling_namespace_checked=True, portable_ready=True,
               sources=sources, repository_sources={name: digest(name) for name in CORE})
    integration = Path(args.integration)
    proof = dict(passed=True, domain=DOMAIN, native_observation=fixture, native_case_count=len(observations),
                 replay_case_count=len(observations), observed=observations,
                 compiled_symbol=mangled, application_dependencies={path: digest(path) for path in APP}, object_sha256=digest(args.object),
                 replay_sha256=digest(args.exe), fixture_sha256=digest(args.fixtures),
                 formatter_version=subprocess.check_output([FORMAT[0], "--version"], text=True).strip(),
                 integration_sha256=digest(integration) if integration.is_file() else None,
                 proposed_readiness=dict(ready=[row], pending=[]))
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(proof, indent=2) + "\n")
    print(f"{len(observations)} observed Solo parameter cases")


if __name__ == "__main__":
    main()
