"""Compile and check one owned target, or replay against a CMake executable."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
import re
import time
from pathlib import Path
import shlex
import subprocess
import sys

ROOT = Path.cwd()
BUILD = Path("/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01")
SCRATCH = ROOT / "temp/recovery-work/cycle21-g01-local"
NATIVE = ROOT / "uc-library/tests/recovery/cycle21_g01_s01/native.py"
ELF = Path("/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/reconstruction10x10-20261121/"
           "packeting/wave0102-carried01/snapshot/rootfs/RML16AI_Rack_13731/home/root/mixer")
MIXER = Path("uc-library/src/Presonus/Mixer/MixerComponentBase.cpp")


def command(argv):
    print(shlex.join([str(s) for s in argv]), flush=True)
    subprocess.run(argv, check=True)


def compile_target(index, task_dir):
    scratch = SCRATCH / task_dir.name
    scratch.mkdir(parents=True, exist_ok=True)
    entries = json.loads((BUILD / "compile_commands.json").read_text())
    baseline = str(Path("/home/rs/projects/opencs/ai-line-analysis"))
    entry = next(e for e in entries if e["file"].endswith(str(MIXER)))
    flags = shlex.split(entry["command"])
    flags = [arg.replace(f"-I{baseline}/uc-library/include", "-Iuc-library/include")
             for arg in flags[:flags.index("-o")]]
    flags += ["-ffunction-sections", "-fdata-sections"]
    providers = {
        2: ["ChannelComponent", "TapeInputComponent"],
        3: ["ChannelComponent", "MasterSectionComponent"],
        4: ["ChannelComponent", "MasterSectionComponent"],
    }
    sources = [MIXER, task_dir / "Replay.cpp"]
    sources.extend(MIXER.parent / f"{provider}.cpp" for provider in providers.get(index, ()))
    # The solo replays invoke actual DelayTimer, MasterSection and channel APIs.
    # The active RM archive supplies canonical unmodified transitive providers.
    objects = []
    for source in sources:
        obj = scratch / source.with_suffix(".o").name
        replay_flags = ["-fno-rtti"] if source.name == "Replay.cpp" and index >= 3 else []
        command([*flags, *replay_flags, "-c", source, "-o", obj])
        objects.append(obj)
    link = shlex.split((BUILD / "CMakeFiles/mixer_delegate_replay.dir/link.txt").read_text())
    runtime = [BUILD / arg if arg.endswith(".a") and not Path(arg).is_absolute() else arg
               for arg in link[link.index("-lstdc++"):]]
    rpath = next(arg for arg in link if arg.startswith("-Wl,-rpath,"))
    command([flags[0], "-pthread", "-Wl,--gc-sections", rpath, "-o", scratch / "Replay",
             *objects, *runtime])


def exact_symbol(mangled, obj):
    output = subprocess.check_output(["nm", "--defined-only", obj], text=True)
    match = [line for line in output.splitlines() if line.split()[-1:] == [mangled]]
    if len(match) != 1 or match[0].split()[1] != "T":
        raise ValueError(f"Expected unique global text definition for {mangled}")
    return match[0]


def symbols(mangled, task_dir):
    print(exact_symbol(mangled, SCRATCH / task_dir.name / "MixerComponentBase.o"))


def replay(executable, fixture):
    data = json.loads(fixture.read_text())
    for case in data["cases"]:
        result = subprocess.run([executable, case["sequence"], case["option"]],
                                check=True, capture_output=True, text=True)
        actual = result.stdout.splitlines()
        if actual != case["events"]:
            raise ValueError(f"{case['sequence']!r}/{case['option']!r}: {actual} != {case['events']}")
    print(f"Matched {len(data['cases'])} original ARM boundary fixture cases")
    return data


def native(index, fixture):
    observed = subprocess.check_output([sys.executable, NATIVE, str(index), ELF], text=True)
    if json.loads(observed) != json.loads(fixture.read_text()):
        raise ValueError("Original ARM observation did not reproduce")
    print(f"Reproduced {len(json.loads(observed)['cases'])} exact ARM executions")
    return json.loads(observed)


def digest(path):
    sha = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            sha.update(chunk)
    return sha.hexdigest()


def canonical_proof(args):
    parser = argparse.ArgumentParser(description="Check supplied canonical mixer products")
    parser.add_argument("--task", required=True)
    for option in ("exe", "object", "integration", "out"):
        parser.add_argument("--" + option, required=True, type=Path)
    parsed = parser.parse_args(args)
    if not re.fullmatch(r"cycle21_g01_s0[1-5]", parsed.task):
        parser.error("unknown sealed task")
    index = int(parsed.task[-1])
    started = datetime.now(timezone.utc).isoformat()
    clock = time.monotonic()
    task_dir = Path("uc-library/tests/recovery") / parsed.task
    fixture = task_dir / "fixtures.json"
    handoff_path = Path("uc-library/candidates") / parsed.task / "HANDOFF.json"
    handoff = json.loads(handoff_path.read_text())
    identity, = handoff["originals"]
    if handoff["task_id"] != parsed.task:
        raise ValueError("Handoff task does not match canonical proof task")
    if digest(fixture) != handoff["build_integration"]["fixture_sha256"]:
        raise ValueError("Fixture differs from sealed handoff")
    integration_hash = digest(parsed.integration)
    integration = json.loads(parsed.integration.read_text())
    if not isinstance(integration, dict) or not integration:
        raise ValueError("Integration receipt must be a nonempty JSON object")
    sys.path.insert(0, str(ROOT / "uc-library/tools/recovery"))
    import canonical_compile_bindings as canonical

    providers = {
        1: ["MixerComponentBaseDelegate.hpp"],
        2: ["ChannelComponent.cpp", "TapeInputComponent.cpp"],
        3: ["ChannelComponent.cpp", "MasterSectionComponent.cpp"],
        4: ["ChannelComponent.cpp", "MasterSectionComponent.cpp"],
    }
    paths = [
        "uc-library/include/presonus/mixer/" + name if name.endswith(".hpp")
        else "uc-library/src/Presonus/Mixer/" + name
        for name in providers.get(index, ())
    ]
    binding = canonical.bind(
        ROOT, parsed.object, str(MIXER), exe_path=parsed.exe,
        required_provider_sources=paths,
        required_archive_names=("libpresonus_rm_components.a", "libcorelib.a"),
    )
    symbol = exact_symbol(identity["mangled"], parsed.object)
    observations = native(index, fixture)
    if any(observations[key] != identity[key] for key in ("elf_sha256", "address", "size", "section")):
        raise ValueError("Original range identity differs from sealed handoff")
    replay(parsed.exe.resolve(), fixture)
    header = Path("uc-library/include/presonus/mixer/MixerComponentBase.hpp")
    formatter = "uc-library/.venv/bin/clang-format"
    command([formatter, "--style=file", "--fallback-style=LLVM", "--dry-run", "--Werror",
             header, MIXER, task_dir / "Replay.cpp"])
    sources = dict(binding["files"])
    sources.update({str(path): digest(path) for path in (MIXER, header, task_dir / "Replay.cpp",
                                                        fixture, NATIVE.relative_to(ROOT),
                                                        Path(__file__).resolve().relative_to(ROOT))})
    core_implementations = {
        1: [],
        2: ["corecomponent.cpp"],
        3: ["coreparams.cpp", "corecomponent.cpp"],
        4: ["coreparams.cpp", "corecomponent.cpp"],
        5: ["corecomponent.cpp", "coreparams.cpp", "corestorage.h"],
    }
    for name in core_implementations[index]:
        path = "third_party/ccl-framework/core/portable/" + name
        sources[path] = digest(path)
    if digest(parsed.integration) != integration_hash:
        raise ValueError("Integration receipt changed during proof")
    domain = handoff["validation_domain"]
    limitations = [handoff["limitations"]]
    pending = {
        "original_elf_sha256": identity["elf_sha256"], "mangled": identity["mangled"],
        "sources": {key.removeprefix("uc-library/"): value for key, value in sources.items()
                    if key.startswith(("uc-library/src/", "uc-library/include/"))},
        "repository_sources": {key: value for key, value in sources.items()
                               if key.startswith("third_party/ccl-framework/core/")},
        "cpp_compiled": True, "mangling_namespace_checked": True,
        "portable_ready": False, "domain": domain,
        "declaration_uncertainties": limitations, "canonical_binding_pending": True,
    }
    if not pending["repository_sources"]:
        raise ValueError("Canonical runtime binding omitted all pinned Core dependencies")
    proof = {
        "version": 1, "task_id": parsed.task, "compiled": True,
        "formatting_verified": True, "mangling_verified": True, "behavior_verified": True,
        "native_behavior_verified": True, "canonical_binding_pending": True,
        "original_declaration_verified": False, "original_arm_abi_verified": False,
        "hardware_verified": False, "validation_domain": domain, "limitations": limitations,
        "ranges": [{**identity, "file_offset": observations["file_offset"],
                    "range_sha256": observations["range_sha256"]}],
        "elf_sha256": identity["elf_sha256"], "source_sha256": sources,
        "compiled_symbols": symbol, "object_sha256": digest(parsed.object),
        "executable_sha256": digest(parsed.exe),
        "formatter_version": subprocess.check_output([formatter, "--version"], text=True).strip(),
        "proposed_readiness": {"ready": [], "pending": [pending]},
        "integration": {"path": str(parsed.integration), "sha256": integration_hash},
        "canonical_compile_binding": binding,
        "canonical_producer_helper": {
            "path": "uc-library/tools/recovery/canonical_compile_bindings.py",
            "sha256": digest(canonical.__file__),
        },
        "fresh_native_execution": {
            "elf_sha256": identity["elf_sha256"], "case_count": len(observations["cases"]),
            "observations_sha256": digest(fixture), "producer_sha256": digest(NATIVE),
        },
        "thread_id": os.environ.get("CODEX_THREAD_ID"),
        "environment_session_id": os.environ.get("CODEX_SESSION_ID"),
        "started_utc": started, "completed_utc": datetime.now(timezone.utc).isoformat(),
        "duration_seconds": time.monotonic() - clock, "argv": sys.argv,
    }
    parsed.out.parent.mkdir(parents=True, exist_ok=True)
    parsed.out.write_text(json.dumps(proof, indent=2) + "\n")


def main():
    check, *args = sys.argv[1:]
    if check == "compile":
        compile_target(int(args[0]), Path(args[1]))
    elif check == "symbols":
        symbols(args[0], Path(args[1]))
    elif check == "replay":
        replay(*(Path(arg).resolve() for arg in args))
    elif check == "native":
        native(int(args[0]), Path(args[1]))
    elif check == "proof":
        canonical_proof(args)
    else:
        raise ValueError(f"Unknown check {check}")


if __name__ == "__main__":
    main()
