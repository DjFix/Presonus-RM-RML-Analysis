"""Compile and replay the independent MainLCD view notifications."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

SOURCE = "uc-library/src/Presonus/MainLCDPageStack.cpp"
HEADER = "uc-library/include/presonus/MainLCDComponent.hpp"
REPLAY = "uc-library/tests/recovery/cycle21_g07_s08/Replay.cpp"
CORE = tuple("third_party/ccl-framework/core/portable/gui/" + name for name in (
    "coreview.h", "coreview.cpp", "coreviewshared.h",
))
SDK = Path("temp/core-upstream/root-integration-01/upstream-core/sdk")
FORMAT = ["uc-library/.venv/bin/clang-format", "--style=file", "--fallback-style=LLVM",
          "--dry-run", "--Werror", SOURCE, HEADER, REPLAY]
WRAPS = []
DOMAIN = ("Four offline view trees: empty or nested containers with a noncontainer leaf, "
          "with or without an owner at the root. Observed recursive dispatch, preorder "
          "notification and owner clearing before real CCL destruction.")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def commands(exe, obj):
    flags = ["/usr/bin/c++", "-std=c++17", "-O2", "-DNDEBUG", "-Ulinux", "-fno-rtti",
             "-Iuc-library/include", "-isystem", str(SDK / "include/presonus-core-5")]
    return [flags + ["-c", SOURCE, "-o", obj],
            flags + [REPLAY, obj, str(SDK / "lib/libcorelib.a"),
                     str(SDK / "lib/libpresonus_core_allocator.a"), "-l:libpng16.so.16", "-l:libz.so.1", "-o", exe]]


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
            [args.exe, str(int(case["nested"])), str(int(case["owner_present"]))],
            text=True, timeout=20).splitlines()
        expected = [",".join(case["notifications"]), ",".join(case["container_queries"])]
        if observed != expected:
            raise RuntimeError(f"Actual view cleanup {observed} differs from {expected}")
        observations.append(observed)
    sources = {name.removeprefix("uc-library/"): digest(name) for name in (SOURCE, HEADER)}
    row = dict(original_elf_sha256=fixture["elf_sha256"], mangled=mangled, domain=DOMAIN,
               cpp_compiled=True, mangling_namespace_checked=True, portable_ready=False,
               declaration_uncertainties=["The original ordinary return type is unencoded. "
                                          "No caller in the validated scope consumes a result; the source port uses void."],
               sources=sources, repository_sources={name: digest(name) for name in CORE})
    integration = Path(args.integration)
    proof = dict(passed=True, domain=DOMAIN, native_observation=fixture, native_case_count=len(observations),
                 replay_case_count=len(observations), observed=observations,
                 compiled_symbol=mangled, object_sha256=digest(args.object),
                 replay_sha256=digest(args.exe), fixture_sha256=digest(args.fixtures),
                 formatter_version=subprocess.check_output([FORMAT[0], "--version"], text=True).strip(),
                 integration_sha256=digest(integration) if integration.is_file() else None,
                 proposed_readiness=dict(ready=[], pending=[row]))
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(proof, indent=2) + "\n")
    print(f"{len(observations)} observed recursive view cleanup cases")


if __name__ == "__main__":
    main()
