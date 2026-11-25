"""Compile and replay the DigitalPotControl constructor against exact ARM observations."""
import argparse
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys

import native

ROOT = Path(__file__).resolve().parents[4]
TEST = Path(__file__).resolve().parent.relative_to(ROOT)
TASK = TEST.name
SCRATCH = Path("temp/recovery-work") / TASK
SOURCE = Path("uc-library/src/surface_panel/DigitalPotControl.cpp")
HEADER = Path("uc-library/include/presonus/surface_panel/DigitalPotControl.hpp")
CONTROL = Path("uc-library/src/Presonus/Panel/control.cpp")
CONTROL_HEADER = Path("uc-library/include/presonus/panel/control.hpp")
REPLAY = TEST / "Replay.cpp"
FORMAT = ["uc-library/.venv/bin/clang-format", "--style=file",
          "--fallback-style=LLVM", "--dry-run", "--Werror", SOURCE, HEADER, REPLAY]
CXX = ["/usr/bin/c++", "-std=c++17", "-Wall", "-Wextra", "-Wno-multichar",
       "-Iuc-library/include", "-isystem", "third_party/ccl-framework", "-Ulinux"]
BUILD = native.PROJECT / "temp/core-upstream/root-integration-01"
CORE_LIB = BUILD / "upstream-core/sdk/lib"
LIBRARIES = [BUILD / "libpresonus_uc.a", CORE_LIB / "libcorelib.a"]
CORE_PROVENANCE = BUILD / "upstream-core/sdk/share/presonus-core-5/provenance.json"
BASE = TASK.endswith("c2")
DOMAIN = (
    "Six signed tags from INT_MIN through INT_MAX on distinct sentinel-filled "
    "receivers, for each of two exact original ARM entries. The host replay "
    "checks the DigitalPotControl specialization, separately constructed real "
    "Control provider, and a copy after the original lifetime against the six "
    "observable base-state words. Also checks the preexisting borrowed state "
    "and endpoint across a copy and destruction of the first borrower."
)
LIMITATIONS = [
    "ARM execution verifies the original vtable literal independently of the "
    "portable host vtable. No ARM layout, binary interoperability or hardware claim.",
    "The portable owned value duplicates the initial last-level observation. "
    "The original writes only seven receiver words, including the vtable pointer. "
    "The owned storage and optional boundary callbacks are source-port design.",
    "Parameter binding, actual writes to devices and transport remain outside "
    "this constructor domain. Offline endpoint test only checks borrowed-copy behavior.",
]


def hash_file(path):
    return native.digest(Path(path).read_bytes())


def binding(path):
    return dict(path=str(path), sha256=hash_file(path))


def run(argv, **options):
    args = list(map(str, argv))
    print(json.dumps(args), flush=True)
    return subprocess.run(args, check=True, cwd=ROOT, text=True,
                          stdout=subprocess.PIPE, **options).stdout


def symbols(obj, replay_object=None):
    original = "_ZN8Presonus5Panel17DigitalPotControlC"
    rows = run(["/usr/bin/nm", "--defined-only", obj]).splitlines()
    definitions = [line for line in rows
                   if line.split()[-1:] in [[original + "1Ei"], [original + "2Ei"]]]
    assert len(definitions) == 2 and all(line.split()[-2] == "T" for line in definitions)
    if replay_object:
        variant = original + ("2Ei" if BASE else "1Ei")
        undefined = run(["/usr/bin/nm", "--undefined-only", replay_object])
        assert any(line.split()[-1] == variant for line in undefined.splitlines())
        assert "_ZN8Presonus5Panel7ControlC1Ei" in undefined
    return definitions


def compile_local(obj, exe):
    SCRATCH.mkdir(parents=True, exist_ok=True)
    replay_object = SCRATCH / "replay.o"
    control_obj = SCRATCH / "control.o"
    records = []
    for source, product, flags in (
        (SOURCE, obj, ["-fno-rtti", "-fno-sized-deallocation"]),
        (CONTROL, control_obj, ["-fno-rtti"]),
        (REPLAY, replay_object,
         ["-fno-rtti", *(["-DDIGITAL_POT_BASE_CONSTRUCTOR"] if BASE else [])]),
    ):
        depfile = product.with_suffix(".d")
        command = [*CXX, *flags, "-MD", "-MF", depfile, "-c", source, "-o", product]
        run(command)
        deps = shlex.split(depfile.read_text().replace("\\\n", "").split(":", 1)[1])
        records.append(dict(cwd=str(ROOT), argv=list(map(str, command)), object=binding(product),
                            depfile=binding(depfile), dependencies=[binding(dep) for dep in deps]))
    link_map = SCRATCH / "link.map"
    link = [CXX[0], obj, control_obj, replay_object, *LIBRARIES,
            "-pthread", "-ldl", "-lm", "-Wl,-Map," + str(link_map), "-o", exe]
    run(link)
    link_text = link_map.read_text()
    link_inputs = {line.removeprefix("LOAD ") for line in link_text.splitlines()
                   if line.startswith("LOAD ")}
    archive_members = []
    for archive, member in re.findall(r"^([^\s()]+\.a)\(([^()]+)\)$", link_text,
                                     re.MULTILINE):
        contents = subprocess.check_output(["/usr/bin/ar", "p", archive, member], cwd=ROOT)
        archive_members.append(dict(archive=archive, member=member,
                                    sha256=native.digest(contents)))
    metadata = dict(compiles=records, link=dict(cwd=str(ROOT), argv=list(map(str, link)),
                    inputs=[binding(path) for path in sorted(link_inputs)],
                    included_archive_members=archive_members,
                    map=binding(link_map), executable=binding(exe)),
                    core_provenance=binding(CORE_PROVENANCE))
    (SCRATCH / "build.json").write_text(json.dumps(metadata, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", nargs="?", default="proof",
                        choices=("format", "compile", "symbols", "native", "proof"))
    parser.add_argument("--exe", type=Path, default=SCRATCH / "replay")
    parser.add_argument("--object", type=Path, default=SCRATCH / "digital-pot.o")
    parser.add_argument("--fixture", type=Path, default=TEST / "fixtures.json")
    parser.add_argument("--integration", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.mode == "format":
        run(FORMAT)
        return
    if args.mode == "compile":
        compile_local(args.object, args.exe)
        return
    local = args.exe == SCRATCH / "replay"
    if args.mode == "symbols":
        print(symbols(args.object, SCRATCH / "replay.o" if local else None))
        return

    observations = json.loads(json.dumps(native.generate()))
    assert observations == json.loads(args.fixture.read_text())
    cases = [case for role in observations for case in role["cases"]]
    print(f"{len(cases)} independent original ARM executions passed")
    if args.mode == "native":
        return
    assert args.out is not None
    run(FORMAT)
    definitions = symbols(args.object, SCRATCH / "replay.o" if local else None)
    payload = "".join(f"{row['tag']}\n" for row in cases)
    host = run([args.exe], input=payload).splitlines()
    expected = [row["receiver_words"][1:] * 3 for row in cases]
    assert [list(map(int, line.split())) for line in host] == expected
    print(f"{len(cases)} portable comparisons and borrowed-copy checks passed")
    sources = {str(path.relative_to("uc-library")): hash_file(path)
               for path in (SOURCE, HEADER, CONTROL, CONTROL_HEADER)}
    build = json.loads((SCRATCH / "build.json").read_text()) if local else None
    core_paths = set()
    if build:
        for compile in build["compiles"]:
            for dependency in compile["dependencies"]:
                path = dependency["path"]
                if path.startswith("third_party/ccl-framework/"):
                    core_paths.add(path)
    else:
        core_paths.update(("third_party/ccl-framework/core/portable/coreparams.h",
                           "third_party/ccl-framework/core/public/corevector.h"))
    providers = {path: hash_file(path) for path in sorted(core_paths)}
    results = [
        dict(original_elf_sha256=row["original"]["elf"], mangled=row["original"]["mangled"],
             original_address=row["original"]["address"], cpp_compiled=True,
             mangling_namespace_checked=True, portable_ready=False, domain=DOMAIN,
             sources=sources, repository_sources=providers, declaration_uncertainties=LIMITATIONS)
        for row in observations
    ]
    proof = dict(version=1, task_id=TASK, domain=DOMAIN, limitations=LIMITATIONS,
                 cpp_compiled=True, mangling_namespace_checked=True,
                 cpp_differential_passed=True, formatting_verified=True, compiled=True,
                 compiled_mangled_names_matched=True, fresh_native_execution=True,
                 native_behavior_verified=True, original_declaration_verified=False,
                 original_arm_abi_verified=False, hardware_verified=False,
                 portable_ready=False, canonical_binding_pending=local, functions=results,
                 proposed_readiness=dict(ready=[], pending=results),
                 command=[sys.executable, "-B", *sys.argv],
                 formatter_version=run([FORMAT[0], "--version"]).strip(),
                 compiler_version=run([CXX[0], "--version"]).splitlines()[0],
                 unicorn_version=__import__("unicorn").__version__, sources=sources,
                 repository_sources=providers, oracle=binding(TEST / "native.py"),
                 producer_sha256=hash_file(__file__), fixture=binding(args.fixture),
                 ranges=[row["original"] for row in observations],
                 vtable_points=[row["literal"] for row in observations],
                 native_cases=len(cases), portable_cases=len(host), symbols=definitions,
                 object=binding(args.object), executable=binding(args.exe), build=build,
                 integration=binding(args.integration) if args.integration else None)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(proof, indent=2) + "\n")


if __name__ == "__main__":
    main()
