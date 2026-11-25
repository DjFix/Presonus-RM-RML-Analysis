"""Compare portable executions with original ARM observations."""
import json
from pathlib import Path
import subprocess
import sys


def portable(executable, fixture):
    data = json.loads(Path(fixture).read_bytes())
    calls = 0
    for observation in data["observations"]:
        for case in observation["cases"]:
            argument = case["argument"]
            argv = [executable, data["mode"]]
            if argument is not None:
                argv.append(str(argument))
            actual = int(subprocess.check_output(argv, text=True))
            assert actual == case["result"], (argv, actual, case["result"])
            calls += 1
    print(f"{calls} portable comparisons to original ARM observations")


def native(producer, packet, fixture):
    actual = subprocess.check_output([sys.executable, producer, packet])
    assert json.loads(actual) == json.loads(Path(fixture).read_bytes())
    print("Both original ARM roles matched the recorded native fixture")


def symbols(mangled, *files):
    for path in files:
        output = subprocess.check_output(["nm", "--defined-only", path], text=True)
        assert any(line.split()[-1] == mangled for line in output.splitlines() if line.strip())
    print(mangled)


if __name__ == "__main__":
    mode, *args = sys.argv[1:]
    {"native": native, "portable": portable, "symbols": symbols}[mode](*args)
