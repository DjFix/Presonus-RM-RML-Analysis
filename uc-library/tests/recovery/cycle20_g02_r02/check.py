"""Compare the compiled offline meter/OMAP scope to fresh exact ARM executions."""
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
TEST = Path(__file__).resolve().parent.relative_to(ROOT)
TASK = TEST.name
METER = TASK.endswith("s07")
CLASS = "MeterBallistics" if METER else "OMAPTargetHandler"
HEADER = Path(f"uc-library/include/presonus/{'' if METER else 'dsp/'}{CLASS}.hpp")
SOURCE = Path(f"uc-library/src/Presonus/{'' if METER else 'Dsp/'}{CLASS}.cpp")
REPLAY = TEST / "Replay.cpp"
SCRATCH = Path("temp/recovery-work") / TASK
PYTHON = "uc-library/.venv/bin/python"
FORMAT = "uc-library/.venv/bin/clang-format"
PROJECT = Path("/home/rs/projects/opencs/ai-line-analysis")
CONTROL = Path("temp/recovery-work/control10x20-after-4fed70d11")
FROZEN = PROJECT / CONTROL / "packeting/actual06-first-capture01/snapshot"
SNAPSHOT = FROZEN.parent / "SNAPSHOT.json"
SNAPSHOT_SHA = "8b98e9e1c416f6ae3ebc6207c9434f298eebd6f37f812bdd9ccf3516e555846f"
ELFS = [FROZEN / "rootfs/RML16AI_Rack_13731/home/root/mixer"]
if METER:
    ELFS.append(FROZEN / "rootfs/CS18_v13840/home/root/surface")
REVIEW_PATH = ("meter-ballistics/table.native01.json" if METER else
               "offline-default-replacement-reserves/NATIVE_OMAP_PROPERTY_G02_R02.json")
REVIEW = FROZEN / CONTROL / "selection" / REVIEW_PATH
REVIEW_SHA = ("52cd73733679ca6b37396384198fd3df680e8d8d307e5859d5ceb534ce2e9514" if METER else
              "c58011e7c9d4c3c16b99237a864d9f49e66b5120b3a2ff501d6443ef8c5942c8")
DOMAIN = (
    "Each exact RM and CS18 C1 executes the genuine ARM constructor, arithmetic and comparison "
    "helpers. Five finite six-breakpoint vectors per role include the four reviewed inputs and "
    "straddle the -144 dB clamp. All ten output binary32 words match per invocation. The original "
    "powf PLT relocation is verified and uses actual Linux libm at the explicit boundary. "
    "The original input and output guard bytes remain intact."
    if METER else
    "Six exact RM direct/primary-vtable executions, three seeded receiver and property "
    "states each. Native memory accesses are confined to the stack and the two vtable "
    "reads on virtual calls. Valid typed portable receiver and Core Property state remain unchanged."
)
LIMITS = (
    ["Bounded portable constructor with six readable floats and a finite, nonzero last interval. "
     "Non-finite inputs, exceptional arithmetic, device behavior and native object layout are outside scope.",
     "Both exact original C1 rows were checked. The C++ compiler also exports the usual C2 "
     "symbol, for which neither original ELF has a corresponding symbol. It is outside admission.",
     "Native libm powf is an identified external boundary implemented by actual Linux libm. "
     "The original firmware's dynamic library compatibility is outside scope."]
    if METER else
    ["Portable void return. Original r0 retains the receiver with no consumed result established.",
     "The source-port virtual member preserves the deliberate class-local boundary. Original "
     "inheritance, full vtable order, binary interoperability and hardware are unresolved.",
     "The separately implemented release method remains outside these getter cases."]
)
CORE_PIN = "e8cbdea4a4a20e15111f5a690798a259c0374b31"
CORE_PATHS = [f"third_party/ccl-framework/core/public/{name}.h" for name in
              ("coreproperty", "coretypes", "coreplatform", "coreclibrary", "coremalloc")] if not METER else []
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


def provider_binding():
    assert digest(SNAPSHOT) == SNAPSHOT_SHA
    files = json.loads(SNAPSHOT.read_text())["files"]
    providers = {name: files[name] for name in CORE_PATHS}
    for name, expected in providers.items():
        assert digest(name) == expected == digest(FROZEN / name)
    return providers


def compile_inputs():
    providers = provider_binding()
    depfiles = []
    operands = {}
    for stem in ("production", "replay"):
        depfile = SCRATCH / f"{stem}.d"
        depfiles.append(bind(depfile))
        for name in depfile.read_text().replace("\\\n", " ").split()[1:]:
            operands[name] = bind(name)
    assert set(operands) - {str(p) for p in (HEADER, SOURCE, REPLAY)} == set(providers)
    for name, expected in providers.items():
        assert operands[name]["sha256"] == expected
        operands[name]["frozen_read_path"] = str(FROZEN / name)
    return dict(snapshot=bind(SNAPSHOT), core_pin=None if METER else CORE_PIN,
                depfiles=depfiles, operands=operands)


def compile_local():
    flags = ["c++", "-std=c++20", "-fno-rtti", "-Wno-multichar", "-Iuc-library/include",
             "-Ithird_party/ccl-framework"]
    if METER:
        flags.extend(["-fno-fast-math", "-ffp-contract=off"])
    for stem, source in (("production", SOURCE), ("replay", REPLAY)):
        run([*flags, "-MMD", "-MF", SCRATCH / f"{stem}.d", "-c", source,
             "-o", SCRATCH / f"{stem}.o"])
    run(["c++", SCRATCH / "replay.o", SCRATCH / "production.o",
         "-lm", "-o", SCRATCH / "replay"])
    compile_inputs()


def compare(native, executable):
    assert digest(REVIEW) == REVIEW_SHA
    previous = json.loads(REVIEW.read_text())
    if METER:
        old_by_hash = {row["elf_sha256"]: row for row in previous["exact_originals"].values()}
        targets, payload, expected = [], [], []
        for original in native["originals"]:
            elf = original["elf"]["sha256"]
            target = original["target"]
            old = old_by_hash[elf]
            assert (target["address"], target["size"], target["sha256"]) == (
                old["address"], old["size"], old["range_sha256"])
            for index, case in enumerate(original["cases"]):
                if index < len(old["cases"]):
                    for key in ("inputs", "outputs"):
                        assert case[key] == old["cases"][index][key]
                payload.append(" ".join(map(str, [original["role"], *case["input_bits"]])))
                expected.append(" ".join(map(str, [original["role"], *case["outputs"]])))
            targets.append((elf, target["mangled"], original["role"]))
    else:
        old, = previous["rows"]
        for fresh, earlier in zip(native["cases"], old["cases"], strict=True):
            assert all(value == earlier[key] for key, value in fresh.items()
                       if key != "property_unchanged")
        targets = [(native["elf"]["sha256"], native["mangled"], "server")]
        payload = [f"{c['dispatch']} {c['seed']}" for c in native["cases"]]
        expected = [f"{row} {int(c['whole_state_unchanged'] and c['property_unchanged'])}"
                    for row, c in zip(payload, native["cases"], strict=True)]
    outputs = run([executable.resolve()], "\n".join(payload) + "\n").splitlines()
    assert outputs == expected, (outputs, expected)
    return targets, outputs


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
    executable = args.exe or SCRATCH / "replay"
    fixture = TEST / "fixtures.json"
    sealed = json.loads(fixture.read_text())
    mangled = sealed["originals"][0]["target"]["mangled"] if METER else sealed["mangled"]
    table = {cols[-1]: cols[-2] for line in run(["nm", "--defined-only", production]).splitlines()
             if len(cols := line.split()) >= 3}
    assert table[mangled] == ("T" if METER else "W")
    if METER:
        assert mangled.replace("C1E", "C2E") in table
        assert "powf" in run(["nm", "--undefined-only", production])
    else:
        assert table["_ZN8Presonus3Dsp17OMAPTargetHandler7releaseEv"] == "W"
    if args.mode == "symbols":
        return
    producer = TEST / "native.py"
    native = json.loads(run([PYTHON, "-B", producer, *ELFS]))
    assert native == sealed
    targets, output = compare(native, executable)
    sources = {str(path.relative_to("uc-library")): digest(path) for path in (HEADER, SOURCE)}
    providers = provider_binding()
    rows = []
    for elf, name, role in targets:
        row = dict(original_elf_sha256=elf, mangled=name, sources=sources,
                   repository_sources=providers, domain=DOMAIN, cpp_compiled=True,
                   mangling_namespace_checked=True, portable_ready=METER,
                   role=role)
        if not METER:
            row["declaration_uncertainties"] = LIMITS
        rows.append(row)
    proof = dict(task_id=TASK, session_id=os.environ.get("CODEX_THREAD_ID"),
                 desktop_session_id=os.environ.get("CODEX_SESSION_ID"), start_utc=start,
                 native=native, portable_rows=output, case_count=len(output),
                 previous_native_review=bind(REVIEW), cpp_differential_passed=True,
                 compiled_mangled_names_matched=True, mangled_names=[mangled],
                 functions=rows, proposed_readiness={"ready": rows if METER else [],
                                                      "pending": [] if METER else rows},
                 sources=sources, repository_sources=providers, validation_domain=DOMAIN,
                 limitations=LIMITS, native_producer=bind(producer), fixture=bind(fixture),
                 checker=bind(TEST / "check.py"), production=bind(production),
                 executable=bind(executable), format_check_passed=True,
                 formatter=run([FORMAT, "--version"]).strip(),
                 compiler=run(["c++", "--version"]).splitlines()[0],
                 native_versions=run([PYTHON, "-B", "-c",
                                      "import elftools,unicorn; print(elftools.__version__,unicorn.__version__)"]).strip())
    if METER:
        dependencies = run(["ldd", executable.resolve()])
        [libm] = [line.split()[2] for line in dependencies.splitlines() if "libm.so.6 =>" in line]
        proof["libm"] = binding = bind(Path(libm).resolve())
        native_libm = run([PYTHON, "-B", "-c",
                          "import ctypes; from pathlib import Path; "
                          "a=ctypes.CDLL('libm.so.6'); "
                          "print(next(x.split()[-1] for x in Path('/proc/self/maps').read_text().splitlines() if '/libm.so.6' in x))"]).strip()
        assert binding["sha256"] == digest(native_libm)
    if args.integration:
        proof["integration"] = bind(args.integration)
    else:
        proof["dependency_receipt"] = compile_inputs()
    proof["tool_timings"] = TIMES
    proof["end_utc"] = utc()
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(proof, indent=2) + "\n")
    print(f"{TASK}: matched {len(output)} original cases. {DOMAIN}")


if __name__ == "__main__":
    main()
