"""Compile verified provider inputs or replay one exact Actual06 G01 task."""
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

from native import VARIANTS, capture


ROOT = Path(__file__).resolve().parents[4]
LIB = Path("uc-library")
INCLUDE = LIB / "include"
APP = LIB / "src/Presonus"
CORE = Path("third_party/ccl-framework/core")
TEST = Path(__file__).with_name("Replay.cpp").relative_to(ROOT)
FORMAT = [str(LIB / ".venv/bin/clang-format"), "--style=file", "--fallback-style=LLVM",
          "--dry-run", "--Werror"]
GROUPS = {
    "mackie": ("MackieControlComponent", "MackieControlComponent", "cs18"),
    "color": ("MappableMixer", "MappableMixer", "common"),
    "midi": ("Surface/MidiMixerHandler", "surface/MidiMixerHandler", "cs18"),
    "observer": ("Surface/SLMixerHandler", "surface/sl_mixer_encoder", "cs18"),
}
TASK_GROUPS = dict(zip(VARIANTS, ("mackie", "mackie", "color", "color", "midi", "midi",
                                  "observer", "observer", "observer")))
TARGET_PATHS = {g: (APP / (source + ".cpp"), INCLUDE / ("presonus/" + header + ".hpp"))
                for g, (source, header, _) in GROUPS.items()}
PROVIDERS = [APP / (x + ".cpp") for x in (
    "MackieControlModel", "MackieControlModelMappings", "Surface/MidiMixerLifecycle",
    "Surface/PanelRegistrarMidiDispatch", "Color/MixerColorConverter",
    "ColorMapping", "Color/ColorMappingName",
)]
OWNED = {x for group in TARGET_PATHS.values() for x in group} | {TEST}


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read(path):
    return json.loads(path.read_text())


def write(path, body):
    path.parent.mkdir(exist_ok=True, parents=True)
    path.write_text(json.dumps(body, indent=2) + "\n")


def run(argv, temp=None):
    env = os.environ | ({"TMPDIR": str(temp.resolve())} if temp else {})
    p = subprocess.run([str(x) for x in argv], cwd=ROOT, env=env, text=True,
                       capture_output=True, timeout=100)
    if p.returncode:
        raise RuntimeError(f"{argv!r}:\n{p.stdout}{p.stderr}")
    return p.stdout


def build(args):
    tick = time.monotonic()
    dest = args.build
    dest.mkdir(exist_ok=True, parents=True)
    bindings = read(args.bindings)
    overlay = dest / "frozen-headers"
    selected = {}
    for logical_text, row in bindings["dependencies"].items():
        logical, path = Path(logical_text), Path(row["path"])
        assert sha(path) == row["sha256"], logical
        if logical.is_relative_to(INCLUDE):
            link = overlay / logical.relative_to(INCLUDE)
            link.parent.mkdir(exist_ok=True, parents=True)
            if not link.is_symlink():
                link.symlink_to(path.resolve())
            assert link.resolve() == path.resolve()
            selected[link] = logical
        elif logical in PROVIDERS:
            selected[path] = logical
    assert sha(args.provider / "archive-receipt") == bindings["archive_receipt_sha256"]
    libraries = [args.provider / name for name in ("libcorelib.a", "libpresonus_core_allocator.a")]
    for path in libraries:
        assert sha(path) == bindings["libraries"][path.name]
    flags = ["-O3", "-std=c++20", "-fno-rtti", "-DNDEBUG=1", "-DCORE_USE_OPENSSL=1",
             "-DPRESONUS_HAS_UPSTREAM_CORE=1", "-Ulinux", "-pthread",
             "-I" + str(overlay), "-Iuc-library/include", "-isystem",
             "third_party/ccl-framework", "-ffunction-sections", "-fdata-sections"]
    commands, objects, closures = [], [], {}
    for source in ([paths[0] for paths in TARGET_PATHS.values()] + PROVIDERS + [TEST]):
        actual = bindings["dependencies"].get(str(source), {}).get("path", source)
        obj = dest / (source.stem + ".o")
        depfile = dest / (source.stem + ".d")
        argv = ["c++", *flags, "-MD", "-MF", depfile, "-c", actual, "-o", obj]
        run(argv, dest)
        deps = shlex.split(depfile.read_text().replace(chr(92) + chr(10), " ").split(":", 1)[1])
        closure = {}
        for x in sorted(set(deps)):
            path = Path(x)
            logical = selected.get(path, path)
            digest = sha(path)
            if logical not in OWNED and (logical.is_relative_to(INCLUDE) or
                                        logical.is_relative_to(CORE) or logical in PROVIDERS):
                assert digest == bindings["dependencies"][str(logical)]["sha256"], logical
            closure[x] = digest
        closures[str(source)] = {"depfile_sha256": sha(depfile), "inputs": closure}
        objects.append(obj)
        commands.append(list(map(str, argv)))
    argv = ["c++", *objects, *libraries, "-Wl,--gc-sections", "-pthread", "-ldl",
            "-o", dest / "Replay"]
    run(argv, dest)
    commands.append(list(map(str, argv)))
    write(dest / "commands.json", {
        "commands": commands, "depfile_closure": closures, "binding_sha256": sha(args.bindings),
        "compiler": run(["c++", "--version"]).splitlines()[0], "TMPDIR": str(dest.resolve()),
        "provider_archives": {str(path): sha(path) for path in libraries},
        "elapsed_seconds": time.monotonic() - tick,
    })


def symbols(obj, expected):
    names = {l.split()[-1] for l in run(["nm", "--defined-only", obj]).splitlines()
             if len(l.split()) == 3}
    assert expected <= names, expected - names
    return sorted(expected)


def domain(task):
    if task in ("s13", "s14"):
        return ("Both firmware roles, separately range-verified native null and two "
                "pointer identities, isolated read/write of converter field; real "
                "Linux MixerColorConverter objects, default null, identity, replacement, "
                "clearing, table isolation and borrowed lifetime.")
    return ("Exact CS18 native direct entry and indirect branch through the "
            "section-verified original vtable and RTTI. Trace stays in target, "
            "receiver and argument memory remain unchanged. Linux qualified calls "
            "and actual virtual member dispatch with typed state and fail-on-call "
            "service probes. No physical device operations.")


def replay(args):
    source_transition = load_transition(args.source_transition, args.source_transition_sha256)
    started = datetime.now(timezone.utc)
    group = TASK_GROUPS[args.task]
    selected = (*TARGET_PATHS[group], TEST)
    run([*FORMAT, *selected])
    fixture = read(args.fixture)
    assert capture(args.snapshot, args.reference, args.task) == fixture
    names = {r["target"]["mangled"] for r in fixture["originals"]}
    names = set(symbols(args.object, names))
    symbols(args.exe, names)
    stdout = run([args.exe.resolve(), args.task]).strip()
    assert stdout == args.task + " typed host replay passed"
    bindings = read(args.bindings)
    local_commands = args.object.parent / "commands.json"
    local = read(local_commands) if local_commands.is_file() else None
    if local:
        assert local["binding_sha256"] == sha(args.bindings)
    else:
        current_dependencies = {
            "uc-library/include/presonus/surface_panel/ControlGroup.hpp": (
                "85a4852beeb8a95c6e7e1725ca3c1310d926b098a8a9b1779a1abffe302696ae",
                "1b9182559e5c3d143f4a678fc5c04a3b38b6ef2188b01e215decb6480e429c08",
            ),
            "uc-library/include/presonus/PageComponent.hpp": (
                "54200b8d2ccb7d3568566c0703587e258f4f440045f126a5388a4000fd5b1bbb",
                "4564d19e2cc2b8c13d38697c89943c41947aa1af5f399b0e8079f919ae83e608",
            ),
            "uc-library/include/presonus/surface_panel/ControlHelpers.hpp": (
                "323e21a80647b72ccf179c0f2e8263e8b7e65c7d1196ba252fcb9f91e677fa8a",
                "d7d22daef66b840fe0f95d5d41c9a99100a9bfea6fb3348d915fd02c6308428a",
            ),
        }
        for logical, item in bindings["dependencies"].items():
            expected = item["sha256"]
            if logical in current_dependencies:
                previous, current = current_dependencies[logical]
                assert expected == previous and sha(item["path"]) == previous, logical
                expected = current
            expected = current_source_digest(logical, expected, source_transition)
            assert sha(logical) == expected, logical
    sources = {str(p.relative_to(LIB)): sha(p) for p in selected}
    core = {p: item["sha256"] for p, item in bindings["dependencies"].items()
            if Path(p).is_relative_to(CORE)}
    assert all(sha(p) == expected for p, expected in core.items())
    scope = domain(args.task)
    uncertainties = ["Original return declaration is unencoded. Portable signature choice is bounded."]
    limits = uncertainties + [
        "ARM layout, other vtable slots, hardware and runtime interoperability remain unverified."
    ]
    if args.task == "s19":
        limits.append("ReplaceArgs is an empty typed portable argument; original fields and layout remain unresolved.")
    rows = [{
        "original_elf_sha256": r["elf_sha256"], "mangled": r["target"]["mangled"], "sources": sources,
        "repository_sources": core, "cpp_compiled": True,
        "mangling_namespace_checked": True, "portable_ready": False,
        "validation_domain": scope, "declaration_uncertainties": uncertainties,
    } for r in fixture["originals"]]
    write(args.out, {
        "archive_source_transition": {"path": str(args.source_transition),
            "sha256": args.source_transition_sha256} if args.source_transition else None,
        "success": True, "cpp_differential_passed": True, "compiled_mangled_names_matched": True,
        "portable_ready": False, "mangled_names": sorted(names), "domain": scope, "validation_domain": scope,
        "functions": rows, "proposed_readiness": {"ready": [], "pending": rows},
        "limitations": limits, "sources": sources, "repository_sources": core,
        "format": {"format_check_passed": True, "version": run([FORMAT[0], "--version"]).strip(),
                   "files": {str(path): sha(path) for path in selected}},
        "core_commit": "e8cbdea4a4a20e15111f5a690798a259c0374b31",
        "native": fixture, "host_stdout": stdout, "native_case_count": sum(len(r["cases"]) for r in fixture["originals"]),
        "replay_argv": sys.argv, "native_producer_sha256": sha(Path(__file__).with_name("native.py")),
        "replay_producer_sha256": sha(__file__), "fixture_sha256": sha(args.fixture),
        "compiled_object_sha256": sha(args.object), "executable_sha256": sha(args.exe),
        "integration_sha256": sha(args.integration), "provider_binding_sha256": sha(args.bindings),
        "canonical_dependency_transition": current_dependencies if not local else None,
        "local_compile": local, "provider_session_id": os.getenv("CODEX_THREAD_ID"),
        "replay_start_utc": started.isoformat(), "replay_end_utc": datetime.now(timezone.utc).isoformat(),
    })
    print(stdout)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--task", choices=VARIANTS)
    p.add_argument("--symbols", action="store_true")
    for name in ("build", "provider", "bindings", "snapshot", "reference", "fixture", "exe",
                 "object", "integration", "out"):
        p.add_argument("--" + name, type=Path)
    p.add_argument("--source-transition", type=Path)
    p.add_argument("--source-transition-sha256")
    args = p.parse_args()
    if args.build:
        build(args)
    elif args.symbols:
        print(symbols(args.object, {r["target"]["mangled"] for r in read(args.fixture)["originals"]}))
    else:
        replay(args)


if __name__ == "__main__":
    main()
