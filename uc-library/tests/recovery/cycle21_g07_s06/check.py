"""Compile and replay the independent MonoBus callback."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

SOURCE = "uc-library/src/Presonus/Mixer/MonoBusComponent.cpp"
HEADER = "uc-library/include/presonus/mixer/MonoBusComponent.hpp"
REPLAY = "uc-library/tests/recovery/cycle21_g07_s06/Replay.cpp"
CORE = tuple("third_party/ccl-framework/core/portable/" + name for name in (
    "corecomponent.cpp", "corecomponent.h", "coreparams.cpp", "coreparams.h", "coreparaminfo.h",
))
APP = ("uc-library/include/presonus/mixer/ChannelComponent.hpp",
       "uc-library/include/presonus/mixer/SendOutputComponent.hpp",
       "uc-library/include/presonus/mixer/OutputComponent.hpp",
       "uc-library/src/Presonus/Mixer/SendOutputComponent.cpp",
       "uc-library/src/Presonus/Mixer/OutputComponent.cpp")
SDK = Path("temp/core-upstream/root-integration-01/upstream-core/sdk")
FORMAT = ["uc-library/.venv/bin/clang-format", "--style=file", "--fallback-style=LLVM",
          "--dry-run", "--Werror", SOURCE, HEADER, REPLAY]
WRAPS = []
DOMAIN = ("Fourteen local MonoBus cases with actual send/output delegation, dirty flags across "
          "three typed groups, numeric pair assignment, CCL string order and actual range alias "
          "effects across positive, zero, missing and inactive branches. Bounded offline state.")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def commands(exe, obj):
    flags = ["/usr/bin/c++", "-std=c++20", "-O2", "-DNDEBUG", "-Ulinux",
             "-Iuc-library/include", "-isystem", str(SDK / "include/presonus-core-5")]
    build = SDK.parent.parent
    units = [path for path in APP if path.endswith(".cpp")]
    objects = [str(Path(obj).parent / (Path(path).stem + ".o")) for path in units]
    archives = (build / "libpresonus_rm_components.a", build / "libpresonus_uc.a",
                SDK / "lib/libcorelib.a", SDK / "lib/libpresonus_core_allocator.a",
                build / "private-glibc29-provider/libpresonus_private_glibc29.a")
    return [flags + ["-c", SOURCE, "-o", obj],
            *(flags + ["-c", path, "-o", output] for path, output in zip(units, objects)),
            flags + ["-fno-rtti", REPLAY, obj, *objects, *map(str, archives),
                     "-l:libpng16.so.16", "-l:libz.so.1", "-lm", "-o", exe]]


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
        observed = subprocess.check_output(
            [args.exe, *(str(int(value)) for value in case["inputs"])],
            text=True, timeout=20).splitlines()
        expected = [" ".join(map(str, event)) for event in case["trace"]
                    if event[0] in ("send", "name")]
        expected.append("dirty " + " ".join(map(str, case["dirty"])))
        expected.append("splits " + " ".join(f"{value:.2f}" for value in case["splits"]))
        expected.extend("value " + name for name in case["names"])
        expected.append(f"alias {case['minimum']} {case['resets']}")
        if observed != expected:
            raise RuntimeError(f"Actual MonoBus state {observed} differs from {expected}")
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
    print(f"{len(observations)} observed MonoBus parameter cases")


if __name__ == "__main__":
    main()
