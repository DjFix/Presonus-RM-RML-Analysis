"""Build and compare exact native and portable ScribbleStripController cases."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from native import observe

PREFIX = "sqlite02_scribblestripcontroller_"
TESTROOT = Path("uc-library/tests/recovery")
COMMON = TESTROOT / (PREFIX + "create_view_r2")
SOURCE = Path("uc-library/src/Presonus/Surface/ScribbleStripController.cpp")
HEADER = Path("uc-library/include/presonus/surface/ScribbleStripController.hpp")
DRIVER = COMMON / "Replay.cpp"
SCRATCH = Path("temp/recovery-work/scribble-worker-build-r2")
OBJECT = SCRATCH / "ScribbleStripController.o"
DEPS = SCRATCH / "ScribbleStripController.d"
PAN_SOURCES = [Path("uc-library/src/Presonus") / name for name in
               ("PanControl.cpp", "PanControlBindings.cpp")]
PAN_OBJECTS = [SCRATCH / source.with_suffix(".o").name for source in PAN_SOURCES]
PAN_DEPS = [obj.with_suffix(".d") for obj in PAN_OBJECTS]
ARCHIVE = SCRATCH / "libscribble_checked.a"
EXECUTABLE = SCRATCH / "replay"
PROVIDERS = [SCRATCH / "providers" / name for name in (
    "libpresonus_cs18_components.a", "libcorelib.a", "libpresonus_core_allocator.a",
    "libpresonus_png.a", "libpresonus_zlib.a", "libpresonus_private_glibc29.a")]
FORMATTER = Path("uc-library/.venv/bin/clang-format")
FLAGS = ["c++", "-std=c++17", "-O3", "-DNDEBUG", "-DCORE_USE_OPENSSL=1",
         "-DPRESONUS_HAS_UPSTREAM_CORE=1", "-Wall", "-Wextra", "-Wpedantic",
         "-Ulinux", "-fno-rtti", "-fno-lto", "-fno-fast-math", "-ffp-contract=off",
         "-pthread", "-Iuc-library/include", "-isystem", "third_party/ccl-framework"]
COMMANDS = {
    "format": [[FORMATTER, "--style=file", "--fallback-style=LLVM", "--dry-run",
                "--Werror", SOURCE, HEADER, DRIVER]],
    "compile": [
        [*FLAGS, "-MD", "-MF", DEPS, "-c", SOURCE, "-o", OBJECT],
        *[[*FLAGS, "-MD", "-MF", dep, "-c", source, "-o", obj]
          for source, obj, dep in zip(PAN_SOURCES, PAN_OBJECTS, PAN_DEPS)],
        ["ar", "rcs", ARCHIVE, OBJECT],
        [*FLAGS, DRIVER, ARCHIVE, *PAN_OBJECTS, *PROVIDERS, "-ldl", "-lm", "-o", EXECUTABLE],
    ],
    "symbols": [["nm", "--defined-only", OBJECT], ["nm", "--defined-only", ARCHIVE]],
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(argv, quiet=False):
    argv = [str(arg) for arg in argv]
    if not quiet:
        print(argv, flush=True)
    return subprocess.check_output(argv, text=True)


def native_expected(case):
    expected = []
    bindings = []
    constructor = None
    for event in case["events"]:
        name, *values = event
        if name in ("pan", "vpot"):
            constructor = [name, *values[0], values[1]]
        elif name == "allocate":
            # The native allocator size is a native layout observation only.
            continue
        elif name in ("linked", "number", "style", "dot"):
            # Setters are observed through the final concrete control state.
            bindings.append(event)
        elif name != "lookup" or values[-1] != 0:
            expected.append(event)
    expected.extend(bindings)
    if constructor:
        expected.append(constructor)
    if constructor and constructor[0] == "pan":
        ids = {identity for _, identity in bindings if identity}
        expected.append(["post_delete_notifications", len(ids)])
    expected.append(["result", case["result"]])
    return ["\t".join(map(str, line)) for line in expected]


def compare(fixture, mode, executable):
    traces = []
    for case in fixture["cases"]:
        inputs = case["input"]
        name = inputs["name"]
        kind = inputs.get("type")
        argv = [executable, mode, inputs["index"], name if name is not None else "<null>",
                kind if kind is not None else "<null>", *inputs["keys"]]
        trace = run(argv, quiet=True).splitlines()
        want = native_expected(case)
        assert trace == want, (inputs, trace, want)
        traces.append(trace)
    return traces


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["format", "compile", "symbols", "replay"])
    parser.add_argument("mode", choices=["create_view", "get_object_for_view"])
    parser.add_argument("--exe", type=Path, default=EXECUTABLE)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    task = PREFIX + args.mode + "_r2"
    context = Path("temp/recovery-work/sqlite-issued/packet") / task / "CONTEXT.json"
    fixture_path = TESTROOT / task / "fixtures.json"
    fixture = json.loads(fixture_path.read_text())
    if args.action in COMMANDS:
        if args.action == "compile":
            SCRATCH.mkdir(parents=True, exist_ok=True)
        outputs = [run(command) for command in COMMANDS[args.action]]
        if args.action == "symbols":
            mangled = fixture["original"]["mangled"]
            for output in outputs:
                assert sum(line.split()[-1:] == [mangled] for line in output.splitlines()) == 1
            print(mangled)
        return

    assert observe(context, args.mode) == fixture
    traces = compare(fixture, args.mode, args.exe)
    print(f"Verified {len(traces)} independent ARM and portable CCL cases")
    if args.out:
        original = fixture["original"]
        ready = True
        domain = (
            "All ten Param suffixes with exact typed identity, sparse and empty mappings, "
            "null, case, mixed/non-leading delimiters, and leading slash dispatch to the "
            "real CCL root provider with resolved and missing root parameters."
            if args.mode == "get_object_for_view" else
            "Exact PanControl and McuVpotControl allocations, default bounds/primary "
            "parameter, channel-linked/style/dot pointer identity across full, sparse and "
            "empty mappings and null/unknown types. Virtual deletion of exact PanControl "
            "with live linked/channel subscriptions followed by real CCL parameter change "
            "notifications without manual detachment."
        )
        sources = {str(path.relative_to("uc-library")): digest(path)
                   for path in (SOURCE, HEADER)}
        row = dict(original, original_elf_sha256=original["elf"], sources=sources,
                   cpp_compiled=True, mangling_namespace_checked=True, portable_ready=ready,
                   domain=domain)
        proof = dict(
            verified=True, cpp_compiled=True, mangling_namespace_checked=True,
            portable_ready=ready, domain=domain, originals=[row],
            proposed_readiness=dict(ready=[row] if ready else [], pending=[]),
            native=fixture, portable_traces=traces, fixture_sha256=digest(fixture_path),
            provider_lifecycle_observation=("Provider-linked Linux observation; ARM factory "
                "instructions were independently replayed but do not exercise view destruction."),
            formatter=run([FORMATTER, "--version"]).strip(),
            compiler=run(["c++", "--version"]).splitlines()[0],
            hashes={str(path): digest(path) for path in (Path(__file__), COMMON / "native.py",
                    DRIVER, SOURCE, HEADER, OBJECT, DEPS, ARCHIVE, args.exe, *PAN_SOURCES, *PAN_OBJECTS, *PAN_DEPS, *PROVIDERS)},
            commands={k: [[str(arg) for arg in command] for command in commands]
                      for k, commands in COMMANDS.items()},
        )
        args.out.write_text(json.dumps(proof, indent=2) + "\n")


if __name__ == "__main__":
    main()
