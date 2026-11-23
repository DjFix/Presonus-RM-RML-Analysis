"""Verify one meter indicator port against fresh original execution."""
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
WORKER = Path("/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling200-02/agent-repos04/ucnet148")
TEST = Path(__file__).resolve().parent.relative_to(ROOT)
TASK = TEST.name
MODE = int(TASK[-2:])
SCRATCH = Path("temp/recovery-work") / TASK
PROJECT = Path("/home/rs/projects/opencs/ai-line-analysis")
CONTROL = Path("temp/recovery-work/control10x20-after-4fed70d11")
CAPTURE = CONTROL / "packeting/actual08-authorized-wave01-capture01"
PACKET = CAPTURE / "packets" / TASK
FROZEN = PROJECT / CAPTURE / "snapshot"
SNAPSHOT = FROZEN.parent / "SNAPSHOT.json"
SNAPSHOT_SHA = "08ad9917876facf4ab21684237c037287d99103df61f4d5e3560612bf61e241b"
REVIEW, REVIEW_SHA = {
    16: ("meter-maid/setSignal", "a4be95b70b69acf098a82df83ce7eee737c34847320abd0a420dfe41e387c4ae"),
    17: ("meter-maid/setClipped", "b27458d0b2e2c930cda9c6abdbbe43b9acf29d5f496ceb1ad186e241c5a31efa"),
    18: ("meter-final-local/isClipped", "7282f28c88edd41082b14e0ce63d5c3698ea47ecb3f042bae38202310d09aca5"),
}[MODE]
REVIEW = FROZEN / CONTROL / "selection" / f"{REVIEW}.native01.json"
PYTHON = "uc-library/.venv/bin/python"
FORMATTER = "uc-library/.venv/bin/clang-format"
CCL = "third_party/ccl-framework"
REPLAY = TEST / "Replay.cpp"
HEADER = Path("uc-library/include/presonus/MeterMaid.hpp")
SOURCE = Path("uc-library/src/Presonus/MeterMaid.cpp")
BASE_HEADER = Path("uc-library/include/presonus/MeterBallistics.hpp")
BASE = Path("uc-library/src/Presonus/MeterBallistics.cpp")
OWNED = (HEADER, SOURCE, REPLAY)
FLAGS = ["-std=c++20", "-fno-rtti", "-fno-fast-math", "-ffp-contract=off",
         "-fno-sized-deallocation", "-ffunction-sections", "-fdata-sections",
         "-Wno-multichar", "-Iuc-library/include", f"-I{CCL}"]
ARCHIVES = {
    Path("temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libcorelib.a"):
        "3c4f0825acb529fda135587b7ff5cb92ca0100bb417a20c034d3fdef80a93e0c",
    Path("temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libpresonus_core_allocator.a"):
        "69892fbcec9a50a140462982073c686a67ca4763dfb5dfa190534d022b78a40d",
}
ELFS = [FROZEN / p for p in ("rootfs/RML16AI_Rack_13731/home/root/mixer",
                            "rootfs/CS18_v13840/home/root/surface")]
NATIVE = [PYTHON, "-B", TEST / "native.py", PACKET / "request.json", REVIEW, *ELFS]
DOMAIN = {
    16: "Both original signal setter extents, true and false, with bound and unbound signal slot. "
        "Original ARM unsigned conversion and actual NumericParam slot/false-edit boundary execute. "
        "The Linux replay checks the actual typed CCL value, call arguments and untouched peers.",
    17: "Both original clip setter extents, true and false, with bound and unbound clip slot. "
        "Original ARM unsigned conversion and actual NumericParam slot/false-edit boundary execute. "
        "The Linux replay checks the actual typed CCL value, call arguments and untouched peers.",
    18: "Both original clip query extents with bound and unbound slot, signed zero, positive fraction, "
        "one and negative finite value. Actual ARM compare helpers establish a positive threshold; "
        "Linux calls the genuine typed CCL getter once only for a bound clip slot and preserves peer state.",
}[MODE]
LIMITS = [
    "Portable source port using borrowed CCL pointers. Original ownership, member declarations and ARM ABI remain unresolved.",
    "Original ordinary C++ return declaration remains unresolved.",
    "The exact original NumericParam virtual destination is observed at a controlled boundary; genuine pinned CCL source executes independently on Linux. No device behavior is exercised.",
]
TIMES = []


def utc():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def binding(path):
    return dict(path=str(path), sha256=digest(path))


def run(argv, payload=None):
    argv = list(map(str, argv))
    start, then = utc(), time.monotonic()
    proc = subprocess.run(argv, cwd=ROOT, text=True, capture_output=True, input=payload,
                          env={**os.environ, "TMPDIR": str(ROOT / SCRATCH)})
    TIMES.append(dict(argv=argv, start_utc=start, seconds=time.monotonic()-then,
                      exit_code=proc.returncode))
    if proc.stderr:
        print(proc.stderr, end="", file=sys.stderr)
    proc.check_returncode()
    return proc.stdout


def deps(local):
    assert digest(SNAPSHOT) == SNAPSHOT_SHA
    hashes = json.loads(SNAPSHOT.read_text())["files"]
    paths, receipts, operands = set(), [], {}
    for ix, path in enumerate((SOURCE, BASE, REPLAY)):
        if local:
            depfile = SCRATCH / f"compile-{ix}.d"
            raw = depfile.read_text()
            receipts.append(binding(depfile))
        else:
            raw = run(["c++", *FLAGS, "-MM", path])
        paths.update(raw.replace("\\\n", " ").split()[1:])
    for operand in paths:
        path = Path(operand)
        name = str(path.relative_to(FROZEN)) if path.is_relative_to(FROZEN) else operand
        operands[name] = dict(read_path=str(path), sha256=digest(path))
    for item in sorted(set(operands) - set(map(str, OWNED))):
        assert operands[item]["sha256"] == hashes[item] == digest(FROZEN / item), item
    core = {name: hashes[name] for name in sorted(operands) if name.startswith(CCL + "/core/")}
    provider_source = f"{CCL}/core/portable/coreparams.cpp"
    assert digest(provider_source) == hashes[provider_source] == digest(FROZEN / provider_source)
    core[provider_source] = hashes[provider_source]
    return core, dict(linked_provider_source=binding(FROZEN / provider_source), snapshot=binding(SNAPSHOT), depfiles=receipts,
                      compiler_inputs=operands,
                      pinned_ccl_commit="e8cbdea4a4a20e15111f5a690798a259c0374b31",
                      frozen_inputs={name: str(FROZEN / name) for name in sorted(set(operands) - set(map(str, OWNED)))})


def compile_local():
    assert ROOT == WORKER
    for path, expected in ARCHIVES.items():
        assert path.resolve().is_relative_to(WORKER) and digest(path) == expected
    objects = []
    assert digest(SNAPSHOT) == SNAPSHOT_SHA
    hashes = json.loads(SNAPSHOT.read_text())["files"]
    assert digest(FROZEN / BASE) == hashes[str(BASE)]
    assert digest(BASE_HEADER) == hashes[str(BASE_HEADER)] == digest(FROZEN / BASE_HEADER)
    for ix, source in enumerate((SOURCE, FROZEN / BASE, REPLAY)):
        obj = SCRATCH / ("production.o" if ix == 0 else f"compile-{ix}.o")
        objects.append(obj)
        run(["c++", *FLAGS, "-MMD", "-MF", SCRATCH / f"compile-{ix}.d",
             "-c", source, "-o", obj])
    run(["c++", *objects, *ARCHIVES, "-Wl,--gc-sections", "-lz", "-lpthread", "-ldl",
         "-lm", f"-Wl,-Map,{SCRATCH/'replay.map'}", "-o", SCRATCH/"replay"])
    deps(True)


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
    assert Path(run(["git", "rev-parse", "--show-toplevel"]).strip()) == ROOT
    SCRATCH.mkdir(parents=True, exist_ok=True)
    run([FORMATTER, "--style=file", "--fallback-style=LLVM", "--dry-run", "--Werror", *OWNED])
    if args.mode == "format":
        return
    if args.mode == "compile":
        compile_local()
        return
    obj = args.object or SCRATCH / "production.o"
    exe = args.exe or SCRATCH / "replay"
    fixture = TEST / "fixtures.json"
    sealed = json.loads(fixture.read_text())
    names = {item["target"]["mangled"] for item in sealed["originals"]}
    assert names <= {line.split()[-1] for line in run(["nm", "--defined-only", obj]).splitlines()
                     if len(line.split()) >= 3}
    if args.mode == "symbols":
        return
    assert digest(REVIEW) == REVIEW_SHA
    native = json.loads(run(NATIVE))
    assert native == sealed
    cases = [case for item in native["originals"] for case in item["cases"]]
    payload = "".join(f"{int(c['bound'])} {c['input_bits']}\n" for c in cases)
    results = run([exe.resolve()], payload).splitlines()
    assert results == [str(c["result"]) for c in cases]
    providers, receipt = deps(not bool(args.integration))
    sources = {str(path.relative_to("uc-library")): digest(path)
               for path in (HEADER, SOURCE, BASE_HEADER)}
    rows = [
        dict(original_elf_sha256=item["elf"]["sha256"], mangled=item["target"]["mangled"],
             sources=sources, repository_sources=providers, domain=DOMAIN, cpp_compiled=True,
             mangling_namespace_checked=True, portable_ready=False, declaration_uncertainties=LIMITS)
        for item in native["originals"]
    ]
    proof = dict(task_id=TASK, start_utc=start, native=native, portable_rows=results,
                 case_count=len(results), previous_native_review=binding(REVIEW),
                 cpp_differential_passed=True, compiled_mangled_names_matched=True,
                 mangled_names=sorted(names), functions=rows,
                 proposed_readiness={"ready": [], "pending": rows}, sources=sources,
                 repository_sources=providers, dependency_receipt=receipt, validation_domain=DOMAIN,
                 limitations=LIMITS, fixture=binding(fixture), native_producer=binding(TEST/"native.py"),
                 checker=binding(TEST/"check.py"), production=binding(obj), executable=binding(exe),
                 format_check_passed=True, formatter=run([FORMATTER, "--version"]).strip(),
                 compiler=run(["c++", "--version"]).splitlines()[0],
                 native_versions=run([PYTHON,"-B","-c",
                    "import elftools,unicorn; print(elftools.__version__,unicorn.__version__)"]).strip(),
                 session_id=os.environ.get("CODEX_THREAD_ID"), physical_root=str(ROOT))
    if args.integration:
        proof["integration"] = binding(args.integration)
    else:
        proof["local_archives"] = [binding(path) for path in ARCHIVES]
        proof["linker_map"] = binding(SCRATCH/"replay.map")
    proof["tool_timings"] = TIMES
    proof["end_utc"] = utc()
    if args.out:
        args.out.write_text(json.dumps(proof, indent=2) + "\n")
    print(f"{TASK}: matched {len(results)} exact cases. {DOMAIN}")


if __name__ == "__main__":
    main()
