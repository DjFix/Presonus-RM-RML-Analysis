"""Check callback mangling, native observations and actual CCL replay."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import subprocess

import native

TASK = Path(__file__).parent.name
LIB = Path("uc-library")
SOURCES = ['src/Presonus/PageComponent.cpp', 'include/presonus/PageComponent.hpp']
DEPENDENCIES = []
CORE = [f"third_party/ccl-framework/core/portable/{file}.{extension}"
        for file in ("corecomponent", "coreparams") for extension in ("cpp", "h")]
DOMAIN = "Both bool values and two initialized ARM receivers; exact Page hook only touches its stack and returns. Canonical typed Page replay compares tag, form, stored page byte, visibility and borrowed-provider call count."
LIMITATION = ("Ordinary original return declaration remains unresolved. The portable void "
              "callback models the observed side effects. The effects of platform and Core "
              "calls in the native process are bounded by the named test hooks. Original "
              "inheritance, vtable, layout, ARM ABI and hardware behavior are unresolved.")


def digest(path):
    return hashlib.file_digest(path.open("rb"), "sha256").hexdigest()


def expected_cases(document):
    for row in document["cases"]:
        assert not row["events"]
        visible = row["visible"]
        state = [98, "one", 27, 1] if visible else [-43, "two", 9, 0]
        yield [row["show"], visible], [*state, *state, 0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("exe", "object", "fixture", "integration", "out"):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--symbols-only", action="store_true")
    args = parser.parse_args()
    symbol_argv = ["nm", "--defined-only", str(args.object)]
    symbols = subprocess.check_output(symbol_argv, text=True).splitlines()
    hits = [line for line in symbols if line.split()[-2:] == ["T", native.NAME]]
    if len(hits) != 1:
        raise ValueError(f"Expected one defined symbol {native.NAME}: {hits}")
    if args.symbols_only:
        print(hits[0])
        return
    start = datetime.datetime.now(datetime.timezone.utc).isoformat()
    document = json.loads(args.fixture.read_text())
    results = []
    for inputs, expected in expected_cases(document):
        command = [str(args.exe.resolve()), *map(str, inputs)]
        actual = subprocess.check_output(command, text=True).split()
        if actual != list(map(str, expected)):
            raise ValueError(f"Case {inputs}: observed {actual}, expected {expected}")
        results.append(dict(inputs=inputs, observed=actual))
    if not results:
        raise ValueError("Missing replay cases")
    formatter = str(LIB / ".venv/bin/clang-format")
    fmt = [formatter, "--style=file", "--fallback-style=LLVM", "--dry-run", "--Werror",
           *[str(LIB / source) for source in SOURCES], str(Path(__file__).with_name("Replay.cpp"))]
    subprocess.run(fmt, check=True)
    row = dict(
        original_elf_sha256=document["elf_sha256"], mangled=native.NAME,
        validation_domain=DOMAIN, declaration_uncertainties=[LIMITATION],
        cpp_compiled=True, mangling_namespace_checked=True, portable_ready=False,
        sources={source: digest(LIB / source) for source in SOURCES},
        repository_sources={source: digest(Path(source)) for source in CORE})
    receipt = dict(
        task=TASK, replay_passed=True, validation_domain=DOMAIN,
        native_case_count=len(document["cases"]), case_count=len(results),
        original=dict(elf_sha256=document["elf_sha256"], native_ranges=document["ranges"]),
        proposed_readiness=dict(ready=[], pending=[row]), results=results,
        compile_symbol=hits[0], symbol_argv=symbol_argv,
        executable_sha256=digest(args.exe), object_sha256=digest(args.object),
        checker_sha256=digest(Path(__file__)), fixture_sha256=digest(args.fixture),
        native_producer_sha256=digest(Path(native.__file__)),
        canonical_provider_sources={source: digest(LIB / source) for source in DEPENDENCIES},
        formatter_argv=fmt,
        clang_format_version=subprocess.check_output([formatter, "--version"], text=True).strip(),
        validation_started_utc=start,
        validation_finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    if args.integration.is_file():
        receipt.update(integration_path=str(args.integration), integration_sha256=digest(args.integration))
    elif args.integration.name != "local-no-integration.json":
        raise FileNotFoundError(args.integration)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(receipt, indent=2) + "\n")
    print(f"{TASK}: replayed {len(results)} portable CCL cases")


if __name__ == "__main__":
    main()
