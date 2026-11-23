"""Check the compiled meter hook against fresh exact original ARM observations."""
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
DIR = Path(__file__).resolve().parent.relative_to(ROOT)
TASK = DIR.name
SCALE = TASK.endswith("s03")
TYPE = "MeterScaleControl" if SCALE else "MeterManagerBase"
SOURCE = Path(f"uc-library/src/Presonus/{TYPE}.cpp")
HEADER = Path(f"uc-library/include/presonus/{TYPE}.hpp")
DRIVER = DIR / "Replay.cpp"
FIXTURE = DIR / "fixtures.json"
SCRATCH = Path("temp/recovery-work") / TASK
PYTHON = "uc-library/.venv/bin/python"
FORMATTER = "uc-library/.venv/bin/clang-format"
FORMAT = [FORMATTER, "--style=file", "--fallback-style=LLVM", "--dry-run", "--Werror"]
ARCHIVE_DIR = Path("temp/provider-baseline08")
ARCHIVES = [ARCHIVE_DIR / name for name in ["libcorelib.a", "libpresonus_core_allocator.a"]]
PROVENANCE = ARCHIVE_DIR / "PROVENANCE.json"
FROZEN = Path("/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/"
              "control10x20-after-4fed70d11/packeting/"
              "actual03-separate-ui-audio-batch08/snapshot")
ELF = FROZEN / ("rootfs/CS18_v13840/home/root/surface" if SCALE
                else "rootfs/RML16AI_Rack_13731/home/root/mixer")
PRIOR_ADD_RANGE = "uc-library/validation/control10x20-next39-current02/pending.fragment.json"
PRIOR_ADD_RANGE_SHA = "4dd05964e3836426b71fd588d61adadc21f2ed57e1165c8924c01dff3a782608"
TIMINGS = []


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def binding(path):
    return {"path": str(path), "sha256": digest(path)}


def run(argv):
    argv = list(map(str, argv))
    started = time.monotonic()
    result = subprocess.run(argv, cwd=ROOT, text=True, capture_output=True,
                            env={**os.environ, "TMPDIR": str(ROOT / SCRATCH)})
    TIMINGS.append({"argv": argv, "seconds": time.monotonic() - started,
                    "exit_code": result.returncode})
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    result.check_returncode()
    return result.stdout


def verify_local_archive_inputs():
    receipt = json.loads(PROVENANCE.read_text())
    paths = {item["local"]: item["sha256"] for item in receipt["files"]}
    for archive in ARCHIVES:
        assert digest(archive) == paths[str(archive)]


def compile_local():
    verify_local_archive_inputs()
    flags = ["c++", "-std=c++17", "-fno-rtti", "-Wno-multichar", "-ffunction-sections",
             "-fdata-sections", "-Iuc-library/include", "-Ithird_party/ccl-framework"]
    run([*flags, "-MMD", "-MF", SCRATCH / "production.d", "-c", SOURCE,
         "-o", SCRATCH / "production.o"])
    run([*flags, "-MMD", "-MF", SCRATCH / "replay.d", "-c", DRIVER,
         "-o", SCRATCH / "replay.o"])
    run(["c++", SCRATCH / "replay.o", SCRATCH / "production.o", "-Wl,--gc-sections",
         *ARCHIVES, "-lz", "-lpthread", "-ldl", "-lm", "-o", SCRATCH / "replay"])


def compare_outputs(native, actual):
    if not SCALE:
        expected = [f"{c['route']} {c['seed']} {c['phase']} {int(c['unchanged'])}"
                    for c in native["cases"]]
    else:
        expected = [str(next(row["count"] for row in native["cases"][0]["observed"]
                             if row["kind"] == "pinned Core Vector resize"))]
        records = []
        for case in native["cases"]:
            records.extend(row for row in case["observed"] if row["kind"] == "Ranges addRange")
            expected.append(str(len(records)))
            for row in records:
                fields = [row["name"], row["count"], 1, *row["values"]]
                expected.append(" ".join(map(str, fields)))
    assert expected == actual, (expected, actual)


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
    SCRATCH.mkdir(parents=True, exist_ok=True)
    start = datetime.now(timezone.utc).isoformat()
    if args.mode == "compile":
        compile_local()
        return
    run([*FORMAT, HEADER, SOURCE, DRIVER])
    if args.mode == "format":
        return
    production = args.object or SCRATCH / "production.o"
    exe = args.exe or SCRATCH / "replay"
    fixture = json.loads(FIXTURE.read_text())
    mangled = fixture["mangled"]
    names = {line.split()[-1] for line in run(["nm", "--defined-only", production]).splitlines()
             if len(line.split()) >= 3}
    assert mangled in names
    if SCALE:
        assert "_ZN8Presonus17MeterScaleControl6Ranges8addRangeEPKciPKi" in names
        dependencies = run(["nm", "-u", production])
        for name in ("__cxa_guard_acquire", "__cxa_guard_release", "__cxa_atexit"):
            assert name in dependencies
    if args.mode == "symbols":
        return
    original = json.loads(run([PYTHON, "-B", DIR / "native.py", ELF]))
    assert original == fixture
    executable_rows = run([exe.resolve()]).splitlines()
    compare_outputs(original, executable_rows)
    if SCALE:
        domain = ("Two original CS18 executions on a cold then warm native static guard. "
                  "Linux typed CCL registry starts empty, preserves registry identity, appends "
                  "three ordered ranges per call and retains the first result for each name. "
                  "All 29 values per call and stable borrowed arrays are checked.")
        limits = ["Provisional void return, C++ source port only; ARM ABI and target layouts unresolved.",
                  "Native CCL vector, addRange and runtime guard/lifetime boundaries are modeled. "
                  "The unchanged typed addRange, pinned CCL vector and host C++ static lifecycle execute on Linux.",
                  "Concurrent calls, allocation failure, exceptional and device paths are outside the replay."]
        ccl = ["public/corevector.h", "public/corestringbuffer.h",
               "portable/gui/corecontrols.h", "portable/gui/corecontrols.cpp"]
    else:
        domain = ("RM/RML exact default hook with both boolean values, two seeded receiver states, "
                  "and direct and verified actual primary vtable dispatch. The native receiver and "
                  "portable observed fields remain unchanged. Portable application boundary calls abort.")
        limits = ["Provisional void return: native r0 retains the receiver with no evidence of a consumed result. "
                  "Original class layout, inheritance and ARM ABI remain unresolved.",
                  "Native receiver is bounded synthetic storage with the original vptr; portable receiver uses "
                  "real pinned CCL Thread and Lock. No worker thread, network or hardware execution."]
        ccl = ["public/corevector.h", "system/corethread.h",
               "platform/linux/corethread.linux.cpp", "platform/shared/posix/corethread.posix.cpp"]
    sources = {str(p.relative_to("uc-library")): digest(p) for p in (HEADER, SOURCE)}
    providers = {f"third_party/ccl-framework/core/{p}":
                 digest(f"third_party/ccl-framework/core/{p}") for p in ccl}
    row = dict(original_elf_sha256=original["elf"]["sha256"], mangled=mangled,
               sources=sources, repository_sources=providers, domain=domain,
               cpp_compiled=True, mangling_namespace_checked=True, portable_ready=False,
               declaration_uncertainties=limits)
    proof = dict(task_id=TASK, start_utc=start, native=original, portable_rows=executable_rows,
                 case_count=len(original["cases"]), cpp_differential_passed=True,
                 compiled_mangled_names_matched=True, mangled_names=[mangled],
                 proposed_readiness={"ready": [], "pending": [row]},
                 sources=sources, repository_sources=providers,
                 fixture=binding(FIXTURE), native_producer=binding(DIR / "native.py"),
                 checker=binding(DIR / "check.py"), production=binding(production),
                 executable=binding(exe), validation_domain=domain, limitations=limits,
                 format_check_passed=True, formatter=run([FORMATTER, "--version"]).strip(),
                 compiler=run(["c++", "--version"]).splitlines()[0],
                 native_versions=run([PYTHON, "-B", "-c",
                                      "import elftools,unicorn; print(elftools.__version__,unicorn.__version__)"]).strip())
    if SCALE:
        prior = Path(PRIOR_ADD_RANGE) if args.integration else SCRATCH / "add-range-prior-pending.fragment.json"
        assert digest(prior) == PRIOR_ADD_RANGE_SHA
        proof["prior_add_range_admission"] = binding(prior)
    if args.integration:
        proof["integration"] = binding(args.integration)
    else:
        verify_local_archive_inputs()
        proof["local_provider_archives"] = [binding(path) for path in ARCHIVES]
        for name in ("production.d", "replay.d"):
            paths = (SCRATCH / name).read_text().replace("\\\n", " ").split()[1:]
            proof.setdefault("compiled_file_hashes", {}).update(
                {path: digest(path) for path in paths})
    proof["tool_timings"] = TIMINGS
    proof["end_utc"] = datetime.now(timezone.utc).isoformat()
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(proof, indent=2) + "\n")
    print(f"{TASK}: matched {proof['case_count']} exact original cases. {domain}")


if __name__ == "__main__":
    main()
