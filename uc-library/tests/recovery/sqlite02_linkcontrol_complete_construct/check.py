"""Compile the bounded LinkControl replay, verify symbols, or replay a sealed fixture."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

import native

TASK = native.TASK
TEST = Path("uc-library/tests/recovery") / TASK
CANDIDATE = Path("uc-library/candidates") / TASK
SCRATCH = Path("temp/recovery-work") / TASK
SOURCE = Path("uc-library/src/Presonus/LinkControl.cpp")
HEADER = Path("uc-library/include/presonus/LinkControl.hpp")
FORMAT = ["uc-library/.venv/bin/clang-format", "--style=file", "--fallback-style=LLVM"]
CXX = ["/usr/bin/c++", "-std=c++17", "-fno-rtti", "-Wall", "-Wextra",
       "-Wno-multichar", "-Ulinux", "-Iuc-library/include",
       "-isystem", "third_party/ccl-framework"]
WRAPS = ["-Wl,--wrap=_ZdlPv", "-Wl,--wrap=_ZdlPvm",
         "-Wl,--wrap=_ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE"]
DOMAIN = (
    "Six original ARM executions and six matching Linux C++ lifecycle executions "
    "for the exact variant. Covers signed and empty rectangles, null and live primary "
    "and right-side Parameters, aliasing, replacement, empty/left/right/both borrowed "
    "bitmaps, observer removal order, base cleanup and receiver release where applicable. "
    "Three additional linked-provider tests destroy the primary, right side, or common "
    "Parameter before the widget and notify the surviving source afterward."
)
LIMITATIONS = [
    "Native Control and Parameter calls are verified typed boundaries. Native base "
    "construction uses an independently invoked pinned CCL Control, and destructor "
    "side effects of base cleanup use the pinned CCL source contract. Portable replay "
    "executes real linked CCL observer removal. No Core firmware bodies are replayed.",
    "The native deleting case reaches the original relocated _ZdlPv PLT boundary and "
    "releases only the associated guest mapping. Linux virtual delete reaches a wrapped "
    "real operator delete. Guest allocator internals, owned bitmap branches, exception "
    "unwinding, ARM ABI/layout and hardware are outside the observed domain.",
]
COMMANDS = []


def run(argv, **kwargs):
    args = list(map(str, argv))
    COMMANDS.append(args)
    print(json.dumps(args), flush=True)
    return subprocess.run(args, check=True, text=True, capture_output=True, **kwargs).stdout


def hash_file(path):
    return native.digest(Path(path).read_bytes())


def bind(path):
    return dict(path=str(path), sha256=hash_file(path))


def build_directory():
    for parent in (Path.cwd(), *Path.cwd().parents):
        build = parent / "temp/core-upstream/root-integration-01"
        if (build / "libpresonus_uc.a").is_file():
            return build
    raise FileNotFoundError("Canonical Linux build and pinned CCL archives are required")


def compile_local(obj, exe):
    SCRATCH.mkdir(parents=True, exist_ok=True)
    replay = SCRATCH / "Replay.o"
    for source, product in ((SOURCE, obj), (TEST / "Replay.cpp", replay)):
        run([*CXX, "-MD", "-MF", product.with_suffix(".d"), "-c", source, "-o", product])
    build = build_directory()
    sdk = build / "upstream-core/sdk/lib"
    libraries = [build / "libpresonus_uc.a", *(sdk / library for library in (
        "libcorelib.a", "libpresonus_core_allocator.a", "libpresonus_png.a",
        "libpresonus_zlib.a"))]
    run([CXX[0], obj, replay, "-Wl,--start-group", *libraries, "-Wl,--end-group",
         *WRAPS, "-pthread", "-ldl", "-lm", "-Wl,-Map," + str(SCRATCH / "link.map"),
         "-o", exe])
    metadata = dict(argv=COMMANDS, sources=[bind(SOURCE), bind(TEST / "Replay.cpp")],
                    objects=[bind(obj), bind(replay)],
                    archive_inputs=[bind(lib) for lib in libraries],
                    dependencies=[bind(obj.with_suffix(".d")), bind(replay.with_suffix(".d"))],
                    link_map=bind(SCRATCH / "link.map"), executable=bind(exe),
                    core_provider_provenance=bind(
                        sdk.parent / "share/presonus-core-5/provenance.json"))
    (SCRATCH / "build.json").write_text(json.dumps(metadata, indent=2) + "\n")


def symbols(obj, name):
    definitions = [row for row in run(["/usr/bin/nm", "--defined-only", obj]).splitlines()
                   if row.split()[-1].startswith("_ZN8Presonus11LinkControl")
                   and row.split()[-1].split("LinkControl", 1)[1][:2]
                   in ("C1", "C2", "D0", "D1", "D2")]
    assert len(definitions) == 5 and all(row.split()[-2] == "T" for row in definitions)
    assert name in {row.split()[-1] for row in definitions}
    return definitions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("format", "compile", "symbols", "fixture", "replay"))
    parser.add_argument("--exe", type=Path, default=SCRATCH / "replay")
    parser.add_argument("--object", type=Path, default=SCRATCH / "LinkControl.o")
    parser.add_argument("--fixture", type=Path, default=TEST / "fixtures.json")
    parser.add_argument("--proof", type=Path)
    parser.add_argument("--integration", type=Path)
    args = parser.parse_args()
    packet = json.loads(native.PACKET.read_text())
    original = packet["originals"][0]["original"]
    if args.mode == "format":
        run([*FORMAT, "--dry-run", "--Werror", HEADER, SOURCE, TEST / "Replay.cpp"])
        return
    if args.mode == "compile":
        compile_local(args.object, args.exe)
        return
    if args.mode == "symbols":
        print("\n".join(symbols(args.object, original["mangled"])))
        return
    fresh = native.generate(args.exe)
    if args.mode == "fixture":
        args.fixture.write_text(json.dumps(fresh, indent=2) + "\n")
        return
    assert fresh == json.loads(args.fixture.read_text())
    cases = fresh["cases"]
    inp = "".join(" ".join(map(str, row["inputs"])) + "\n" for row in cases)
    output = run([args.exe.resolve(), fresh["variant"]], input=inp)
    portable = [list(map(int, row.split())) for row in output.splitlines()]
    assert portable == [row["normalized"] for row in cases]
    print(f"{fresh['variant']}: {len(cases)} exact ARM executions and Linux C++ cases passed")
    if not args.proof:
        return
    definitions = symbols(args.object, original["mangled"])
    run([*FORMAT, "--dry-run", "--Werror", HEADER, SOURCE, TEST / "Replay.cpp"])
    sources = {str(path.relative_to("uc-library")): hash_file(path) for path in (HEADER, SOURCE)}
    providers = {record["path"]: hash_file(record["path"])
                 for record in packet["task"]["review"]["providers"]}
    assert providers == {record["path"]: record["sha256"]
                         for record in packet["task"]["review"]["providers"]}
    integration = bind(args.integration) if args.integration else None
    result = dict(original_elf_sha256=original["elf"], firmware=original["firmware"],
                  role=original["role"], mangled=original["mangled"],
                  original_address=original["address"], cpp_compiled=True,
                  mangling_namespace_checked=True, domain=DOMAIN, sources=sources,
                  repository_sources=providers, portable_ready=bool(integration))
    proof = dict(version=1, task_id=TASK, domain=DOMAIN, limitations=LIMITATIONS,
                 cpp_compiled=True, mangling_namespace_checked=True,
                 cpp_differential_passed=True, formatting_verified=True, compiled=True,
                 compiled_mangled_names_matched=True, fresh_native_execution=True,
                 native_behavior_verified=True, original_declaration_verified=True,
                 original_arm_abi_verified=False, hardware_verified=False,
                 portable_ready=bool(integration), canonical_binding_pending=not integration,
                 functions=[result], command=[sys.executable, "-B", *sys.argv],
                 formatter_version=run([FORMAT[0], "--version"]).strip(),
                 compiler_version=run([CXX[0], "--version"]).splitlines()[0],
                 unicorn_version=__import__("unicorn").__version__, sources=sources,
                 repository_sources=providers, oracle=bind(TEST / "native.py"),
                 producer_sha256=hash_file(__file__), fixture=bind(args.fixture),
                 ranges=[original], vtable=fresh["vtable"],
                 native_vtable_slots=fresh["native_vtable_slots"],
                 provider_ranges=fresh["provider_ranges"], native_cases=len(cases),
                 portable_cases=len(portable), portable_provider_cases=3,
                 symbols=definitions, object=bind(args.object), executable=bind(args.exe),
                 build=json.loads((SCRATCH / "build.json").read_text()) if not integration else None,
                 integration=integration, argv=COMMANDS)
    args.proof.parent.mkdir(parents=True, exist_ok=True)
    args.proof.write_text(json.dumps(proof, indent=2) + "\n")


if __name__ == "__main__":
    main()
