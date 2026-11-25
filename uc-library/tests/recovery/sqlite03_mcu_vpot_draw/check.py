"""Local Linux build and differential check; also accepts the canonical CTest binary."""
import json
import os
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OUT = ROOT / "temp/recovery-work/sqlite-issued/sqlite03_mcu_vpot_draw-check"
EXE = OUT / "driver"
TEST = HERE.relative_to(ROOT)
SOURCES = ["uc-library/include/presonus/McuVpotControl.hpp",
           "uc-library/src/Presonus/McuVpotControl.cpp", str(TEST / "Replay.cpp")]
SYMBOL = "_ZN8Presonus14McuVpotControl4drawERKN4Core8Portable9DrawEventE"
VENV = "uc-library/.venv/bin/"
FORMATTING = [VENV + "clang-format", "--style=file", "--fallback-style=LLVM",
              "--dry-run", "--Werror", *SOURCES]


def compile_command():
    canonical = (ROOT / "uc-library/.venv").resolve().parents[1]
    lib = canonical / "temp/core-upstream/root-integration-01/upstream-core/sdk/lib"
    return ["/usr/bin/c++", "-std=c++17", "-fno-rtti", "-Wno-multichar", "-DNDEBUG",
            "-ffunction-sections", "-fdata-sections", "-Iuc-library/include",
            "-Ithird_party/ccl-framework", *SOURCES[1:], str(lib / "libcorelib.a"),
            str(lib / "libpresonus_core_allocator.a"), "-Wl,--gc-sections",
            str(lib / "libpresonus_png.a"), str(lib / "libpresonus_zlib.a"), "-lpthread", "-ldl", "-o", str(EXE)]


def run(command):
    print(json.dumps(command), flush=True)
    return subprocess.run(command, cwd=ROOT, check=True,
                          env=os.environ | {"TMPDIR": str(OUT)})


def replay(exe, fixtures):
    cases = json.loads(fixtures.read_text())["cases"]
    fields = ("width", "height", "primary", "enabled", "vertical", "disabled",
              "focus", "hasStyle", "hasDot", "value", "style", "dot")
    payload = "".join(" ".join(str(case[k]) for k in fields) + "\n" for case in cases)
    print(json.dumps([str(exe)]), "with", fixtures, flush=True)
    result = subprocess.run([str(exe)], input=payload, capture_output=True,
                            text=True, check=True)
    lines = result.stdout.splitlines()
    assert len(lines) == 3 * len(cases), (len(lines), len(cases), result.stderr)

    def parse(line):
        count, *calls = line.split()
        assert int(count) == len(calls), line
        return calls

    for index, case in enumerate(cases):
        app, background, focus = map(parse, lines[index * 3:index * 3 + 3])
        expected = []
        for record in case["expected"]:
            if record == ["background"]:
                expected.extend(background)
            elif record == ["focus"]:
                expected.extend(focus)
            else:
                expected.append(":".join(map(str, record)))
        assert app == expected, (index, case, app, expected)
    print(f"{len(cases)} portable executions match original ordered draws with CCL providers")


def main():
    mode = sys.argv[1]
    if mode == "format":
        run(FORMATTING)
    elif mode == "compile":
        OUT.mkdir(parents=True, exist_ok=True)
        run(compile_command())
    elif mode == "symbols":
        command = ["/usr/bin/nm", "--defined-only", str(EXE)]
        print(json.dumps(command))
        lines = subprocess.check_output(command, text=True).splitlines()
        match, = [line for line in lines if line.endswith(" T " + SYMBOL)]
        print(match)
    elif mode == "native":
        run([VENV + "python", str(TEST / "native.py"), "--verify"])
    elif mode == "replay":
        replay(pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else EXE,
               pathlib.Path(sys.argv[3]) if len(sys.argv) > 3 else HERE / "fixtures.json")
    else:
        raise ValueError(mode)


if __name__ == "__main__":
    main()
