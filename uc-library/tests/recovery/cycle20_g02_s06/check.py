"""Check Controller::doUpdates against fresh offline RM observations."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
TASK = "cycle20_g02_s06"
TEST = Path("uc-library/tests/recovery") / TASK
SOURCE = Path("uc-library/src/Presonus/Dsp/ControllerInterface.cpp")
HEADER = Path("uc-library/include/presonus/dsp/Controller.hpp")
REPLAY = TEST / "Replay.cpp"
SCRATCH = Path("temp/recovery-work") / TASK
PYTHON = "uc-library/.venv/bin/python"
FORMAT = "uc-library/.venv/bin/clang-format"
PROJECT = Path("/home/rs/projects/opencs/ai-line-analysis")
CONTROL = Path("temp/recovery-work/control10x20-after-4fed70d11")
FROZEN = PROJECT / CONTROL / "packeting/actual05-next-batch02/snapshot"
SNAPSHOT = FROZEN.parent / "SNAPSHOT.json"
SNAPSHOT_SHA = "0eedcf5ac90a258e4c1613a43d1e5cfdf515601bab7634174a0be7dbc9da123c"
ELF = FROZEN / "rootfs/RML16AI_Rack_13731/home/root/mixer"
REVIEW = FROZEN / CONTROL / "selection/meter-dsp-leaves/NATIVE_CONTROLLER01.json"
REVIEW_SHA = "efddcae494288ab842138b92225e8b00952e133b4cd97e8754ac4755a6280cb9"
ARCHIVE_DIR = Path("temp/provider-baseline08")
ARCHIVES = [ARCHIVE_DIR / ("lib" + x + ".a") for x in
            ("presonus_rm_components", "presonus_uc", "corelib", "presonus_core_allocator")]
PROVENANCE = ARCHIVE_DIR / "PROVENANCE.json"
CORE_PIN = "e8cbdea4a4a20e15111f5a690798a259c0374b31"
DOMAIN = ("Six exact RM/RML ARM executions with three synthetic receiver byte seeds, using "
          "the original direct entry and the actual primary Controller vtable slot. ARM "
          "access traces show only stack operations and the two expected virtual "
          "dispatch reads. Six valid Linux typed controller cases preserve observed "
          "scalar and borrowed provider state. Unexpected portable callbacks abort.")
LIMITS = [
    "The void return is a portable convention. The original retained r0 is the receiver "
    "and does not establish the C++ return declaration.",
    "The original primary vtable was checked separately. Source-port layout, full vtable "
    "shape, original constructor/ownership declarations and ARM interoperability are unresolved.",
    "This verifies the base default. Derived DSP updates, flushing, and hardware are outside scope.",
]
TIMES = []


def utc():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def bind(path):
    return {"path": str(path), "sha256": digest(path)}


def run(argv, payload=None):
    argv = list(map(str, argv))
    start = utc()
    before = time.monotonic()
    result = subprocess.run(argv, cwd=ROOT, text=True, capture_output=True, input=payload,
                            env={**os.environ, "TMPDIR": str(ROOT / SCRATCH)})
    TIMES.append(dict(argv=argv, start_utc=start, seconds=time.monotonic() - before,
                      exit_code=result.returncode))
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    result.check_returncode()
    return result.stdout


def verify_archives():
    bound = {item["local"]: item["sha256"] for item in json.loads(PROVENANCE.read_text())["files"]}
    return [item for path in ARCHIVES if (item := bind(path))["sha256"] == bound[str(path)]]


def compile_local():
    assert len(verify_archives()) == len(ARCHIVES)
    flags = ["c++", "-std=c++20", "-fno-rtti", "-Wno-multichar", "-ffunction-sections",
             "-fdata-sections", "-Iuc-library/include", "-Ithird_party/ccl-framework"]
    for stem, source in (("production", SOURCE), ("replay", REPLAY)):
        run([*flags, "-MMD", "-MF", SCRATCH / f"{stem}.d", "-c", source,
             "-o", SCRATCH / f"{stem}.o"])
    run(["c++", SCRATCH / "replay.o", SCRATCH / "production.o", "-Wl,--gc-sections",
         f"-Wl,-Map,{SCRATCH / 'replay.map'}", "-Wl,--start-group", *ARCHIVES,
         "-Wl,--end-group", "-lz", "-lpthread", "-ldl", "-lm", "-o", SCRATCH / "replay"])
    bind_dependents()


def bind_dependents():
    assert digest(SNAPSHOT) == SNAPSHOT_SHA
    hashes = json.loads(SNAPSHOT.read_text())["files"]
    operands = {}
    depfiles = []
    for stem in ("production", "replay"):
        depfile = SCRATCH / f"{stem}.d"
        depfiles.append(bind(depfile))
        for name in depfile.read_text().replace("\\\n", " ").split()[1:]:
            path = Path(name)
            item = bind(path)
            if path not in (SOURCE, HEADER, REPLAY):
                frozen = FROZEN / path
                assert item["sha256"] == hashes[name] == digest(frozen), name
                item["frozen_read_path"] = str(frozen)
            operands[name] = item
    assert len([row for row in operands.values() if "frozen_read_path" in row]) == 13
    return dict(snapshot=bind(SNAPSHOT), core_pin=CORE_PIN, depfiles=depfiles, operands=operands)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", nargs="?", default="replay",
                        choices=("format", "compile", "symbols", "replay"))
    parser.add_argument("--exe", type=Path)
    parser.add_argument("--object", type=Path)
    parser.add_argument("--integration", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    os.chdir(ROOT)
    start = utc()
    SCRATCH.mkdir(parents=True, exist_ok=True)
    run([FORMAT, "--style=file", "--fallback-style=LLVM", "--dry-run", "--Werror",
         HEADER, SOURCE, REPLAY])
    if args.mode == "format":
        return
    if args.mode == "compile":
        compile_local()
        return
    production = args.object or SCRATCH / "production.o"
    exe = args.exe or SCRATCH / "replay"
    fixture = TEST / "fixtures.json"
    expected = json.loads(fixture.read_text())
    mangled = expected["mangled"]
    names = {line.split()[-1] for line in run(["nm", "--defined-only", production]).splitlines()
             if len(line.split()) >= 3}
    assert mangled in names
    if args.mode == "symbols":
        return
    native = TEST / "native.py"
    actual = json.loads(run([PYTHON, "-B", native, ELF]))
    assert actual == expected
    assert digest(REVIEW) == REVIEW_SHA
    reviewed, = json.loads(REVIEW.read_text())["rows"]
    for row, old in zip(actual["cases"], reviewed["cases"], strict=True):
        assert all(value == old[key] for key, value in row.items())
    payload = "".join(f"{c['dispatch']} {c['seed']}\n" for c in actual["cases"])
    portable = run([exe.resolve()], payload).splitlines()
    assert portable == [f"{c['dispatch']} {c['seed']} {int(c['whole_state_unchanged'])}"
                        for c in actual["cases"]]

    snapshot_receipt = bind_dependents() if not args.integration else None
    assert digest(SNAPSHOT) == SNAPSHOT_SHA
    frozen_hashes = json.loads(SNAPSHOT.read_text())["files"]
    provider_names = ["coreclibrary", "corecontainer", "coreformatter", "coreinterpolator",
                      "coremalloc", "coreplatform", "coreproperty", "corestringbuffer",
                      "corestringtraits", "coretypes", "corevector"]
    providers = {f"third_party/ccl-framework/core/public/{name}.h":
                 frozen_hashes[f"third_party/ccl-framework/core/public/{name}.h"]
                 for name in provider_names}
    app_dependencies = ["uc-library/include/presonus/dsp/IController.hpp",
                        "uc-library/include/presonus/mixer_dsp/ParamDescriptorList.hpp"]
    assert all(digest(name) == expected == digest(FROZEN / name)
               for name, expected in providers.items())
    assert all(digest(name) == frozen_hashes[name] == digest(FROZEN / name)
               for name in app_dependencies)
    sources = {str(path.relative_to("uc-library")): digest(path)
               for path in (HEADER, SOURCE, *map(Path, app_dependencies))}
    row = dict(original_elf_sha256=actual["elf"]["sha256"], mangled=mangled,
               sources=sources, repository_sources=providers, domain=DOMAIN, cpp_compiled=True,
               mangling_namespace_checked=True, portable_ready=False, declaration_uncertainties=LIMITS)
    proof = dict(task_id=TASK, session_id=os.environ.get("CODEX_THREAD_ID"),
                 desktop_session_id=os.environ.get("CODEX_SESSION_ID"), start_utc=start,
                 native=actual, portable_rows=portable, case_count=len(portable),
                 previous_native_review=bind(REVIEW), dependency_receipt=snapshot_receipt,
                 cpp_differential_passed=True, compiled_mangled_names_matched=True,
                 mangled_names=[mangled], proposed_readiness={"ready": [], "pending": [row]},
                 sources=sources, repository_sources=providers,
                 fixture=bind(fixture), native_producer=bind(native), checker=bind(TEST / "check.py"),
                 production=bind(production), executable=bind(exe), validation_domain=DOMAIN,
                 limitations=LIMITS, format_check_passed=True, formatter=run([FORMAT, "--version"]).strip(),
                 compiler=run(["c++", "--version"]).splitlines()[0],
                 native_versions=run([PYTHON, "-B", "-c",
                                      "import elftools,unicorn; print(elftools.__version__,unicorn.__version__)"]).strip())
    if args.integration:
        proof["integration"] = bind(args.integration)
    else:
        proof["archive_receipt"] = dict(provenance=bind(PROVENANCE), archives=verify_archives(),
                                        linker_map=bind(SCRATCH / "replay.map"))
    proof["tool_timings"] = TIMES
    proof["end_utc"] = utc()
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(proof, indent=2) + "\n")
    print(f"{TASK}: matched {len(portable)} fresh original cases. {DOMAIN}")


if __name__ == "__main__":
    main()
