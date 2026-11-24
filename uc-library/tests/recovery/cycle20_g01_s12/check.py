"""Check actual constructor symbols, native fixtures and Linux owned/borrowed behavior."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from canonical_source_transition import current_source_digest, load_transition
import time

from native import capture, NAMES


ROOT = Path(__file__).resolve().parents[4]
TEST = Path(__file__).with_name("Replay.cpp").relative_to(ROOT)
SOURCE = Path("uc-library/src/Presonus/AssignmentHandlerTable.cpp")
HEADER = Path("uc-library/include/presonus/surface/AssignmentHandlerTable.hpp")
REGISTRATION = Path("uc-library/src/Presonus/AssignmentHandlerRegistration.cpp")
HANDLER = Path("uc-library/src/Presonus/Surface/SLMixerEncoder.cpp")
CORE = Path("third_party/ccl-framework/core")
VECTOR = CORE / "public/corevector.h"
FORMAT = ["uc-library/.venv/bin/clang-format", "--style=file", "--fallback-style=LLVM",
          "--dry-run", "--Werror"]
DOMAIN = (
    "Six ARM executions per separately mapped constructor across three receiver fills "
    "and two placements; observe exactly the self-relative array pointer and zero count, "
    "no additional object writes, and normal return. Linux executes both exact compiler "
    "constructor entries with an empty pinned CCL vector, then actual table insertion, "
    "lookup, traversal and removal; verify independent owned tables and copies, borrowed "
    "alias preservation, and non-owning handler lifetime."
)
LIMITS = [
    "Portable initialized empty-container semantics. Original inline-array layout, "
    "ARM ABI, allocator implementation details and later application call sites are outside scope.",
    "Linux compiler may alias C1/C2. Individual original ARM ranges are distinct "
    "and each is independently replayed.",
]


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read(path):
    return json.loads(path.read_text())


def write(path, body):
    path.parent.mkdir(exist_ok=True, parents=True)
    path.write_text(json.dumps(body, indent=2) + "\n")


def run(argv, tmp=None):
    env = os.environ | ({"TMPDIR": str(tmp.resolve())} if tmp else {})
    proc = subprocess.run([str(x) for x in argv], cwd=ROOT, env=env, text=True,
                          capture_output=True, timeout=100)
    if proc.returncode:
        raise RuntimeError(f"{argv!r}:\n{proc.stdout}{proc.stderr}")
    return proc.stdout


def build(args):
    start = time.monotonic()
    dest = args.build
    dest.mkdir(exist_ok=True, parents=True)
    bindings = read(args.bindings)
    frozen = {}
    include = dest / "verified-include"
    inputs = Path("uc-library/include")
    for text, record in bindings["dependencies"].items():
        logical, frozen_path = Path(text), Path(record["path"])
        assert digest(frozen_path) == record["sha256"], logical
        if logical.is_relative_to(inputs):
            link = include / logical.relative_to(inputs)
            link.parent.mkdir(exist_ok=True, parents=True)
            if not link.is_symlink():
                link.symlink_to(frozen_path.resolve())
            assert link.resolve() == frozen_path.resolve()
            frozen[link] = logical
    registration = Path(bindings["dependencies"][str(REGISTRATION)]["path"])
    frozen[registration] = REGISTRATION
    handler = Path(bindings["dependencies"][str(HANDLER)]["path"])
    frozen[handler] = HANDLER
    assert digest(args.provider / "archive-receipt") == bindings["archive_receipt_sha256"]
    libraries = [args.provider / name for name in ("libcorelib.a", "libpresonus_core_allocator.a")]
    for path in libraries:
        assert digest(path) == bindings["libraries"][path.name]

    cflags = ["-O3", "-std=c++20", "-fno-rtti", "-DNDEBUG=1", "-DCORE_USE_OPENSSL=1",
              "-DPRESONUS_HAS_UPSTREAM_CORE=1", "-Ulinux", "-pthread", "-I" + str(include),
              "-ffunction-sections", "-fdata-sections", "-Iuc-library/include", "-isystem", "third_party/ccl-framework"]
    commands, objects, depfiles = [], [], {}
    for source in (SOURCE, registration, handler, TEST):
        obj = dest / (source.name + ".o")
        depfile = dest / (source.name + ".d")
        argv = ["c++", *cflags, "-MD", "-MF", depfile, "-c", source, "-o", obj]
        run(argv, dest)
        commands.append(list(map(str, argv)))
        objects.append(obj)
        deps = shlex.split(depfile.read_text().replace(chr(92) + chr(10), " ").split(":", 1)[1])
        closure = {}
        for item in sorted(set(deps)):
            path = Path(item)
            logical = frozen.get(path, path)
            sha = digest(path)
            if logical not in (HEADER, SOURCE, TEST) and (
                logical.is_relative_to(inputs) or logical.is_relative_to(CORE) or
                logical in (REGISTRATION, HANDLER)
            ):
                assert sha == bindings["dependencies"][str(logical)]["sha256"], logical
            closure[item] = sha
        depfiles[str(source)] = {"sha256": digest(depfile), "inputs": closure}
    argv = ["c++", *objects, *libraries, "-Wl,--gc-sections", "-pthread", "-ldl", "-o", dest / "Replay"]
    run(argv, dest)
    commands.append(list(map(str, argv)))
    write(dest / "commands.json", {
        "argv": commands, "compiler_depfile_closure": depfiles, "TMPDIR": str(dest.resolve()),
        "elapsed_seconds": time.monotonic() - start, "binding_sha256": digest(args.bindings),
        "compiler": run(["c++", "--version"]).splitlines()[0],
        "provider_libraries": {str(p): digest(p) for p in libraries},
    })


def symbols(obj):
    table = {}
    for row in run(["nm", "--defined-only", obj]).splitlines():
        fields = row.split()
        if len(fields) == 3 and fields[-1] in NAMES:
            assert fields[1] in ("T", "W")
            table[fields[-1]] = fields[0]
    assert set(table) == set(NAMES)
    return table


def replay(args):
    source_transition = load_transition(args.source_transition, args.source_transition_sha256)
    started = datetime.now(timezone.utc)
    format_paths = (SOURCE, HEADER, TEST)
    run([*FORMAT, *format_paths])
    fixture = read(args.fixture)
    assert capture(args.elf, args.reference) == fixture
    bindings = read(args.bindings)
    mangled = symbols(args.object)
    assert symbols(args.exe)
    host = run([args.exe.resolve()]).splitlines()
    assert host == ["C1 empty owned isolated non-owning", "C2 empty owned isolated non-owning",
                    "borrowed shared non-owning"]
    local = args.object.parent / "commands.json"
    local_receipt = read(local) if local.is_file() else None
    if local_receipt:
        assert local_receipt["binding_sha256"] == digest(args.bindings)
    else:
        current_dependency = {
            "uc-library/include/presonus/surface/sl_mixer_encoder.hpp":
                ("e9e0415a8f0d8b0a3bd15cf9dfe8eec37f3ae838d75da3d67f2a1e017b17b4fa",
                 "fd181be8e86d20f1e6376e607f80b3abfe35765d73559b0a539b3f462a870791"),
        }
        for logical, entry in bindings["dependencies"].items():
            expected = entry["sha256"]
            if logical in current_dependency:
                previous, current = current_dependency[logical]
                assert expected == previous, logical
                assert digest(entry["path"]) == previous, logical
                expected = current
            expected = current_source_digest(logical, expected, source_transition)
            assert digest(logical) == expected, logical
    sources = {str(p.relative_to("uc-library")): digest(p) for p in format_paths}
    if not local_receipt:
        sources[str(REGISTRATION.relative_to("uc-library"))] = digest(REGISTRATION)
    core = {p: record["sha256"] for p, record in bindings["dependencies"].items()
            if Path(p).is_relative_to(CORE)}
    assert str(VECTOR) in core
    assert all(digest(p) == expected for p, expected in core.items())
    originals = [{
        "original_elf_sha256": fixture["elf_sha256"], "mangled": name, "sources": sources,
        "repository_sources": core, "cpp_compiled": True,
        "mangling_namespace_checked": True, "portable_ready": True, "validation_domain": DOMAIN,
    } for name in NAMES]
    write(args.out, {
        "archive_source_transition": {"path": str(args.source_transition),
            "sha256": args.source_transition_sha256} if args.source_transition else None,
        "success": True, "cpp_differential_passed": True, "portable_ready": True,
        "compiled_mangled_names_matched": True, "mangled_names": NAMES,
        "original_elf_sha256": fixture["elf_sha256"], "domain": DOMAIN,
        "validation_domain": DOMAIN, "limitations": LIMITS, "functions": originals,
        "proposed_readiness": {"ready": originals, "pending": []},
        "sources": sources, "repository_sources": core,
        "format": {"format_check_passed": True, "version": run([FORMAT[0], "--version"]).strip(),
                   "files": {str(p): digest(p) for p in format_paths}},
        "core_commit": "e8cbdea4a4a20e15111f5a690798a259c0374b31",
        "native": fixture, "host_trace": host, "host_cases": len(host), "native_cases": 12,
        "mangling_symbol_addresses": mangled, "object_sha256": digest(args.object),
        "executable_sha256": digest(args.exe), "integration_sha256": digest(args.integration),
        "fixture_sha256": digest(args.fixture), "bindings": bindings,
        "binding_sha256": digest(args.bindings), "local_compile": local_receipt,
        "canonical_dependency_transition": current_dependency if not local_receipt else None,
        "native_producer_sha256": digest(Path(__file__).with_name("native.py")),
        "replay_producer_sha256": digest(__file__), "replay_argv": sys.argv,
        "provider_session_id": os.getenv("CODEX_THREAD_ID"),
        "replay_start_utc": started.isoformat(),
        "replay_end_utc": datetime.now(timezone.utc).isoformat(),
    })
    print("12 native observations and 3 Linux cases passed for the exact C1/C2 identities")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbols", action="store_true")
    for name in ("build", "provider", "bindings", "fixture", "exe", "object",
                 "elf", "reference", "integration", "out"):
        parser.add_argument("--" + name, type=Path)
    parser.add_argument("--source-transition", type=Path)
    parser.add_argument("--source-transition-sha256")
    args = parser.parse_args()
    if args.build:
        build(args)
    elif args.symbols:
        print(json.dumps(symbols(args.object)))
    else:
        replay(args)


if __name__ == "__main__":
    main()
