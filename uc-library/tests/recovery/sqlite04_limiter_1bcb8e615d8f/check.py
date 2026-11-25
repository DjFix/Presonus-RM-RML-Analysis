"""Build, verify and replay the shared limiter harness against exact fixtures."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

parser = argparse.ArgumentParser()
parser.add_argument("check", choices=("compile", "symbols", "replay"))
parser.add_argument("--fixture", type=Path)
parser.add_argument("--fixture-sha256")
parser.add_argument("--exe", type=Path)
parser.add_argument("--object", type=Path)
parser.add_argument("--packet", type=Path)
parser.add_argument("--scratch", type=Path)
parser.add_argument("--providers", type=Path)
args = parser.parse_args()

tools = Path(__file__).parent
source_root = Path("uc-library/src/Presonus/Dsp")

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def run(argv, **kwargs):
    return subprocess.run([str(value) for value in argv], check=True, text=True, **kwargs)

if args.check == "compile":
    provider_names = ("libcorelib.a", "libpresonus_core_allocator.a")
    provenance = json.loads((args.providers / "PROVENANCE.json").read_text())
    provider_files = [args.providers / name for name in provider_names]
    bound_providers = {Path(entry["copy"]).name: entry["sha256"] for entry in provenance["archives"]}
    assert {path.name: digest(path) for path in provider_files} == bound_providers
    print(json.dumps({str(path): digest(path) for path in provider_files}), flush=True)
    args.scratch.mkdir(parents=True, exist_ok=True)
    sources = [source_root / (name + ".cpp") for name in (
        "LimiterController", "Controller", "ControllerInterface", "ControllerSetupProcess",
        "ControllerInfo", "ParamDescriptorList", "Eq8LimiterParameterLists",
    )] + [tools / "Replay.cpp"]
    commands = []
    objects = []
    for source in sources:
        obj = args.scratch / (source.name + ".o")
        dep = obj.with_suffix(".d")
        commands.append([
            "g++", "-std=c++20", "-O2", "-fno-rtti", "-fno-fast-math", "-ffp-contract=off",
            "-fno-sized-deallocation", "-MD", "-MT", obj, "-MF", dep, "-Iuc-library/include",
            "-Ithird_party/ccl-framework", "-c", source, "-o", obj,
        ])
        objects.append(obj)
    commands.append(["g++", *objects, "-Wl,--start-group", *provider_files,
                     "-Wl,--end-group", "-pthread", "-ldl", "-o", args.scratch / "replay"])
    for command in commands:
        print(json.dumps([str(arg) for arg in command]), flush=True)
        run(command)
    print(json.dumps({str(path): digest(path) for path in (*objects, *(p.with_suffix(".d") for p in objects))}))
    sys.exit(0)

assert digest(args.fixture) == args.fixture_sha256
fixture = json.loads(args.fixture.read_text())
symbol = fixture["original"]["mangled"]
if args.check == "symbols":
    symbols = run(["nm", "--defined-only", args.object], capture_output=True).stdout.splitlines()
    row, = (line for line in symbols if line.split()[-1] == symbol)
    assert row.split()[1].upper() in ("T", "W")
    print(row)
    sys.exit(0)

if args.packet:
    native = run([sys.executable, tools / "native.py", args.packet], capture_output=True)
    assert json.loads(native.stdout) == fixture

mode = fixture["mode"]
if mode == "ctor":
    mode = "c1" if "C1" in symbol else "c2"
cases = fixture["native_cases"]
input_lines = "".join(" ".join(map(str, [len(case["inputs"]), *case["inputs"]])) + "\n"
                      for case in cases)
observed = run([args.exe, mode], input=input_lines, capture_output=True).stdout.splitlines()
assert len(observed) == len(cases)

def nan(word):
    return (word & 0x7fffffff) > 0x7f800000

for case, line in zip(cases, observed):
    count, *actual = map(int, line.split())
    assert count == len(actual) == len(case["expected"])
    # Only computed values may have provider-specific NaN sign/payload.
    nan_fields = {"get": [0], "set": [2] if case["inputs"][0] == 1 else [],
                  "update": [3, 10]}.get(mode, [])
    for i, (got, expected) in enumerate(zip(actual, case["expected"])):
        assert got == expected or (i in nan_fields and nan(got) and nan(expected)), (
            mode, case["inputs"], i, hex(got), hex(expected),
        )
print(f"{symbol}: {len(cases)} independent native/portable cases")
