"""Build the GateController source and compare native fixtures in Linux."""
import argparse
import hashlib
import json
import os
import re
import shlex
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
PROD = [
    Path("uc-library/include/presonus/dsp/GateController.hpp"),
    Path("uc-library/src/Presonus/Dsp/GateController.cpp"),
]
REPLAY = Path("uc-library/tests/recovery") / HERE.name / "Replay.cpp"
PREREQUISITES = [
    "uc-library/src/Presonus/Dsp/Controller.cpp",
    "uc-library/src/Presonus/Dsp/ControllerInterface.cpp",
    "uc-library/src/Presonus/Dsp/ControllerInfo.cpp",
    "uc-library/src/Presonus/Dsp/ControllerSetupProcess.cpp",
    "uc-library/src/Presonus/Dsp/ParamDescriptorList.cpp",
    "uc-library/src/Presonus/Dsp/GateParameterList.cpp",
    "uc-library/src/Presonus/Dsp/GateSourceProviders.cpp",
    "uc-library/src/Presonus/Dsp/CompressorSourceProviders.cpp",
    "uc-library/src/Presonus/Dsp/EqSourceProviders.cpp",
    "uc-library/src/DSP/BiquadCalcConstructor.cpp",
    "uc-library/src/DSP/BiquadMethods.cpp",
    "uc-library/src/DSP/BiquadIncremental.cpp",
]
UNSIZED = "-fno-sized-deallocation"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(args, **kwargs):
    args = list(map(str, args))
    print(json.dumps(args), flush=True)
    return subprocess.check_output(args, text=True, **kwargs)


LIBRARIES = (
    "libpresonus_rm_components.a",
    "libcorelib.a",
    "libpresonus_core_allocator.a",
    "libpresonus_private_glibc29.a",
)


def verify_provider(manifest, expected_hash):
    assert sha(manifest) == expected_hash, manifest
    prefix = manifest.parent
    provider = json.loads(manifest.read_bytes())
    assert provider["version"] == 1
    assert all(f"lib/{name}" in provider["files"] for name in LIBRARIES)
    for name, digest in provider["files"].items():
        path = Path(name)
        assert not path.is_absolute() and ".." not in path.parts
        assert sha(prefix / path) == digest, path
    return prefix


def compile_replay(scratch, executable, manifest, manifest_hash):
    prefix = verify_provider(manifest, manifest_hash)
    flags = [
        "-std=c++20", "-O3", "-Wall", "-Wextra", "-Wpedantic", "-Ulinux",
        "-DCORE_USE_OPENSSL=1", "-DPRESONUS_HAS_UPSTREAM_CORE=1", "-pthread",
        "-fno-fast-math", "-ffp-contract=off",
        "-Iuc-library/include", "-Iuc-library/src/mixer_dsp", "-isystem", prefix / "include/presonus-core-5",
    ]
    env = {**os.environ, "TMPDIR": str(scratch.resolve())}
    objects = []
    units = []
    for path in [PROD[1], REPLAY, *PREREQUISITES]:
        path = Path(path)
        obj = scratch / f"{path.stem}.o"
        options = [UNSIZED] if path == PROD[1] else []
        if path.stem in {"EqSourceProviders", "CompressorSourceProviders", "ParamDescriptorList"}:
            options += ["-fno-rtti"]
        if path.stem in {"EqSourceProviders", "GateParameterList", "ParamDescriptorList",
                         "BiquadMethods", "BiquadIncremental"}:
            options += ["-fno-lto", "-frounding-math", "-fno-builtin"]
        depfile = obj.with_suffix(".d")
        argv = list(map(str, ["/usr/bin/c++", *flags, *options, "-MD", "-MF",
                             depfile, "-MT", obj, "-c", path, "-o", obj]))
        run(argv, env=env)
        target, _, dependencies = depfile.read_text().replace("\\\n", " ").partition(":")
        assert shlex.split(target) == [str(obj)], depfile
        paths = shlex.split(dependencies)
        assert str(path) in paths, (path, paths)
        units.append({
            "source": str(path), "argv": argv,
            "object": {"path": str(obj), "sha256": sha(obj)},
            "depfile": {"path": str(depfile), "sha256": sha(depfile)},
            "dependencies": {name: sha(name) for name in paths},
        })
        objects.append(obj)
    libraries = [prefix / "lib" / name for name in LIBRARIES]
    link_map = scratch / "replay.map"
    link = list(map(str, [
        "/usr/bin/c++", *flags, "-Wl,--wrap=_ZdlPv", "-Wl,--wrap=_ZdlPvm",
        f"-Wl,-Map,{link_map}", *objects, *libraries, "-lssl", "-lcrypto", "-lz", "-ldl",
        "-o", executable,
    ]))
    run(link, env=env)
    verify_provider(manifest, manifest_hash)
    for unit in units:
        assert all(sha(path) == expected for path, expected in unit["dependencies"].items())
    receipt = {
        "version": 1, "provider_manifest": str(manifest), "provider_manifest_sha256": manifest_hash,
        "units": units, "archives": {str(p): sha(p) for p in libraries},
        "link_argv": link, "link_map": {"path": str(link_map), "sha256": sha(link_map)},
        "executable": {"path": str(executable), "sha256": sha(executable)},
    }
    (scratch / "compile-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")



def replay(executable, data):
    mode = data["mode"]
    cases = data["cases"]

    def execute(group):
        lines = []
        for case in group:
            values = case["input"]
            lines.append(f"{mode} {len(values)} " + " ".join(map(str, values)) + "\n")
        result = run([executable], input="".join(lines))
        observed = [list(map(int, line.split())) for line in result.splitlines()]
        assert len(observed) == len(group)
        for case, actual in zip(group, observed):
            assert case["expected"] == actual, (mode, case["input"], case["expected"], actual)

    if mode in ("C1", "C2"):
        # A separate process gives every non-warm case a fresh singleton.
        for case in cases:
            execute([case])
    else:
        execute(cases)
    print(json.dumps({"passed": True, "mode": mode, "cases": len(cases),
                      "executable_sha256": sha(executable)}))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("gate", choices=("format", "compile", "symbols", "replay"))
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--scratch", type=Path)
    parser.add_argument("--executable", type=Path)
    parser.add_argument("--provider-manifest", type=Path)
    parser.add_argument("--provider-manifest-sha256")
    args = parser.parse_args()
    data = json.loads(args.fixtures.read_bytes())
    assert data["producer_sha256"] == sha(HERE / "native.py")
    scratch = args.scratch
    executable = args.executable or (scratch / "replay" if scratch else None)
    if args.gate == "format":
        fmt = "uc-library/.venv/bin/clang-format"
        print(run([fmt, "--version"]), end="")
        run([fmt, "--style=file", "--fallback-style=LLVM", "--dry-run", "--Werror",
             *PROD, REPLAY])
    elif args.gate == "compile":
        if not args.provider_manifest or not args.provider_manifest_sha256:
            parser.error("compile requires an immutable provider manifest and its SHA-256")
        scratch.mkdir(parents=True, exist_ok=True)
        compile_replay(scratch, executable, args.provider_manifest, args.provider_manifest_sha256)
    elif args.gate == "symbols":
        obj = scratch / "GateController.o"
        mangled = data["range"]["mangled"]
        for path in (obj, executable):
            text = run(["/usr/bin/nm", "--defined-only", path])
            found = [line for line in text.splitlines() if line.split()[-1:] == [mangled]]
            assert len(found) == 1, (mangled, found)
            print(found[0])
        if data["mode"] == "D0":
            text = run(["/usr/bin/objdump", "-dr", obj])
            d0 = text.split(f"<{mangled}>:", 1)[1].split("\n\n", 1)[0]
            assert re.search(r"R_X86_64_PLT32\s+_ZdlPv-", d0), d0
            assert "_ZN8Presonus3Dsp10ControllerD2Ev" in d0, d0
    else:
        replay(executable, data)


if __name__ == "__main__":
    main()
