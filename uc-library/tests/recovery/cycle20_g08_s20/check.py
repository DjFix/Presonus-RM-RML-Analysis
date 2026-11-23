"""Build and check the scoped portable AlertBook constructor replay."""
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
HEADER = Path("uc-library/include/presonus/panel/AlertBook.hpp")
SOURCE = Path("uc-library/src/Presonus/Panel/AlertBook.cpp")
SCRATCH = Path("temp/recovery-work/cycle20_g08-local/s20")
FORMATTER = "uc-library/.venv/bin/clang-format"
FORMAT = [FORMATTER, "--style=file", "--fallback-style=LLVM", "--dry-run", "--Werror",
          HEADER, SOURCE, TEST / "Replay.cpp"]
CORE = Path("third_party/ccl-framework/core")
PROVIDERS = [CORE / f for f in ("portable/corecomponent.h", "portable/corecomponent.cpp",
                                "portable/coreparams.cpp", "portable/coreparams.h",
                                "portable/coreparaminfo.h", "public/corevector.h")]
BOOK_INPUTS = tuple(Path(f) for f in ("uc-library/include/presonus/panel/Book.hpp",
                                     "uc-library/src/Presonus/Panel/Book.cpp",
                                     "uc-library/include/presonus/panel/Page.hpp",
                                     "uc-library/include/presonus/panel/Element.hpp",
                                     "uc-library/include/presonus/panel/TextEntryElement.hpp"))
BUILD = Path("temp/core-upstream/root-integration-01")
ARCHIVES = [BUILD / f for f in ("libpresonus_rm_components.a", "libpresonus_uc.a",
                               "upstream-core/sdk/lib/libcorelib.a",
                               "upstream-core/sdk/lib/libpresonus_core_allocator.a",
                               "private-glibc29-provider/libpresonus_private_glibc29.a")]
DOMAIN = ("Both separately mapped and run exact RM AlertBook constructors, with 0, 41 and -1 "
          "arguments. Normal path only. Native Book, Component and ParamList boundaries are "
          "modeled; live host Book and pinned CCL compare the input, component identity, "
          "initial neutral state and the actual ordered three-parameter roster.")
LIMITS = ["Original ARM layout, C++ class ABI and unwind behavior are outside scope.",
          "Portable construction composes host Book and Component. Copy and destructor "
          "behavior on the new owned path are not compared to original ABI variants.",
          "The existing borrowed constructor still uses its external provider."]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("format", "compile", "symbols", "replay"))
    parser.add_argument("--exe", type=Path, default=SCRATCH / "Replay")
    parser.add_argument("--object", type=Path, default=SCRATCH / "AlertBook.cpp.o")
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
        flags = ["/usr/bin/c++", "-std=c++17", "-O3", "-DNDEBUG", "-fno-rtti",
                 "-Wno-multichar", "-ffunction-sections", "-fdata-sections", "-pthread",
                 "-Ulinux", "-Iuc-library/include", "-Ithird_party/ccl-framework"]
        replay_object = SCRATCH / "Replay.cpp.o"
        book_object = SCRATCH / "Book.cpp.o"
        for source, output in ((SOURCE, args.object), (BOOK_INPUTS[1], book_object),
                               (TEST / "Replay.cpp", replay_object)):
            run(flags + ["-MMD", "-MF", str(output) + ".d", "-c", source, "-o", output])
        run(["/usr/bin/c++", replay_object, args.object, book_object, "-Wl,--start-group",
             *ARCHIVES, "-Wl,--end-group", "-Wl,--gc-sections", "-pthread", "-ldl", "-lm",
             "-o", args.exe])
        (SCRATCH / "compilation.json").write_text(json.dumps(commands, indent=2) + "\n")
        return
    originals = json.loads(args.fixtures.read_text())["originals"]
    symbols = run(["nm", "--defined-only", args.object])
    for original in originals:
        assert any(row.split()[-2:] == ["T", original["mangled"]] for row in symbols.splitlines())
    if args.mode == "symbols":
        return
    if args.out is None:
        parser.error("replay requires --out")
    run(FORMAT)
    formatter = run([FORMATTER, "--version"]).strip()
    cases = [row for original in originals for row in original["cases"]]
    actual = run([args.exe.resolve()], "".join(f"{row['initial_value']}\n" for row in cases))
    expected = []
    for row in cases:
        fields = [row["initial_value"], row["component"], int(row["state_zero"])]
        for param in row["roster"]:
            fields.extend(param[key] for key in ("kind", "tag", "name", "title"))
        expected.append("|".join(map(str, fields)))
    assert cases and actual.splitlines() == expected

    files = [HEADER, SOURCE, *BOOK_INPUTS, TEST / "Replay.cpp", TEST / "native.py",
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
