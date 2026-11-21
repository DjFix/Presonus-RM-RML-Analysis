"""Compile or replay one exact portable mixer status method."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys
import time

import native

ROOT = Path.cwd()
LIB = Path("uc-library")
TEST = LIB / "tests/recovery/cycle21_g01_r07"
SCRATCH = Path("temp/recovery-work/cycle21-g01-r07-local")
TASK = TEST.name
CMAKE = Path("/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01")
OBJECT = SCRATCH / "MixerComponentBase.o"
EXE = SCRATCH / "Replay"
HPP = LIB / "include/presonus/mixer/MixerComponentBase.hpp"
CPP = LIB / "src/Presonus/Mixer/MixerComponentBase.cpp"
PROVIDERS = [LIB / "src/Presonus/NOAA" / f for f in ("TCardHandlerProperties.cpp", "TCardStatus.cpp")]
DRIVER = TEST / "Replay.cpp"
FIXTURE = TEST / "fixtures.json"
SYMBOL = "_ZN8Presonus5Mixer18MixerComponentBase19hasDanteInputRoutesEv"
FORMAT = ["uc-library/.venv/bin/clang-format", "--style=file", "--fallback-style=LLVM",
          "--dry-run", "--Werror", HPP, CPP, DRIVER]
DOMAIN = ("Valid offline NOAA status receiver, exact stat ID/size and initialized payload, "
          "no returned mode and actual card mode values 0, 1, 2, 3 and large unsigned alternatives. "
          "Host performs one status query and restores the prior borrowed payload.")
LIMIT = ("Original ordinary return declaration is unresolved; portable bool reproduces observed "
         "0/1 behavior. Native caller executes with a controlled status getter response at the original "
         "slot boundary. Host exercises actual TCardHandler and TCard status for responding cases. "
         "Stack padding, invalid receiver state, hardware and original ARM ABI are outside this domain.")


def digest(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def utc():
    return datetime.now(timezone.utc).isoformat()


def run(argv):
    argv = list(map(str, argv))
    print(shlex.join(argv), flush=True)
    subprocess.run(argv, check=True)


def source_check():
    run(FORMAT)


def compile_local():
    SCRATCH.mkdir(parents=True, exist_ok=True)
    inventory = CMAKE / "compile_commands.json"
    link_input = CMAKE / "CMakeFiles/mixer_delegate_replay.dir/link.txt"
    entry = next(r for r in json.loads(inventory.read_text()) if r["file"].endswith(str(CPP)))
    options = shlex.split(entry["command"])
    options = [word.replace("-I" + str(CMAKE.parents[2] / "uc-library/include"),
                            "-Iuc-library/include") for word in options[:options.index("-o")]]
    options += ["-ffunction-sections", "-fdata-sections"]
    link = shlex.split(link_input.read_text())
    runtime = [CMAKE / word if word.endswith(".a") and not Path(word).is_absolute() else word
               for word in link[link.index("-lstdc++"):]]
    rpath = next(word for word in link if word.startswith("-Wl,-rpath,"))
    watched = [inventory, link_input, *(Path(word) for word in runtime if Path(word).is_file())]
    before = {str(path): digest(path) for path in watched}
    started = utc()
    objects = []
    for source in (CPP, *PROVIDERS, DRIVER):
        obj = SCRATCH / f"{source.stem}.o"
        flags = ["-fno-rtti"] if source == DRIVER else []
        run([*options, *flags, "-c", source, "-o", obj])
        objects.append(obj)
    run([options[0], "-pthread", "-Wl,--gc-sections", rpath,
         "-o", EXE, *objects, *runtime])
    after = {str(path): digest(path) for path in watched}
    if before != after:
        raise ValueError("Generated build input changed during compile/link")
    (SCRATCH / "build-inputs.json").write_text(json.dumps(
        dict(utc_started=started, utc_completed=utc(), before=before, after=after), indent=2) + "\n")


def symbol(object_path):
    matches = [line for line in subprocess.check_output(
        ["nm", "--defined-only", object_path], text=True).splitlines()
        if line.split()[-2:] == ["T", SYMBOL]]
    if len(matches) != 1:
        raise ValueError(f"Expected one defined {SYMBOL} in {object_path}")
    print(matches[0])
    return matches[0]


def native_check():
    observed = native.generate()
    if observed != json.loads(FIXTURE.read_text()):
        raise ValueError("Original ARM observations changed")
    print(len(observed["cases"]), "exact original ARM executions")
    return observed


def replay(exe, fixture):
    document = json.loads(fixture.read_text())
    outputs = []
    for case in document["cases"]:
        completed = subprocess.run([str(exe.resolve()), case["mode"]], check=True,
                                   capture_output=True, text=True)
        rows = [line for line in completed.stdout.splitlines() if line.startswith("status ")]
        mode = case["native_getter_calls"][0]["mode_written"]
        expected = f"status {case['return']} 1 {mode if mode is not None else 0}"
        if rows != [expected]:
            raise ValueError(f"{case['mode']}: {rows} != {[expected]}")
        outputs.append(expected)
    print(f"{len(outputs)} native/host status cases passed")
    return outputs


def canonical(args):
    p = argparse.ArgumentParser(description="Replay supplied canonical products")
    for flag in ("exe", "object", "integration", "out"):
        p.add_argument("--" + flag, type=Path, required=True)
    parsed = p.parse_args(args)
    start, clock = utc(), time.monotonic()
    integration_sha = digest(parsed.integration)
    sys.path.insert(0, str(ROOT / LIB / "tools/recovery"))
    import canonical_compile_bindings

    bindings = canonical_compile_bindings.bind(
        ROOT, parsed.object, str(CPP), exe_path=parsed.exe,
        required_provider_sources=[str(path) for path in PROVIDERS],
        required_archive_names=("libpresonus_rm_components.a", "libcorelib.a"),
    )
    identity = symbol(parsed.object)
    observations = native_check()
    outputs = replay(parsed.exe, FIXTURE)
    source_check()
    if digest(parsed.integration) != integration_sha:
        raise ValueError("Integration receipt changed")
    sources = dict(bindings["files"])
    for path in (CPP, HPP, DRIVER, FIXTURE, TEST / "native.py", TEST / "check.py"):
        sources[str(path)] = digest(path)
    providers = {path: sha for path, sha in sources.items()
                 if path.startswith("third_party/ccl-framework/core/")}
    if not providers:
        raise ValueError("Missing canonical CCL dependency closure")
    pending = dict(
        original_elf_sha256=observations["elf_sha256"], mangled=SYMBOL,
        cpp_compiled=True, mangling_namespace_checked=True, portable_ready=False,
        validation_domain=DOMAIN, declaration_uncertainties=[LIMIT],
        sources={path.removeprefix("uc-library/"): sha for path, sha in sources.items()
                 if path.startswith(("uc-library/src/", "uc-library/include/"))},
        repository_sources=providers, canonical_binding_pending=True,
    )
    proof = dict(
        version=1, task_id=TASK, behavior_verified=True, compiled=True, formatting_verified=True,
        mangling_verified=True, native_behavior_verified=True, canonical_binding_pending=True,
        validation_domain=DOMAIN, limitations=[LIMIT], replay_results=outputs,
        original={key: value for key, value in observations.items() if key != "cases"},
        compiled_symbols=identity, source_sha256=sources, canonical_compile_binding=bindings,
        executable_sha256=digest(parsed.exe), object_sha256=digest(parsed.object),
        integration=dict(path=str(parsed.integration), sha256=integration_sha),
        proposed_readiness=dict(ready=[], pending=[pending]), started_utc=start,
        completed_utc=utc(), duration_seconds=time.monotonic() - clock,
        formatter_version=subprocess.check_output([FORMAT[0], "--version"], text=True).strip(),
    )
    parsed.out.parent.mkdir(parents=True, exist_ok=True)
    parsed.out.write_text(json.dumps(proof, indent=2) + "\n")


if __name__ == "__main__":
    action, *args = sys.argv[1:]
    if action == "compile":
        compile_local()
    elif action == "symbols":
        symbol(OBJECT)
    elif action == "native":
        native_check()
    elif action == "replay":
        replay(EXE, FIXTURE)
    elif action == "proof":
        canonical(args)
    else:
        raise ValueError(f"Unknown check {action}")
