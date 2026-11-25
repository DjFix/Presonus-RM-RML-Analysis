"""Build, inspect and compare the portable DynamicsControl class."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

from native import ROOT, TASK_PREFIX

SOURCES = ("uc-library/src/Presonus/DynamicsControl.cpp",
           "uc-library/include/presonus/DynamicsControl.hpp")
FIRST = "uc-library/tests/recovery/sqlite02_dynamicscontrol_complete_construct"
CANONICAL = Path("/home/rs/projects/opencs/ai-line-analysis")
BUILD = CANONICAL / "temp/core-upstream/root-integration-01"
SDK = BUILD / "upstream-core/sdk/lib"
DNS = CANONICAL / "temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu"
WRAPS = (
    "_ZdlPv", "_ZdlPvm", "clock_gettime",
    "_ZN4Core8Portable9Parameter11addObserverEPNS0_14IParamObserverE",
    "_ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE",
    "_ZN4Core8Portable7ControlD2Ev",
    "_ZN4Core8Portable7ControlC2ERKNS_5TRectIiEEPNS0_9ParameterE",
    "_ZN4Core8Portable7Control6onIdleEv",
    "_ZN4Core8Portable7Control12paramChangedEPNS0_9ParameterEi",
)
PARAMETER_INDEX = {"primary": 0, "threshold": 1, "ratio": 2, "expander": 3}


def command(argv, **kwargs):
    print("+", " ".join(map(str, argv)), flush=True)
    return subprocess.run(argv, cwd=ROOT, check=True, text=True, **kwargs)


def compile_replay(task, output):
    output.mkdir(parents=True, exist_ok=True)
    obj, exe = output / "DynamicsControl.o", output / "Replay"
    compiler = ["g++", "-std=c++17", "-Wno-multichar", "-fno-rtti", "-DNDEBUG",
                "-DCORE_DISABLE_NEW_OPERATOR=1",
                "-Ithird_party/ccl-framework", "-Iuc-library/include"]
    command([*compiler, "-MMD", "-MF", str(output / "DynamicsControl.d"),
             "-c", SOURCES[0], "-o", str(obj)])
    replay = output / "Replay.o"
    command([*compiler, "-MMD", "-MF", str(output / "Replay.d"), "-c",
             f"uc-library/tests/recovery/{task}/Replay.cpp", "-o", str(replay)])
    command([*compiler, str(replay), str(obj),
             *[f"-Wl,--wrap={symbol}" for symbol in WRAPS],
             *[str(SDK / library) for library in ("libcorelib.a", "libpresonus_core_allocator.a",
                                                   "libpresonus_png.a", "libpresonus_zlib.a")],
             str(DNS / "libdns_sd.so"), f"-Wl,-rpath,{DNS}", "-ldl", "-lm", "-pthread", f"-Wl,-Map,{output / 'Replay.map'}", "-o", str(exe)])


def expected(suffix, case):
    values = list(case["result"])
    trace = case["trace"]
    calls = {event[0] for event in trace}
    if suffix.endswith("construct"):
        return [*values, int("control_construct" in calls)]
    if suffix.endswith("destroy"):
        return [int(v != 0) for v in values[:2]] + [values[2], int("control_destroy" in calls)] + [
            PARAMETER_INDEX[event[1]] for event in trace if event[0] == "remove_observer"]
    if suffix == "on_idle":
        return [*values, int("control_idle" in calls)]
    if suffix == "param_changed":
        data = case["inputs"]
        removed = [PARAMETER_INDEX[event[1]] for event in trace if event[0] == "remove_observer"]
        if data["message"] == 5 and data["changed"] == "primary":
            # Pinned Control rejects kDestroyed: this source port clears its primary
            # binding through the real setParameter(nullptr), including observer removal.
            removed.append(PARAMETER_INDEX["primary"])
        return [*values, int("control_param" in calls and data["message"] != 5), *removed]
    if suffix == "draw":
        for call in trace:
            if call[0] == "draw_line":
                _, start, end, color = call
                values.extend([1, *start, *end, color])
            elif call[0] == "draw_bitmap":
                _, bitmap, point, rect = call
                values.extend([2, int(bitmap == "handle"), *point, *rect])
    if suffix == "set_attributes":
        indices = {"th": 1, "rat": 2, "exp": 3}
        looked_up = [indices[call[1]] for call in trace if call[0] == "lookup"]
        registrations = [PARAMETER_INDEX[call[1]] for call in trace if call[0] == "add_observer"]
        values.extend([len(looked_up), *looked_up, *registrations])
    return values


def replay_args(suffix, data):
    if "rect" in data:
        return data["rect"]
    if "presence" in data:
        return [data["presence"]]
    if suffix == "calculate_pivot_points":
        return [data[key] if data[key] is not None else -1
                for key in ("mode", "threshold", "ratio", "expander")] + data["size"]
    if suffix == "on_idle":
        return [data[key] for key in ("last", "now", "pending")]
    if suffix == "on_touch_input":
        return [data[key] for key in ("primary", "enabled", "event", "value")]
    if suffix == "param_changed":
        return [PARAMETER_INDEX[data["changed"]], data["message"], *data["cached"], data["pending"]]
    if suffix == "draw":
        return [-9 if data["primary"] is None else data["primary"],
                data["image"], data["handle"], data["mode"]]
    if suffix == "set_attributes":
        return [data[k] for k in ("resolver", "params", "mask", "image", "handle", "color")] + data["dimensions"]
    raise ValueError(suffix)


def main(task):
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["compile", "symbols", "replay"])
    parser.add_argument("--output", type=Path, default=ROOT / "temp/recovery-work" / task / "final-class-build")
    parser.add_argument("--exe", type=Path)
    parser.add_argument("--fixture", type=Path,
                        default=ROOT / "uc-library/tests/recovery" / task / "fixtures.json")
    args = parser.parse_args()
    if args.mode == "compile":
        compile_replay(task, args.output)
        return
    fixture = json.loads(args.fixture.read_text())
    assert fixture["task"] == task
    if args.mode == "symbols":
        original = fixture["original"]["mangled"]
        text = command(["nm", "--defined-only", str(args.output / "DynamicsControl.o")],
                       capture_output=True).stdout
        assert any(row.split()[-1] == original for row in text.splitlines() if row.split()), original
        print(original)
        return
    suffix = task.removeprefix(TASK_PREFIX)
    exe = args.exe or args.output / "Replay"
    for case in fixture["cases"]:
        data = case["inputs"]
        argv = [str(exe), suffix, *map(str, replay_args(suffix, data))]
        actual = list(map(float, command(argv, capture_output=True).stdout.split()))
        assert actual == expected(suffix, case), (data, actual, expected(suffix, case))
    print(f"Matched {len(fixture['cases'])} native cases for {task}.")


if __name__ == "__main__":
    main(Path(__file__).parent.name)
