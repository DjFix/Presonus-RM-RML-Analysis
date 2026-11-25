"""Build and check the six offline MixerApplication lifecycle deliveries."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

from native import generate

ROOT = Path(__file__).resolve().parents[4]
TEST_DIR = "uc-library/tests/recovery/sqlite05_mixer_application_c1"
CPP = "uc-library/src/Presonus/Mixer/MixerApplication.cpp"
HEADER = "uc-library/include/presonus/mixer/setup_property_applications.hpp"
REPLAY = f"{TEST_DIR}/Replay.cpp"
PYTHON = "uc-library/.venv/bin/python"
FORMAT = "uc-library/.venv/bin/clang-format"
OUTPUT = Path("temp/recovery-work/mixer-application-local")
EXE = OUTPUT / "replay"
SOURCES = (CPP, REPLAY)
WRAPS = (
    "_Znwm", "_ZdlPv", "_ZdlPvm", "_ZN8Presonus2UC11PacketQueueD2Ev",
    "_ZN8Presonus4NOAA8TCardSPI18unRegisterReceiverEPNS0_14ISysexReceiverE",
    "sigaction",
)


def run(argv):
    print(json.dumps([str(item) for item in argv]), flush=True)
    completed = subprocess.run(
        argv, cwd=ROOT, env={**os.environ, "TMPDIR": str((ROOT / OUTPUT).resolve())},
        check=True, capture_output=True, text=True,
    )
    print(completed.stdout, end="")
    print(completed.stderr, end="", file=sys.stderr)
    return completed.stdout


def compile_port():
    (ROOT / OUTPUT).mkdir(parents=True, exist_ok=True)
    active_build = Path("temp/core-upstream/root-integration-01")
    workspace_build = ROOT.parents[4] / active_build
    build = active_build if (ROOT / active_build).is_dir() else workspace_build
    archives = [
        build / "libpresonus_rm_components.a",
        *(build / f"upstream-core/sdk/lib/lib{name}.a" for name in (
            "corelib", "presonus_core_allocator", "presonus_png", "presonus_zlib",
        )),
        build / "private-glibc29-provider/libpresonus_private_glibc29.a",
    ]
    for archive in archives:
        assert (ROOT / archive).is_file(), archive
        print(f"{hashlib.sha256((ROOT / archive).read_bytes()).hexdigest()} {archive}")
    flags = (
        "-std=c++17", "-UNDEBUG", "-fno-rtti", "-ffunction-sections",
        "-fdata-sections", "-Iuc-library/include", "-Ithird_party/ccl-framework",
    )
    objects = []
    for source in SOURCES:
        obj = OUTPUT / (Path(source).stem + ".o")
        run(["/usr/bin/c++", *flags, "-MMD", "-MF", obj.with_suffix(".d"),
             "-c", source, "-o", obj])
        objects.append(obj)
    run([
        "/usr/bin/c++", *objects, "-Wl,--start-group", *archives,
        "-Wl,--end-group", "-Wl,--gc-sections",
        *(f"-Wl,--wrap={name}" for name in WRAPS),
        "-lpthread", "-ldl", "-lssl", "-lcrypto", "-lm", "-o", EXE,
    ])


def read_fixture(variant, path=None):
    default = ROOT / f"uc-library/tests/recovery/sqlite05_mixer_application_{variant}/fixtures.json"
    return json.loads((Path(path) if path else default).read_text())


def symbols(variant):
    fixture = read_fixture(variant)
    target = fixture["target"]["mangled"]
    listing = run(["readelf", "--wide", "--symbols", OUTPUT / "MixerApplication.o"])
    exact, = [line.split() for line in listing.splitlines() if line.endswith(" " + target)]
    assert exact[3] == "FUNC" and exact[4] == ("WEAK" if variant == "network_ready" else "GLOBAL"), exact
    assert exact[6].isdigit(), exact
    if variant in ("c1", "c2", "d1", "d2"):
        variants = {"c1": "C2", "c2": "C1", "d1": "D2", "d2": "D1"}
        alias = target[:-4] + variants[variant] + "Ev"
        alias_symbol, = [line.split() for line in listing.splitlines() if line.endswith(" " + alias)]
        assert alias_symbol[1:3] == exact[1:3] and alias_symbol[6] == exact[6]
        print(f"Host compiler alias checked: {alias}")
    print("Exact application symbol:", *exact)


def replay(variant, executable, fixture):
    for case in fixture["cases"]:
        mode = variant.upper() if variant != "network_ready" else variant
        argv = [executable.resolve(), mode]
        if variant.startswith("d"):
            argv.append(str(int(case["live_card"])))
        actual = [line.split() for line in run(argv).strip().splitlines()]
        if not actual and case["portable"] == [[]]:
            actual = [[]]
        assert actual == case["portable"], (actual, case["portable"])
        if variant == "d0":
            virtual_argv = [executable.resolve(), "virtual-delete", argv[-1]]
            virtual = run(virtual_argv).strip().split()
            assert virtual == ["DERIVED", *case["portable"][0]], virtual
    print(f"{variant}: {len(fixture['cases'])} matching native/portable cases")


def main():
    action, variant, *args = sys.argv[1:]
    if action == "format":
        run([FORMAT, "--version"])
        run([FORMAT, "--style=file", "--fallback-style=LLVM", "--dry-run", "--Werror",
             *SOURCES, HEADER])
    elif action == "compile":
        compile_port()
    elif action == "symbols":
        symbols(variant)
    elif action == "native":
        assert generate(variant, EXE) == read_fixture(variant)
        print(f"{variant}: checked original ELF symbol and range, reproduced native fixture")
    elif action == "replay":
        executable = Path(args[0]) if args else EXE
        fixture = read_fixture(variant, args[1] if len(args) > 1 else None)
        replay(variant, executable, fixture)
    else:
        raise ValueError(action)


if __name__ == "__main__":
    main()
