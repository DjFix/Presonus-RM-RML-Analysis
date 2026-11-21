"""Compile and replay the independent original destructor observations."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

SOURCE = "uc-library/src/Presonus/Surface/SoloPageComponent.cpp"
HEADER = "uc-library/include/presonus/surface/SoloPageComponent.hpp"
REPLAY = "uc-library/tests/recovery/cycle21_g07_s03/Replay.cpp"
CORE = (
    "third_party/ccl-framework/core/portable/corecomponent.cpp",
    "third_party/ccl-framework/core/portable/corecomponent.h",
    "third_party/ccl-framework/core/public/corevector.h",
)
SDK = Path("temp/core-upstream/root-integration-01/upstream-core/sdk")
FORMAT = ["uc-library/.venv/bin/clang-format", "--style=file", "--fallback-style=LLVM",
          "--dry-run", "--Werror", SOURCE, HEADER, REPLAY]
WRAPS = ["-Wl,--wrap=_Znam,--wrap=_ZdaPv,--wrap=_ZdlPv,--wrap=_ZdlPvm"]
DOMAIN = ("One constructed receiver with nonempty alias storage, one CCL-owned child and "
          "a separately live borrowed alias, normal lifecycle only. Exact ARM entry and "
          "provider boundaries, storage disposal and host real deallocation observed.")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def commands(exe, obj):
    flags = ["/usr/bin/c++", "-std=c++17", "-O2", "-DNDEBUG", "-Ulinux", "-fno-rtti", "-fno-sized-deallocation",
             "-Iuc-library/include", "-isystem", str(SDK / "include/presonus-core-5")]
    return [flags + ["-c", SOURCE, "-o", obj],
            flags + [REPLAY, obj, *WRAPS, str(SDK / "lib/libcorelib.a"),
                     str(SDK / "lib/libpresonus_core_allocator.a"), "-o", exe]]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--exe", required=True)
    p.add_argument("--object", required=True)
    p.add_argument("--fixtures", required=True)
    p.add_argument("--integration", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--mode", choices=["compile", "symbols", "replay"], default="replay")
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
    if mangled.endswith("D0Ev"):
        relocations = subprocess.check_output(["objdump", "-dr", "--disassemble=" + mangled, args.object], text=True)
        import re
        deletes = re.findall(r"\b_ZdlPv(?:m)?(?=[-+\s]|$)", relocations)
        if set(deletes) != {"_ZdlPv"}:
            raise RuntimeError(f"D0 expected unsized operator delete relocation, observed {deletes}")
    if args.mode == "symbols":
        print(mangled)
        return
    subprocess.run(FORMAT, check=True)
    variant = "D0" if mangled.endswith("D0Ev") else "D1"
    case = fixture["cases"][0]
    observed = subprocess.check_output([args.exe, variant], text=True).split()
    fields = ["vector_storage_released", "child_destroyed", "receiver_released", "borrowed_preserved"]
    expected = [str(int(case[field])) for field in fields]
    if observed != expected:
        raise RuntimeError(f"{variant} actual lifecycle {observed} differs from {expected}")
    sources = {name.removeprefix("uc-library/"): digest(name) for name in (SOURCE, HEADER)}
    row = dict(original_elf_sha256=fixture["elf_sha256"], mangled=mangled, domain=DOMAIN,
               cpp_compiled=True, mangling_namespace_checked=True, portable_ready=True,
               sources=sources, repository_sources={name: digest(name) for name in CORE})
    integration = Path(args.integration)
    proof = dict(passed=True, domain=DOMAIN, native_observation=fixture, native_case_count=1,
                 replay_case_count=1, observed=dict(zip(fields, observed)),
                 compiled_symbol=mangled, deleting_destructor_relocation="_ZdlPv" if variant == "D0" else None, object_sha256=digest(args.object),
                 replay_sha256=digest(args.exe), fixture_sha256=digest(args.fixtures),
                 formatter_version=subprocess.check_output([FORMAT[0], "--version"], text=True).strip(),
                 integration_sha256=digest(integration) if integration.is_file() else None,
                 proposed_readiness=dict(ready=[row], pending=[]))
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(proof, indent=2) + "\n")
    print(f"{variant}: 1 observed lifecycle case")


if __name__ == "__main__":
    main()
