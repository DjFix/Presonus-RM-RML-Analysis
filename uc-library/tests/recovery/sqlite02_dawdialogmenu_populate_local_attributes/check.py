"""Replay a Linux DialogMenu executable against both original ARM roles."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

from native import CASE_TASKS, packet

DIRECTORY = Path(__file__).resolve().parent.relative_to(Path.cwd())
SOURCE = Path("uc-library/src/Presonus/IDAWDialogHandler.cpp")
HEADER = Path("uc-library/include/presonus/IDAWDialogHandler.hpp")
FORMATTER = "uc-library/.venv/bin/clang-format"
PROVIDER_SDK = Path("/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01/upstream-core/sdk/lib")
PROVIDER_LIBS = [PROVIDER_SDK / f"lib{name}.a" for name in ("corelib", "presonus_core_allocator")]
COMPILER = ["c++", "-std=c++17", "-fno-rtti", "-O0", "-Iuc-library/include", "-Ithird_party/ccl-framework"]
PENDING = {
    "parse": "The original return declaration is unresolved. Void provides the portable side-effect interface.",
    "children": "Native execution establishes a normalized 0/1 result. Bool is the portable return declaration.",
    "separator": "Native execution establishes a normalized 0/1 result. Bool is the portable return declaration.",
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def version(argv):
    return subprocess.check_output(argv, text=True).splitlines()[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=CASE_TASKS)
    parser.add_argument("--compile", action="store_true")
    parser.add_argument("--symbols", action="store_true")
    parser.add_argument("--exe", type=Path)
    parser.add_argument("--object", type=Path)
    parser.add_argument("--integration", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    start = datetime.now(timezone.utc).isoformat()
    task = CASE_TASKS[args.mode]
    test = DIRECTORY.parent / task
    scratch = Path("temp/recovery-work/daw-menu-local") / task
    object_path = args.object or scratch / "DialogMenu.o"
    executable = args.exe or scratch / "Replay"
    compile_argv = [*COMPILER, "-MMD", "-MF", str(scratch / "DialogMenu.d"), "-c",
                    str(SOURCE), "-o", str(object_path)]
    link_argv = [*COMPILER, str(test / "Replay.cpp"), str(object_path),
                 *map(str, PROVIDER_LIBS), "-o", str(executable)]
    symbols_argv = ["nm", "--defined-only", str(object_path)]
    if args.compile:
        scratch.mkdir(parents=True, exist_ok=True)
        subprocess.run(compile_argv, check=True)
        subprocess.run(link_argv, check=True)
        return

    context = json.loads(packet(args.mode).read_text())
    symbols = subprocess.check_output(symbols_argv, text=True).splitlines()
    names = {line.split()[-1] for line in symbols if line.split()}
    assert all(item["original"]["mangled"] in names for item in context["originals"])
    if args.symbols:
        print(*(item["original"]["mangled"] for item in context["originals"]), sep="\n")
        return

    fixture = test / "fixtures.json"
    oracle = [sys.executable, "-B", str(DIRECTORY / "native.py"), args.mode, "--fixtures", str(fixture)]
    native_output = subprocess.check_output(oracle, text=True).strip()
    observations = json.loads(fixture.read_text())
    replay_argv = [str(executable.resolve()), args.mode]
    actual = subprocess.check_output(replay_argv, text=True).splitlines()
    roles = observations["role_observations"]
    assert len(roles) == 2 and all(actual == role["output"] for role in roles)
    formatted = list(dict.fromkeys([SOURCE, HEADER, DIRECTORY / "Replay.cpp", test / "Replay.cpp"]))
    format_argv = [FORMATTER, "--style=file", "--fallback-style=LLVM", "--dry-run", "--Werror",
                   *map(str, formatted)]
    subprocess.run(format_argv, check=True)
    domain = context["task"]["review"]["domain"] + (
        " Five local scenarios per role and five on Linux cover absent, empty, single, mixed nested, and repeated population."
    )
    limitations = [
        "ARM ran the application instructions with modeled typed attribute, allocator, libc and CCL Vector boundaries.",
        "The Linux replay links the pinned CCL provider. The source port makes no ARM layout, hardware, or binary ABI claim.",
        "Allocation failures, unbounded depth, external inputs, and mutated or expired backing attributes are outside the compared domain.",
        "Saved local parse fixtures use a typed shared empty string to preserve the distinction from a missing title.",
    ]
    uncertainty = PENDING.get(args.mode)
    if uncertainty:
        limitations.append(uncertainty)
    files = list(dict.fromkeys([*formatted, DIRECTORY / "native.py", DIRECTORY / "check.py", fixture]))
    sources = {str(file.relative_to("uc-library")): sha(file) for file in files}
    provider_paths = context["task"]["review"]["required_provider_paths"]
    repository_sources = {name: sha(name) for name in provider_paths}
    for name in provider_paths:
        assert repository_sources[name] == context["task"]["sources"][name]
    functions = [
        dict(original_elf_sha256=row["elf_sha256"], mangled=row["target"]["mangled"],
             original_address=row["target"]["address"], range_verified=True,
             native_cases=len(row["cases"]), cpp_differential_passed=True,
             cpp_compiled=True, mangling_namespace_checked=True,
             sources=sources, repository_sources=repository_sources, domain=domain,
             portable_ready=not uncertainty, original_function_verified=False,
             hardware_verified=False, **({"declaration_uncertainties": [uncertainty]} if uncertainty else {}))
        for row in roles
    ]
    proof = dict(
        version=1, task_id=task, domain=domain, limitations=limitations,
        cpp_differential_passed=True, compiled_original_mangled_names_matched=True,
        mangling_namespace_checked=True, portable_ready=not uncertainty, functions=functions,
        sources=sources, repository_sources=repository_sources,
        proposed_readiness=dict(ready=[] if uncertainty else functions,
                                pending=functions if uncertainty else []),
        native=dict(argv=oracle, output=native_output, **observations),
        replay=dict(argv=replay_argv, output=actual, portable_cases=len(actual)),
        fixture=dict(path=str(fixture), sha256=sha(fixture)),
        oracle_producer_sha256=sha(DIRECTORY / "native.py"), producer_sha256=sha(__file__),
        format=dict(argv=format_argv, version=version([FORMATTER, "--version"]),
                    sources={str(file): sha(file) for file in formatted}),
        compiler=dict(version=version([COMPILER[0], "--version"]),
                      **({} if args.object else dict(compile_argv=compile_argv, link_argv=link_argv,
                         provider_archives={str(lib): sha(lib) for lib in PROVIDER_LIBS}))),
        executable=dict(path=str(executable), sha256=sha(executable)),
        objects={str(object_path): sha(object_path)}, symbols_argv=symbols_argv,
        compiled_symbols=symbols, start_utc=start, end_utc=datetime.now(timezone.utc).isoformat(),
    )
    if args.integration:
        proof["integration"] = dict(path=str(args.integration), sha256=sha(args.integration))
    if args.out:
        args.out.write_text(json.dumps(proof, indent=2) + "\n")
    print(f"{task}: 5 Linux cases match {sum(len(row['cases']) for row in roles)} ARM cases")


if __name__ == "__main__":
    main()
