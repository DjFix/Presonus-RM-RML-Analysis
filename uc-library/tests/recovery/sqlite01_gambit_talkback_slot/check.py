"""Validate the Linux source port against bounded original ARM observations."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess

TASK = "sqlite01_gambit_talkback_slot"
TEST = Path("uc-library/tests/recovery") / TASK
OUT = Path("temp/recovery-work") / TASK
SOURCE = Path("uc-library/src/Presonus/Mixer/GambitMixerComponent.cpp")
HEADER = Path("uc-library/include/presonus/mixer/GambitMixerComponent.hpp")
DRIVER = TEST / "Replay.cpp"
FORMATTER = "uc-library/.venv/bin/clang-format"
FORMAT = [FORMATTER, "--style=file", "--fallback-style=LLVM", "--dry-run", "--Werror",
          *map(str, (SOURCE, HEADER, DRIVER))]
CXX = ["/usr/bin/c++", "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror", "-Iuc-library/include"]
MANGLED = "_ZN8Presonus5Mixer20GambitMixerComponent20getDanteTalkbackSlotEv"
DOMAIN = ("Two separately seeded ARM calls, each returning R0=57, preserving the "
          "receiver and canaries, writing only to the 16-byte stack frame and "
          "making no external calls. Compare portable calls on separately "
          "constructed receivers bracketed by seeded canaries.")
LIMITS = [
    "The original return type and static/member/virtual traits are unresolved. "
    "The host uses a provisional signed 32-bit non-static, non-virtual declaration.",
    "ARM uses synthetic receiver storage and an emulated stack. Original layout, "
    "construction, lifecycle, ARM interoperability and hardware behavior are unverified.",
]


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def exact_symbol(path):
    argv = ["/usr/bin/nm", "--defined-only", str(path)]
    line, = [line for line in subprocess.check_output(argv, text=True).splitlines()
             if line.split()[-1:] == [MANGLED]]
    return {"argv": argv, "matched": line}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["format", "compile", "symbols", "proof"])
    parser.add_argument("--exe", type=Path, default=OUT / "Replay")
    parser.add_argument("--object", type=Path, default=OUT / "GambitMixerComponent.o")
    parser.add_argument("--fixtures", type=Path, default=TEST / "fixtures.json")
    parser.add_argument("--integration", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    compile_obj = [*CXX, "-c", str(SOURCE), "-o", str(args.object)]
    link = [*CXX, str(DRIVER), str(args.object), "-o", str(args.exe)]
    if args.mode == "format":
        subprocess.run(FORMAT, check=True)
        return
    if args.mode == "compile":
        OUT.mkdir(parents=True, exist_ok=True)
        for command in (compile_obj, link):
            subprocess.run(command, check=True)
        return
    symbol = exact_symbol(args.object)
    if args.mode == "symbols":
        print(symbol["matched"])
        return
    subprocess.run(FORMAT, check=True)
    native = json.loads(args.fixtures.read_bytes())
    assert native["original"]["mangled"] == MANGLED
    cases = native["cases"]
    assert cases and all(case["external_calls"] == 0 for case in cases)
    argv = [str(args.exe)]
    values = subprocess.check_output(argv, text=True,
                                     input="".join(f'{case["seed"]}\n' for case in cases))
    values = [list(map(int, line.split())) for line in values.splitlines()]
    assert values == [[case["result"], int(case["receiver_unchanged"]),
                       int(case["stack_canaries_unchanged"])] for case in cases]
    print(f"{len(cases)} portable cases passed")
    if args.out is None:
        return
    integration_digest = None
    if args.integration:
        integration = json.loads(args.integration.read_bytes())
        assert integration["platform"] == "linux" and integration["ctest_passed"] is True
        integration_digest = digest(args.integration)
    sources = {str(path.relative_to("uc-library")): digest(path) for path in (SOURCE, HEADER)}
    row = dict(original_elf_sha256=native["original"]["elf"], mangled=MANGLED,
               cpp_compiled=True, mangling_namespace_checked=True, portable_ready=False,
               validation_domain=DOMAIN, sources=sources, repository_sources={},
               declaration_uncertainties=[LIMITS[0]])
    proof = dict(task_id=TASK, cpp_differential_passed=True, compiled_mangled_names_matched=True,
                 format_check_passed=True, portable_ready=False, validation_domain=DOMAIN,
                 limitations=LIMITS, mangled_names=[MANGLED], functions=[row],
                 proposed_readiness={"ready": [], "pending": [row]},
                 formatter_version=subprocess.check_output([FORMATTER, "--version"], text=True).strip(),
                 format_argv=FORMAT,
                 formatted_files={str(path.relative_to("uc-library")): digest(path)
                                  for path in (SOURCE, HEADER, DRIVER)},
                 fixture_sha256=digest(args.fixtures), native=native,
                 portable=dict(argv=argv, case_count=len(values), results=values),
                 compiled_symbol=symbol, object_sha256=digest(args.object),
                 exe_sha256=digest(args.exe), integration_sha256=integration_digest,
                 integration=str(args.integration) if args.integration else None,
                 producer_inputs={str(TEST / name): digest(TEST / name)
                                  for name in ("native.py", "check.py")})
    if not args.integration:
        proof.update(compile_argv=compile_obj, link_argv=link,
                     compiler_version=subprocess.check_output([CXX[0], "--version"], text=True).splitlines()[0])
    args.out.write_text(json.dumps(proof, indent=2) + "\n")


if __name__ == "__main__":
    main()
