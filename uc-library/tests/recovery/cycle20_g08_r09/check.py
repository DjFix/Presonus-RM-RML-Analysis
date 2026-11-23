"""Build and check the scoped portable PreDelayFormatterT5 deleting destructor replay."""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

TASK = Path(__file__).resolve().parent.name
TEST = Path("uc-library/tests/recovery") / TASK
HEADER = Path("uc-library/include/presonus/mixer/PreDelayFormatterT5.hpp")
SOURCE = Path("uc-library/src/Presonus/Mixer/PreDelayFormatterT5.cpp")
SCRATCH = Path("temp/recovery-work/cycle20_g08-local/r09")
FORMATTER = "uc-library/.venv/bin/clang-format"
FORMAT = [FORMATTER, "--style=file", "--fallback-style=LLVM", "--dry-run", "--Werror",
          HEADER, SOURCE, TEST / "Replay.cpp"]
CORE = Path("third_party/ccl-framework/core")
PROVIDERS = [CORE / f for f in ("public/coreformatter.h", "public/coreformatter.cpp",
                                 "public/corestringbuffer.h", "public/coretypes.h")]
PARENT_INPUTS = tuple(Path(f) for f in ("uc-library/include/presonus/mixer/PreDelayFormatter.hpp",
                                       "uc-library/src/Presonus/Mixer/PreDelayFormatter.cpp"))
BUILD = Path("temp/core-upstream/root-integration-01")
ARCHIVES = [BUILD / f for f in ("libpresonus_rm_components.a", "libpresonus_uc.a",
                               "upstream-core/sdk/lib/libcorelib.a",
                               "upstream-core/sdk/lib/libpresonus_core_allocator.a",
                               "private-glibc29-provider/libpresonus_private_glibc29.a")]
DOMAIN = ("Exact deleting destructor in both offline firmware roles. Three seeded "
          "ARM heap receiver observations per role at the exact unsized deallocator. "
          "The receiver is unmapped and its post-return read fails; adjacent test data is "
          "unchanged. The host destroys the actual typed registered formatter through a "
          "CCL Formatter pointer and frees the same heap receiver at the unsized deallocator. "
          "The registered display path matches the real parent at three values.")
LIMITS = ["The exact original deallocator is a modeled native boundary.",
          "Native D1 is checked independently but does not receive readiness credit; the compiler "
          "may also emit a host D2 companion.",
          "Portable constructor and registry checks use the observed registered name, genuine "
          "application parent and pinned CCL registry. Original static initializer, class layout "
          "and ARM ABI are outside the claim."]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("format", "compile", "symbols", "replay"))
    parser.add_argument("--exe", type=Path, default=SCRATCH / "Replay")
    parser.add_argument("--object", type=Path, default=SCRATCH / "PreDelayFormatterT5.cpp.o")
    parser.add_argument("--fixtures", type=Path, default=TEST / "fixtures.json")
    parser.add_argument("--integration", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    commands = []

    def run(argv, stdin=None):
        argv = list(map(str, argv))
        observed_utc = dt.datetime.now(dt.timezone.utc).isoformat()
        start = time.monotonic()
        result = subprocess.run(argv, input=stdin, text=True, capture_output=True)
        item = dict(argv=argv, start_utc=observed_utc, seconds=time.monotonic() - start,
                    returncode=result.returncode, stdout=result.stdout, stderr=result.stderr)
        commands.append(item)
        print(json.dumps(item), flush=True)
        result.check_returncode()
        return result.stdout

    if args.mode == "format":
        run([FORMATTER, "--version"])
        run(FORMAT)
        return
    if args.mode == "compile":
        SCRATCH.mkdir(parents=True, exist_ok=True)
        flags = ["/usr/bin/c++", "-std=c++17", "-O3", "-DNDEBUG",
                 "-Wno-multichar", "-ffunction-sections", "-fdata-sections", "-pthread",
                 "-Ulinux", "-Iuc-library/include", "-Ithird_party/ccl-framework"]
        replay_object = SCRATCH / "Replay.cpp.o"
        parent_object = SCRATCH / "Parent.cpp.o"
        for source, output in ((SOURCE, args.object), (PARENT_INPUTS[1], parent_object),
                               (TEST / "Replay.cpp", replay_object)):
            run(flags + ["-MMD", "-MF", str(output) + ".d", "-c", source, "-o", output])
        run(["/usr/bin/c++", replay_object, args.object, parent_object, "-Wl,--start-group",
             *ARCHIVES, "-Wl,--end-group", "-Wl,--gc-sections", "-pthread", "-ldl", "-lm", "-lz",
             "-o", args.exe])
        (SCRATCH / "compilation.json").write_text(json.dumps(commands, indent=2) + "\n")
        return
    fixture = json.loads(args.fixtures.read_text())
    originals = fixture["originals"]
    symbols = run(["nm", "--defined-only", args.object])
    for original in originals:
        assert any(row.split()[-2:] == ["T", original["mangled"]] for row in symbols.splitlines())
    companion = fixture["related_companions"][0]["mangled"]
    assert any(row.split()[-2:] == ["T", companion] for row in symbols.splitlines())
    undefined = run(["nm", "--undefined-only", args.object])
    assert any(row.split()[-1] == "_ZdlPv" for row in undefined.splitlines())
    assert not any(row.split()[-1] == "_ZdlPvm" for row in undefined.splitlines())
    d0 = originals[0]["mangled"]
    assembly = run(["objdump", "-dr", f"--disassemble={d0}", args.object])
    assert "R_X86_64_PLT32" in assembly and "_ZdlPv-" in assembly and "_ZdlPvm-" not in assembly
    if args.mode == "symbols":
        return
    if args.out is None:
        parser.error("replay requires --out")
    run(FORMAT)
    formatter = run([FORMATTER, "--version"]).strip()
    cases = [(original["registered_name"], sample, companion_sample)
             for original, companion_row in zip(originals, fixture["related_companions"], strict=True)
             for sample, companion_sample in zip(original["cases"], companion_row["cases"], strict=True)]
    display_value = {1: "0.75", 99: "9.25", 255: "14.75"}
    stdin = "".join(display_value[row["seed"]] + "\n" for _, row, _ in cases)
    actual = run([args.exe.resolve()], stdin)
    expected = [f"{name}|{int(row['receiver_disposed'])}|{int(companion_row['receiver_disposed'])}"
                for name, row, companion_row in cases]
    assert cases and actual.splitlines() == expected

    files = [HEADER, SOURCE, *PARENT_INPUTS, TEST / "Replay.cpp", TEST / "native.py",
             TEST / "check.py", args.fixtures]
    bindings = {str(path.relative_to("uc-library")): sha(path) for path in files}
    entries = [dict(original_elf_sha256=original["elf_sha256"], mangled=original["mangled"],
                    original_address=original["address"], sources=bindings,
                    repository_sources={str(path): sha(path) for path in PROVIDERS},
                    domain=DOMAIN, portable_ready=True, cpp_compiled=True,
                    mangling_namespace_checked=True) for original in originals]
    proof = dict(version=1, task_id=TASK, producer_session_id=os.environ.get("CODEX_THREAD_ID"),
                 created_utc=dt.datetime.now(dt.timezone.utc).isoformat(), domain=DOMAIN,
                 functions=entries, proposed_readiness=dict(ready=entries, pending=[]),
                 compiled_mangled_names_matched=True, cpp_differential_passed=True,
                 cpp_compiled=True, portable_ready=True, original_arm_abi_verified=False,
                 hardware_verified=False, limitations=LIMITS, original_ranges=originals,
                 d1_companions=fixture["related_companions"],
                 case_count=len(cases), fixture_sha256=sha(args.fixtures), commands=commands,
                 formatter_version=formatter, executable=dict(path=str(args.exe), sha256=sha(args.exe)),
                 object=dict(path=str(args.object), sha256=sha(args.object)))
    if args.integration is not None:
        proof["integration"] = dict(path=str(args.integration), sha256=sha(args.integration))
    else:
        proof["compilation"] = json.loads((SCRATCH / "compilation.json").read_text())
        proof["local_provider_archives"] = {str(path): sha(path) for path in ARCHIVES}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(proof, indent=2) + "\n")


if __name__ == "__main__":
    main()
