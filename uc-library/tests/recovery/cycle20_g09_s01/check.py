"""Check the exact Rack symbol and replay observations from the isolated ARM range."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

LIB = Path("uc-library")
SOURCES = ("include/presonus/mixer/RackMixerComponent.hpp",
           "src/Presonus/Mixer/RackMixerComponent.cpp")
PROVIDERS = ("include/presonus/mixer/MixerComponentBase.hpp",)
CORE = Path("third_party/ccl-framework/core")
CORE_SOURCES = (CORE / "portable/corefilename.cpp", CORE / "portable/corefilename.h",
                CORE / "public/corevector.h")
TASK = "cycle20_g09_s01"
MANGLED = "_ZNK8Presonus5Mixer18RackMixerComponent19supportSubgroupModeEv"
DOMAIN = ("Four isolated ARM receiver patterns with stack-only accesses and no calls, "
          "compared with the named const capability on the canonical RackMixerComponent. "
          "Host cases verify the numeric return, borrowed cascade word, selected base "
          "fields and channel view, and owned route vector and auxiliary count.")
UNCERTAINTY = ("The original static return declaration remains unresolved; bool models "
               "observed r0=1. Original inheritance, layout, virtual dispatch ABI, "
               "derived substitutions and all hardware or routing behavior are outside scope.")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("exe", "object", "fixture", "integration", "out"):
        parser.add_argument("--" + flag, type=Path, required=True)
    parser.add_argument("--symbols-only", action="store_true")
    args = parser.parse_args()
    started = now()
    fixtures = json.loads(args.fixture.read_text())
    original = fixtures["original"]
    if original["mangled"] != MANGLED:
        raise ValueError("Unexpected original identity in fixture")
    nm = ["nm", "--defined-only", str(args.object)]
    symbols = subprocess.check_output(nm, text=True).splitlines()
    matches = [line for line in symbols if line.split()[-2:] == ["T", MANGLED]]
    if len(matches) != 1:
        raise ValueError(f"Expected one defined Rack capability: {matches}")
    if args.symbols_only:
        print(matches[0])
        return
    cases = fixtures["cases"]
    expected = [(case["pattern"], case["return_r0"], int(case["state_unchanged"]))
                for case in cases]
    output = subprocess.check_output([str(args.exe.resolve())], text=True)
    actual = [tuple(map(int, line.split())) for line in output.splitlines()]
    if len(expected) != 4 or actual != expected:
        raise ValueError(f"Host observations {actual} differ from ARM observations {expected}")

    formatter = str(LIB / ".venv/bin/clang-format")
    format_argv = [formatter, "--style=file", "--fallback-style=LLVM", "--dry-run", "--Werror",
                   *(str(LIB / source) for source in SOURCES),
                   str(Path(__file__).with_name("Replay.cpp"))]
    subprocess.run(format_argv, check=True)
    row = dict(original_elf_sha256=original["elf_sha256"], mangled=MANGLED,
               cpp_compiled=True, mangling_namespace_checked=True, portable_ready=False,
               declaration_uncertainties=[UNCERTAINTY], validation_domain=DOMAIN,
               sources={name: digest(LIB / name) for name in (*SOURCES, *PROVIDERS)},
               repository_sources={str(path): digest(path) for path in CORE_SOURCES})
    proof = dict(task=TASK, replay_passed=True, cpp_differential_passed=True,
                 compiled_mangled_names_matched=True, mangled_names=[MANGLED],
                 portable_ready=False, case_count=len(actual), validation_domain=DOMAIN,
                 proposed_readiness=dict(ready=[], pending=[row]), original=original,
                 host_observations=actual, native_observations=cases,
                 symbol_argv=nm, compiled_symbol=matches[0],
                 executable_sha256=digest(args.exe), object_sha256=digest(args.object),
                 checker_sha256=digest(Path(__file__)), fixture_sha256=digest(args.fixture),
                 native_producer_sha256=digest(Path(__file__).with_name("native.py")),
                 formatter_argv=format_argv,
                 clang_format_version=subprocess.check_output([formatter, "--version"],
                                                             text=True).strip(),
                 validation_started_utc=started, validation_finished_utc=now())
    if args.integration.is_file():
        proof.update(integration_path=str(args.integration),
                     integration_sha256=digest(args.integration))
    elif args.integration.name != "local-no-integration.json":
        raise FileNotFoundError(args.integration)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(proof, indent=2) + "\n")
    print(f"{TASK}: {len(actual)} native/portable observations matched")


if __name__ == "__main__":
    main()
