"""Build local replay, or verify a supplied production object and replay."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

from native import PREFIX, capture


ROOT = Path(__file__).resolve().parents[4]
HEADER = "uc-library/include/presonus/surface/DAWMixerHandler.hpp"
SOURCE = "uc-library/src/Presonus/Surface/DAWMixerHandler.cpp"
ACTIVATION = "uc-library/src/Presonus/Surface/DAWMixerActivation.cpp"
TEST = str(Path(__file__).with_name("Replay.cpp").relative_to(ROOT))
CORE_PARAM_D1 = "_ZN4Core8Portable9ParamListD1Ev"
CORE_DEPS = [
    "third_party/ccl-framework/core/portable/coreparams.h",
    "third_party/ccl-framework/core/portable/coreparams.cpp",
    "third_party/ccl-framework/core/portable/coreparaminfo.h",
    "third_party/ccl-framework/core/portable/coretypeinfo.h",
    "third_party/ccl-framework/core/public/corevector.h",
]
FORMAT = "uc-library/.venv/bin/clang-format"
DOMAIN = (
    "CS18AI normal destructor on two initialized receiver backgrounds, with separately "
    "range-verified C1 and C2 initialized-guard traces stopped at the same typed member "
    "constructor boundary. Linux exact compiler destructor entry with 0, 1 and 4 "
    "real CCL parameters in owned and caller-owned lists, direct standalone provider "
    "teardown observation, getter and automation behavior, and receiver-specific "
    "deallocation order via the forwarding unsized delete probe."
)
LIMITS = [
    "Portable typed ownership and normal teardown. ARM layout, inheritance and exception unwinding remain unresolved.",
    "Native CCL is intercepted at its original call boundary. D0 reaches its original "
    "import, where the controlled allocator shim unmaps the receiver. Real host "
    "allocator execution and CCL parameter destruction are observed independently.",
    "Native C1 and C2 are observed for member placement only. No constructor readiness is proposed.",
]


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def run(argv):
    return subprocess.run(
        [str(x) for x in argv], cwd=ROOT, check=True, capture_output=True,
        text=True, timeout=120,
    ).stdout


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def build(args):
    dest = args.build
    dest.mkdir(parents=True, exist_ok=True)
    flags = [
        "-std=c++17", "-O3", "-DNDEBUG=1", "-DCORE_USE_OPENSSL=1",
        "-DPRESONUS_HAS_UPSTREAM_CORE=1", "-pthread", "-Ulinux",
        "-fno-sized-deallocation", "-Iuc-library/include", "-isystem",
        "third_party/ccl-framework",
    ]
    corelib = args.provider / "libcorelib.a"
    allocator = args.provider / "libpresonus_core_allocator.a"
    provider = {str(p): sha(p) for p in (
        corelib, allocator, args.provider / "archive-receipt",
        args.provider / "archive-start", args.provider / "archive-end",
    )}
    assert provider[str(corelib)] == "3c4f0825acb529fda135587b7ff5cb92ca0100bb417a20c034d3fdef80a93e0c"
    assert provider[str(allocator)] == "69892fbcec9a50a140462982073c686a67ca4763dfb5dfa190534d022b78a40d"
    commands, objects = [], []
    for source in (SOURCE, ACTIVATION, TEST):
        obj = str(dest / (Path(source).stem + ".o"))
        cmd = ["c++", *flags, "-MD", "-MF", obj + ".d", "-c", source, "-o", obj]
        run(cmd)
        commands.append(cmd)
        objects.append(obj)
    cmd = ["c++", *objects, str(corelib), str(allocator), "-Wl,--wrap=_ZdlPv",
           "-ldl", "-pthread", "-o", str(dest / "Replay")]
    run(cmd)
    commands.append(cmd)
    write(dest / "commands.json", {"commands": commands, "provider": provider})


def symbol_receipt(obj, variant):
    selected = PREFIX + variant + "Ev"
    names = {}
    for line in run(["nm", "--defined-only", obj]).splitlines():
        fields = line.split()
        if len(fields) == 3:
            names[fields[-1]] = (fields[0], fields[1])
    assert names[selected][1] in ("T", "W")
    disassembly = run(["objdump", "-drw", obj])
    chosen = selected
    if variant != "D0" and f"<{selected}>:" not in disassembly:
        alias = PREFIX + ("D2" if variant == "D1" else "D1") + "Ev"
        assert names[selected][0] == names[alias][0]
        chosen = alias
    match = re.search(rf"<{chosen}>:\n(.*?)(?:\n\n|\Z)", disassembly, re.S)
    assert match, chosen
    scoped_body = match.group(1)
    assert CORE_PARAM_D1 in scoped_body
    assert "_ZdlPvm" not in scoped_body
    assert bool(re.search(r"\b_ZdlPv(?:[-+]|\b)", scoped_body)) == (variant == "D0")
    return {"original_name": selected, "disassembled_name": chosen,
            "address": names[selected][0], "scoped_body": scoped_body}


def replay(args):
    started = datetime.now(timezone.utc)
    run([FORMAT, "--style=file", "--fallback-style=LLVM", "--dry-run",
         "--Werror", HEADER, SOURCE, TEST])
    formatted = {source: sha(source) for source in (HEADER, SOURCE, TEST)}
    symbols = symbol_receipt(args.object, args.variant)
    fixture = json.loads(args.fixture.read_text())
    fresh = capture(args.inventory, args.elf, args.variant)
    assert fresh == fixture, "Fresh original ELF observations differ from fixture"
    assert CORE_PARAM_D1 in run(["nm", "--defined-only", args.exe])
    stdout = run([args.exe.resolve(), args.variant]).splitlines()
    expected = [
        f"{args.variant} {ownership} {count} {int(args.variant == 'D0')}"
        for count in (0, 1, 4) for ownership in ("owned", "borrowed")
    ]
    assert stdout == expected, (stdout, expected)
    sources = {p.removeprefix("uc-library/"): sha(p) for p in
               (SOURCE, HEADER, ACTIVATION, TEST)}
    providers = {p: sha(p) for p in CORE_DEPS}
    symbol = symbols["original_name"]
    elf_sha = fresh["elf"]["sha256"]
    domain = DOMAIN
    if args.variant == "D0":
        domain += (" The original D0 import sees the same receiver and the allocator shim "
                   "unmaps its region. A post-return read must fail with UC_ERR_READ_UNMAPPED.")
    function = {
        "original_elf_sha256": elf_sha,
        "mangled": symbol,
        "sources": sources,
        "repository_sources": providers,
        "cpp_compiled": True,
        "mangling_namespace_checked": True,
        "portable_ready": True,
        "validation_domain": domain,
    }
    local_commands = args.object.parent / "commands.json"
    proof = {
        "success": True,
        "cpp_differential_passed": True,
        "compiled_mangled_names_matched": True,
        "portable_ready": True,
        "mangled_names": [symbol],
        "original_elf_sha256": elf_sha,
        "domain": domain,
        "validation_domain": domain,
        "functions": [function],
        "proposed_readiness": {"ready": [function], "pending": []},
        "sources": sources,
        "repository_sources": providers,
        "format": {"format_check_passed": True, "files": formatted,
                   "version": run([FORMAT, "--version"]).strip()},
        "core_commit": "e8cbdea4a4a20e15111f5a690798a259c0374b31",
        "compile": json.loads(local_commands.read_text()) if local_commands.is_file()
                   else "Supplied canonical built executable and production object",
        "symbols": symbols,
        "native": fresh,
        "native_case_count": len(fresh["observations"][args.variant]["cases"]),
        "constructor_placement_case_count": 4,
        "host_case_count": len(stdout),
        "host_results": stdout,
        "fixture_sha256": sha(args.fixture),
        "checker_sha256": sha(__file__),
        "oracle_producer_sha256": sha(Path(__file__).with_name("native.py")),
        "object_sha256": sha(args.object),
        "executable_sha256": sha(args.exe),
        "integration_sha256": sha(args.integration),
        "replay_argv": sys.argv,
        "limitations": LIMITS,
        "replay_start_utc": started.isoformat(),
        "replay_end_utc": datetime.now(timezone.utc).isoformat(),
    }
    write(args.out, proof)
    print(f"{symbol}: 2 native destructor, 4 constructor placement, 6 Linux cases")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path)
    parser.add_argument("--provider", type=Path)
    parser.add_argument("--symbols", action="store_true")
    parser.add_argument("--variant", choices=("D1", "D2", "D0"))
    for option in ("exe", "object", "integration", "out", "elf", "inventory", "fixture"):
        parser.add_argument("--" + option, type=Path)
    args = parser.parse_args()
    if args.build:
        build(args)
    elif args.symbols:
        print(json.dumps(symbol_receipt(args.object, args.variant)))
    else:
        replay(args)


if __name__ == "__main__":
    main()
