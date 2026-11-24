"""Build against exact frozen dependencies and compare rendered traffic to ARM."""
import argparse
import datetime
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from canonical_source_transition import current_source_digest, load_transition
import time

from native import capture, sha


ROOT = Path(__file__).resolve().parents[4]
ASSIGNED = Path("/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling200-02/agent-repos04/daw_maps183")
SRC = Path("uc-library/src/ColorButton.cpp")
HDR = Path("uc-library/include/presonus/ColorButton.hpp")
TEST = Path(__file__).with_name("Replay.cpp").relative_to(ROOT)
CORE = Path("third_party/ccl-framework/core")
INCLUDE = Path("uc-library/include")
FORMAT = ["uc-library/.venv/bin/clang-format", "--style=file", "--fallback-style=LLVM",
          "--dry-run", "--Werror", str(SRC), str(HDR), str(TEST)]
SYMBOL = "_ZN11ColorButton4drawERKN4Core8Portable9DrawEventE"
DOMAIN = (
    "Eight exact CS18 native draw cases and all five section-verified indirect slots; "
    "observe blank selection or rejected channel type, background color, positive and negative "
    "nonzero color indices, single-frame and divided three-frame bitmaps, and focus gating. "
    "Linux uses actual selected channel and color accessors, pinned CCL style, bitmap, graphics "
    "and focus renderer, and compares rendering output to recorded ARM boundary traffic."
)
LIMITS = [
    "Native Core, selection, RTTI and graphics provider calls are controlled boundaries. "
    "Linux uses pinned Core independently; no original ARM provider execution or ABI/layout claim.",
    "The native rejection of a selected non-channel is modeled through the actual typed selection "
    "provider ignoring non-channel children. Native malformed host objects are outside scope.",
    "The portable declaration overrides the pinned Control draw as void; exact original "
    "unencoded return declaration remains unresolved.",
]


def run(argv, *, stdin=None, scratch=None):
    env = os.environ | ({"TMPDIR": str(scratch.resolve())} if scratch else {})
    result = subprocess.run(list(map(str, argv)), cwd=ROOT, env=env, input=stdin,
                            capture_output=True, text=True, timeout=100)
    if result.returncode:
        raise RuntimeError(f"{argv!r}:\n{result.stdout}{result.stderr}")
    return result.stdout


def read(p):
    return json.loads(p.read_text())


def dump(p, d):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(d, indent=2) + "\n")


def build(args):
    assert Path.cwd() == ROOT == ASSIGNED
    assert Path(run(["git", "rev-parse", "--show-toplevel"]).strip()) == ASSIGNED
    start = time.monotonic()
    scratch = args.build
    scratch.mkdir(parents=True, exist_ok=True)
    bindings = read(args.bindings)
    files = bindings["files"]
    overlay = scratch / "frozen-includes"
    aliases = {}
    for logical, row in files.items():
        assert sha(Path(row["path"])) == row["sha256"], logical
    for name in bindings["overlay_headers"]:
        path = Path(files[name]["path"])
        link = overlay / Path(name).relative_to(INCLUDE)
        link.parent.mkdir(exist_ok=True, parents=True)
        if not link.is_symlink():
            link.symlink_to(path)
        assert link.resolve() == path.resolve()
        aliases[str(link)] = name
    sources = [SRC, TEST] + [Path(files[p]["path"]) for p in bindings["compile_providers"]]
    aliases.update({files[p]["path"]: p for p in bindings["compile_providers"]})
    assert sha(args.provider / "copy-receipt.json") == bindings["archive_receipt_sha256"]
    libraries = [args.provider / n for n in ("libcorelib.a", "libpresonus_core_allocator.a")]
    assert all(sha(p) == bindings["libraries"][p.name] for p in libraries)
    flags = ["-std=c++20", "-O3", "-DNDEBUG=1", "-fno-rtti", "-DCORE_USE_OPENSSL=1",
             "-DPRESONUS_HAS_UPSTREAM_CORE=1", "-Ulinux", "-pthread", "-I" + str(overlay),
             "-Iuc-library/include", "-isystem", "third_party/ccl-framework",
             "-ffunction-sections", "-fdata-sections"]
    commands, depfiles, objects = [], {}, []
    for source in sources:
        obj = scratch / (source.stem + ".o")
        depfile = obj.with_suffix(".d")
        argv = ["c++", *flags, "-MD", "-MF", depfile, "-c", source, "-o", obj]
        run(argv, scratch=scratch)
        hashes = {}
        deps = shlex.split(depfile.read_text().replace(chr(92) + chr(10), " ").split(":",1)[1])
        for path in deps:
            logical = aliases.get(path,path)
            h = sha(Path(path))
            if logical in files:
                assert h == files[logical]["sha256"], logical
            elif Path(logical).is_relative_to(CORE) or Path(logical).is_relative_to(INCLUDE):
                assert Path(logical) == HDR, logical
            hashes[path] = h
        commands.append(list(map(str,argv)))
        depfiles[str(source)] = {"depfile_sha256":sha(depfile), "inputs":hashes}
        objects.append(obj)
    argv = ["c++", *objects, *libraries, "-Wl,--gc-sections", "-pthread", "-ldl", "-lz",
            "-o", scratch / "Replay"]
    run(argv, scratch=scratch)
    commands.append(list(map(str,argv)))
    dump(scratch/"commands.json", {
        "argv":commands,"compiler":run(["c++","--version"]).splitlines()[0],
        "depfile_closure":depfiles, "elapsed_seconds":time.monotonic()-start,
        "bindings_sha256":sha(args.bindings), "archives":{str(p):sha(p) for p in libraries},
    })


def symbols(obj):
    names = {l.split()[-1] for l in run(["nm","--defined-only",obj]).splitlines()
             if len(l.split()) == 3}
    assert SYMBOL in names
    return SYMBOL


def verify_output(exe, fixture):
    cases = fixture["cases"]
    inputs = "\n".join(" ".join(str(int(x)) if isinstance(x,bool) else str(x) for x in row["case"])
                       for row in cases)+"\n"
    lines = run([exe.resolve()],stdin=inputs).splitlines()
    cursor = iter(lines)
    for row in cases:
        assert next(cursor) == "case " + row["case"][0]
        observed = []
        for line in cursor:
            if line == "focus-provider":
                break
            observed.append(line)
        focus = []
        for line in cursor:
            if line == "end":
                break
            focus.append(line)
        assert focus == ["fill 0 0 2 14 4278256131"]
        expected = []
        for item in row["output"]:
            if item == ["focus"]:
                expected.extend(focus)
            else:
                expected.append(" ".join(map(str,item)))
        assert observed == expected, (row["case"],observed,expected)
    assert next(cursor,None) is None
    return lines


def replay(args):
    source_transition = load_transition(args.source_transition, args.source_transition_sha256)
    started = datetime.datetime.now(datetime.timezone.utc)
    run(FORMAT)
    fixture = read(args.fixtures)
    assert capture(args.elf,args.reference) == fixture
    assert symbols(args.object) == symbols(args.exe) == fixture["mangled"]
    result = verify_output(args.exe,fixture)
    bindings = read(args.bindings)
    commands = args.object.parent/"commands.json"
    compile_receipt = read(commands) if commands.is_file() else None
    if compile_receipt:
        assert compile_receipt["bindings_sha256"] == sha(args.bindings)
    else:
        for name,row in bindings["files"].items():
            expected = current_source_digest(name, row["sha256"], source_transition)
            assert sha(Path(name)) == expected, name
    sources = {str(p.relative_to("uc-library")):sha(p) for p in (SRC,HDR,TEST)}
    if not compile_receipt:
        sources.update({str(Path(p).relative_to("uc-library")):current_source_digest(p,v["sha256"], source_transition)
                        for p,v in bindings["files"].items() if "SLChannel" in p or "MixerState" in p
                        or "MixerClientComponentBase" in p})
    providers = {p:v["sha256"] for p,v in bindings["files"].items() if Path(p).is_relative_to(CORE)}
    assert all(sha(Path(p))==h for p,h in providers.items())
    row = {"original_elf_sha256":fixture["elf_sha256"],"mangled":SYMBOL,"sources":sources,
           "repository_sources":providers,"cpp_compiled":True,"mangling_namespace_checked":True,
           "portable_ready":False,"validation_domain":DOMAIN,"declaration_uncertainties":[LIMITS[-1]]}
    dump(args.out, {
        "archive_source_transition": {"path": str(args.source_transition),
            "sha256": args.source_transition_sha256} if args.source_transition else None,
        "success":True,"cpp_differential_passed":True,"compiled_mangled_names_matched":True,
        "portable_ready":False,"mangled_names":[SYMBOL],
        "original_elf_sha256":fixture["elf_sha256"],"domain":DOMAIN,"validation_domain":DOMAIN,
        "functions":[row],"proposed_readiness":{"ready":[],"pending":[row]},
        "limitations":LIMITS,"sources":sources,"repository_sources":providers,
        "format":{"format_check_passed":True,"version":run([FORMAT[0],"--version"]).strip(),
                  "files":{str(p):sha(p) for p in (SRC,HDR,TEST)}},
        "native":fixture,"native_case_count":len(fixture["cases"]),"host_case_count":len(fixture["cases"]),
        "host_trace":result,"core_commit":"e8cbdea4a4a20e15111f5a690798a259c0374b31",
        "local_compile":compile_receipt,"bindings_sha256":sha(args.bindings),"replay_argv":sys.argv,
        "fixture_sha256":sha(args.fixtures),"compiled_object_sha256":sha(args.object),
        "executable_sha256":sha(args.exe),"integration_sha256":sha(args.integration),
        "replay_producer_sha256":sha(Path(__file__)),
        "native_producer_sha256":sha(Path(__file__).with_name("native.py")),
        "provider_session_id":os.getenv("CODEX_THREAD_ID"),
        "replay_start_utc":started.isoformat(),
        "replay_end_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
    })
    print("8 exact ARM and 8 typed Linux cases, all 5 native indirect sites")


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--symbols",action="store_true")
    for option in ("build","provider","bindings","object","exe","elf","reference",
                   "fixtures","integration","out"):
        p.add_argument("--"+option,type=Path)
    p.add_argument("--source-transition", type=Path)
    p.add_argument("--source-transition-sha256")
    args=p.parse_args()
    if args.build:
        build(args)
    elif args.symbols:
        print(symbols(args.object))
    else:
        replay(args)


if __name__=="__main__":
    main()
