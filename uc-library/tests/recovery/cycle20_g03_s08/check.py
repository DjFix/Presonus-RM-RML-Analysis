"""Compare ChannelInfo ARM observations with actual CCL and icon enumeration."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import shlex
import subprocess

import native

TASK = Path(__file__).parent.name
NUMBER = int(TASK[-2:])
LIB = Path("uc-library")
SOURCES = [
    "src/Presonus/Surface/ChannelInfoPageComponent.cpp",
    "include/presonus/surface/ChannelInfoPageComponent.hpp",
]
CORE = [f"third_party/ccl-framework/core/portable/{file}.{ext}"
        for file in ("corecomponent", "coreparams", "corefilename") for ext in ("cpp", "h")]
DEPENDENCIES = ["src/IconManager.cpp", "include/presonus/IconManager.hpp",
                "include/presonus/utilities/string_utils.hpp"]
DOMAIN = "Both category and icon offsets, negative, zero and positive deltas, unchanged and clamped transitions, native lower-bound/no-query behavior, and observable actual CCL list refresh after stored offset changes."
LIMITATION = ("Original unencoded return declaration and ARM layout remain unresolved. "
              "Native tests use specified runtime, CCL and IconManager hooks; portable "
              "tests use the pinned CCL provider, actual IconManager and project-local "
              "filesystem fixtures. Native lifetime/global synchronization and panel "
              "behavior are outside scope.")


def digest(path):
    with Path(path).open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def prepare_fixture(path, inputs):
    icons = path / "bitmaps/trackicons"
    expected = {str(Path(name) / icon) for name in inputs["names"][1:] for icon in inputs["icons"]}
    for name in inputs["names"][1:]:
        directory = icons / name
        directory.mkdir(parents=True, exist_ok=True)
        for icon in inputs["icons"]:
            file = directory / icon
            if file.exists():
                assert file.is_file() and file.stat().st_size == 0
            else:
                with file.open("xb"):
                    pass
    icons.mkdir(parents=True, exist_ok=True)
    assert {str(file.relative_to(icons)) for file in icons.glob("*/*")} == expected


def expected(case):
    if NUMBER == 6:
        return [["result", case["result"], case["result"]]]
    events = []
    for event in case["events"]:
        if event[0] in ("label", "value"):
            assert event[3] == 0
            events.append(["change", event[1], event[2]])
    return [*events, ["state", *case["final_state"]]]


def actual_output(text):
    outcome = []
    for line in text.splitlines():
        event, *values = shlex.split(line)
        if event in ("change", "edit"):
            tag, value = values
            tag = int(tag)
            outcome.append([event, tag, int(float(value)) if tag % 2 else value])
        elif event in ("state", "result"):
            outcome.append([event, *map(int, values)])
        else:
            raise ValueError(f"Unexpected replay output: {line}")
    return outcome


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("exe", "object", "fixture", "integration", "out"):
        parser.add_argument("--" + flag, required=True, type=Path)
    parser.add_argument("--symbols-only", action="store_true")
    args = parser.parse_args()
    nm = ["nm", "--defined-only", str(args.object)]
    definitions = subprocess.check_output(nm, text=True).splitlines()
    matches = [line for line in definitions if line.split()[-2:] == ["T", native.NAME]]
    assert len(matches) == 1, matches
    if args.symbols_only:
        print(matches[0])
        return
    start = datetime.datetime.now(datetime.timezone.utc).isoformat()
    document = json.loads(args.fixture.read_text())
    rows = []
    fixture_parent = args.out.parent
    if not fixture_parent.resolve().is_relative_to(Path("temp").resolve()):
        fixture_parent = Path("temp/test-work") / TASK
    cases_root = fixture_parent / f"{args.out.stem}-icon-fixtures"
    for index, case in enumerate(document["cases"]):
        inputs = case["inputs"]
        path = cases_root / str(index)
        prepare_fixture(path, inputs)
        command = [str(args.exe.resolve()), str(NUMBER), str(path), str(inputs["type"]),
                   str(inputs.get("delta", 0)), *map(str, inputs["state"]),
                   inputs.get("ch_icon", ""), str(next(iter(inputs.get("missing_tags", [])), -1))]
        actual = actual_output(subprocess.check_output(command, text=True))
        target = expected(case)
        if actual != target:
            raise ValueError(f"{TASK} case {index}: observed {actual}, expected {target}")
        rows.append(dict(argv=command, result=actual))
    if not rows:
        raise ValueError("Missing portable test cases")
    formatter = "uc-library/.venv/bin/clang-format"
    tests = [Path(__file__).with_name("Replay.cpp"),
             Path(__file__).parent.parent / "cycle20_g03_s06/Replay.cpp"]
    fmt = [formatter, "--style=file", "--fallback-style=LLVM", "--dry-run", "--Werror",
           *map(str, dict.fromkeys([*(LIB / source for source in SOURCES), *tests]))]
    subprocess.run(fmt, check=True)
    row = dict(original_elf_sha256=document["elf_sha256"], mangled=native.NAME,
               validation_domain=DOMAIN, declaration_uncertainties=[LIMITATION],
               cpp_compiled=True, mangling_namespace_checked=True, portable_ready=False,
               sources={source: digest(LIB / source) for source in SOURCES},
               repository_sources={source: digest(source) for source in CORE})
    proof = dict(task=TASK, replay_passed=True, validation_domain=DOMAIN, native_case_count=len(rows),
                 case_count=len(rows), original=dict(elf_sha256=document["elf_sha256"],
                                                    native_ranges=document["ranges"]),
                 proposed_readiness=dict(ready=[], pending=[row]), results=rows,
                 compile_symbol=matches[0], symbol_argv=nm, executable_sha256=digest(args.exe),
                 object_sha256=digest(args.object), checker_sha256=digest(Path(__file__)),
                 fixture_sha256=digest(args.fixture), native_producer_sha256=digest(Path(native.__file__)),
                 shared_native_producer_sha256=digest(tests[-1].with_name("native.py")),
                 canonical_provider_sources={p: digest(LIB / p) for p in DEPENDENCIES},
                 format_argv=fmt,
                 clang_format_version=subprocess.check_output([formatter, "--version"], text=True).strip(),
                 validation_started_utc=start,
                 validation_finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    if args.integration.is_file():
        proof.update(integration_path=str(args.integration), integration_sha256=digest(args.integration))
    elif args.integration.name != "local-no-integration.json":
        raise FileNotFoundError(args.integration)
    args.out.write_text(json.dumps(proof, indent=2) + "\n")
    print(f"{TASK}: replayed {len(rows)} portable icon fixture cases")


if __name__ == "__main__":
    main()
