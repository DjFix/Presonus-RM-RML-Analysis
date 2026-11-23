"""Replay the exact native meter attribute fixture against Linux."""
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
TASK = "cycle20_g02_s04"
DIR = Path("uc-library/tests/recovery") / TASK
SOURCE = Path("uc-library/src/Presonus/MeterScaleControl.cpp")
HEADER = Path("uc-library/include/presonus/MeterScaleControl.hpp")
SCRATCH = Path("temp/recovery-work") / TASK
PYTHON = "uc-library/.venv/bin/python"
FORMATTER = "uc-library/.venv/bin/clang-format"
ARCHIVE_DIR = Path("temp/core-upstream/root-integration-01/upstream-core/sdk/lib")
ARCHIVES = {
    ARCHIVE_DIR / "libcorelib.a":
        "3c4f0825acb529fda135587b7ff5cb92ca0100bb417a20c034d3fdef80a93e0c",
    ARCHIVE_DIR / "libpresonus_core_allocator.a":
        "69892fbcec9a50a140462982073c686a67ca4763dfb5dfa190534d022b78a40d",
}
PROJECT = Path("/home/rs/projects/opencs/ai-line-analysis")
CONTROL = Path("temp/recovery-work/control10x20-after-4fed70d11")
FROZEN = PROJECT / CONTROL / "packeting/actual04-next-batch01/snapshot"
ELF = FROZEN / "rootfs/CS18_v13840/home/root/surface"
REVIEW = FROZEN / CONTROL / "selection/meter-scale-attributes/NATIVE_OBSERVATIONS01.json"
REVIEW_SHA = "6ed2c4a1385ecb3ee6d191f0b197316e306490061a52bb9f65cf287e15012849"
PRIOR = {
    "control10x20-actual03-next20-existing":
        "1c8afa74e1a7ec59ef9e693cf95e8983a08f6eb6a32312ed2d50ddc990c81341",
    "control10x20-actual03-next20":
        "6fa1d4221c43d5c5964405d8c890688132277c85c53dd7e69f4b1f748dcb59c0",
}
DOMAIN = ("Twelve CS18 cases cover cold and initialized registry, absent, empty, non-string, "
          "known and unsupported names, and independent replacement of the two results. "
          "The exact ARM application lookup and signed endpoint conversions run. Linux matches "
          "qualified pinned View call order and dimensions, real linear and linrev providers, "
          "native endpoint values and midpoint, and display tick order. Explicit portable ticks "
          "remain an override.")
LIMITS = [
    "Portable C++ uses the pinned View's void override. Original return declaration, class layout "
    "and ARM ABI remain unresolved.",
    "Native Core View, Attributes, vector, factory and setRange are identified controlled boundaries "
    "along with C++ guard/lifetime registration and strcmp. The signed integer conversion runtime "
    "and original application initializer, target and lookup instructions run. Initializer addRange "
    "uses a modeled boundary fed by native arguments. Genuine CCL and the retained application "
    "registry and lookup execute separately on Linux.",
    "The portable control owns its interpolator. Original ownership, geometry, unknown curves, "
    "concurrency, exceptions and hardware remain outside the tested domain.",
]
TIMINGS = []


def utc():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def binding(path):
    return dict(path=str(path), sha256=digest(path))


def run(argv, payload=None):
    argv = list(map(str, argv))
    started = utc()
    before = time.monotonic()
    result = subprocess.run(argv, cwd=ROOT, text=True, capture_output=True, input=payload,
                            env={**os.environ, "TMPDIR": str(ROOT / SCRATCH)})
    TIMINGS.append(dict(argv=argv, start_utc=started, seconds=time.monotonic() - before,
                        exit_code=result.returncode))
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    result.check_returncode()
    return result.stdout


def verify_archives():
    for archive, expected in ARCHIVES.items():
        assert digest(archive) == expected


def compile_local():
    verify_archives()
    flags = ["c++", "-std=c++17", "-fno-rtti", "-Wno-multichar", "-ffunction-sections",
             "-fdata-sections", "-Iuc-library/include", "-Ithird_party/ccl-framework"]
    run([*flags, "-MMD", "-MF", SCRATCH / "production.d", "-c", SOURCE,
         "-o", SCRATCH / "production.o"])
    run([*flags, "-MMD", "-MF", SCRATCH / "replay.d", "-c", DIR / "Replay.cpp",
         "-o", SCRATCH / "replay.o"])
    run(["c++", SCRATCH / "replay.o", SCRATCH / "production.o", "-Wl,--gc-sections",
         *ARCHIVES, "-lz", "-lpthread", "-ldl", "-lm", "-o", SCRATCH / "replay"])


def attribute_input(value):
    if value is None:
        return "n"
    if isinstance(value, int):
        return f"i {value}"
    return "s " + json.dumps(value)


def expected_output(case):
    row = [case["stored_range"] or "-",
           case["interpolator"] if case["stored_scale"] else "-"]
    if case["stored_scale"]:
        row.extend(f"{value:g}" for value in (case["configured"] or (0, 1, 1)))
    row.append("|")
    row.extend(map(str, case["ticks"]))
    return " ".join(row)


def audit_prior(native):
    assert digest(REVIEW) == REVIEW_SHA
    reviewed = json.loads(REVIEW.read_text())
    cases = {(c["warm"], c["range"], c["interpolator"]): c for c in native["cases"]}
    for previous in reviewed["cases"]:
        current = cases[previous["warm"], previous["range"], previous["interpolator"]]
        assert bool(current["stored_range"]) == previous["stored_range"]
        assert current["stored_scale"] == previous["stored_scale"]
        endpoints = next((r["values"] for r in previous["trace"]
                          if r["operation"] == "pinned Interpolator range"), None)
        assert current["configured"] == endpoints
    admitted = []
    for folder, expected in PRIOR.items():
        path = PROJECT / "uc-library/validation" / folder / "pending.fragment.json"
        item = binding(path)
        assert item["sha256"] == expected
        admitted.append(item)
    return len(reviewed["cases"]), admitted


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
    start = utc()
    if args.mode == "compile":
        compile_local()
        return
    run([FORMATTER, "--style=file", "--fallback-style=LLVM", "--dry-run", "--Werror",
         HEADER, SOURCE, DIR / "Replay.cpp"])
    if args.mode == "format":
        return
    production = args.object or SCRATCH / "production.o"
    exe = args.exe or SCRATCH / "replay"
    fixture = DIR / "fixtures.json"
    expected_fixture = json.loads(fixture.read_text())
    mangled = expected_fixture["mangled"]
    names = {line.split()[-1] for line in run(["nm", "--defined-only", production]).splitlines()
             if len(line.split()) >= 3}
    assert {mangled, "_Z23__initMeterScaleControlv",
            "_ZN8Presonus17MeterScaleControl6Ranges8getRangeEPKc"} <= names
    if args.mode == "symbols":
        return
    producer = DIR / "native.py"
    original = json.loads(run([PYTHON, "-B", producer, ELF]))
    assert original == expected_fixture
    previously_reviewed, admitted = audit_prior(original)
    cases = original["cases"]
    payload = "".join(
        f"{int(c['warm'])} {attribute_input(c['range'])} {attribute_input(c['interpolator'])}\n"
        for c in cases)
    actual = run([exe.resolve()], payload).splitlines()
    assert [expected_output(case) for case in cases] == actual

    ccl = ["portable/coreattributes.h", "portable/coreattributes.cpp", "portable/gui/coreview.h",
           "portable/gui/coreview.cpp", "portable/gui/coregraphics.h", "public/corevector.h",
           "public/coreinterpolator.h", "public/coreinterpolator.cpp"]
    providers = {f"third_party/ccl-framework/core/{p}":
                 digest(f"third_party/ccl-framework/core/{p}") for p in ccl}
    sources = {str(p.relative_to("uc-library")): digest(p) for p in (HEADER, SOURCE)}
    row = dict(original_elf_sha256=original["elf"]["sha256"], mangled=mangled,
               sources=sources, repository_sources=providers, domain=DOMAIN, cpp_compiled=True,
               mangling_namespace_checked=True, portable_ready=False, declaration_uncertainties=LIMITS)
    proof = dict(task_id=TASK, session_id=os.environ.get("CODEX_THREAD_ID"),
                 desktop_session_id=os.environ.get("CODEX_SESSION_ID"), start_utc=start,
                 native=original, portable_rows=actual, case_count=len(cases),
                 previously_reviewed_case_count=previously_reviewed,
                 previous_native_observations=binding(REVIEW), prior_provider_admission=admitted,
                 cpp_differential_passed=True, compiled_mangled_names_matched=True,
                 mangled_names=[mangled], proposed_readiness={"ready": [], "pending": [row]},
                 sources=sources, repository_sources=providers, fixture=binding(fixture),
                 native_producer=binding(producer), checker=binding(DIR / "check.py"),
                 production=binding(production), executable=binding(exe), validation_domain=DOMAIN,
                 limitations=LIMITS, format_check_passed=True,
                 formatter=run([FORMATTER, "--version"]).strip(),
                 compiler=run(["c++", "--version"]).splitlines()[0],
                 native_versions=run([PYTHON, "-B", "-c",
                                      "import elftools,unicorn; print(elftools.__version__,unicorn.__version__)"]).strip())
    if args.integration:
        proof["integration"] = binding(args.integration)
    else:
        verify_archives()
        proof["local_provider_archives"] = [binding(path) for path in ARCHIVES]
        for name in ("production.d", "replay.d"):
            paths = (SCRATCH / name).read_text().replace("\\\n", " ").split()[1:]
            proof.setdefault("compiled_file_hashes", {}).update({path: digest(path) for path in paths})
    proof["tool_timings"] = TIMINGS
    proof["end_utc"] = utc()
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(proof, indent=2) + "\n")
    print(f"{TASK}: matched {len(cases)} freshly executed original cases. {DOMAIN}")


if __name__ == "__main__":
    main()
