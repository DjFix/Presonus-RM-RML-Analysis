"""Role-linked default constructor and exact C1/C2 checks."""
import argparse
import hashlib
import json
from pathlib import Path
import os
import subprocess

LIBRARY = Path("uc-library")
SRC = LIBRARY / "src/Presonus/MappingTableAddItem.cpp"
TESTS = LIBRARY / "tests/recovery"
SHARED = TESTS / "sqlite11_mapping_table_default_c1"
WORK = Path("temp/recovery-work/mapping-default-local")
PYTHON = LIBRARY / ".venv/bin/python"
FORMATTER = LIBRARY / ".venv/bin/clang-format"
FLAGS = ["c++", "-std=c++17", "-O2", "-fno-lto", "-Ulinux",
         "-Wno-multichar", "-Iuc-library/include", "-Ithird_party/ccl-framework",
         "-ffunction-sections", "-fdata-sections"]


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def root_project():
    return next(path for path in [Path.cwd(), *Path.cwd().parents]
                if (path / "temp/core-upstream/root-integration-01"
                    / "libpresonus_cs18_components.a").is_file())


def run(argv, output=False):
    argv = list(map(str, argv))
    print(json.dumps(argv), flush=True)
    WORK.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "TMPDIR": str(WORK.resolve()), "PYTHONDONTWRITEBYTECODE": "1"}
    return subprocess.run(argv, check=True, text=True, env=env,
                          stdout=subprocess.PIPE if output else None).stdout


def build():
    root = root_project()
    canonical = root / "temp/core-upstream/root-integration-01"
    dns = root / "temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu"
    archives = [
        canonical / "libpresonus_cs18_components.a",
        *[canonical / "upstream-core/sdk/lib" / lib for lib in
          ("libcorelib.a", "libpresonus_core_allocator.a",
           "libpresonus_png.a", "libpresonus_zlib.a")],
        canonical / "private-glibc29-provider/libpresonus_private_glibc29.a",
        dns / "libdns_sd.so",
    ]
    bindings = {str(path): sha(path) for path in archives}
    members = run(["ar", "t", archives[0]], output=True).splitlines()
    assert members.count("MappingTableAddItem.cpp.o") == 1
    rm_members = run(["ar", "t", canonical / "libpresonus_rm_components.a"],
                     output=True).splitlines()
    assert "MappingTableAddItem.cpp.o" not in rm_members
    objects = []
    for src, name in ((SRC, "production"), (SHARED / "Replay.cpp", "driver")):
        obj = WORK / (name + ".o")
        run([*FLAGS, "-MMD", "-MF", obj.with_suffix(".d"), "-c", src, "-o", obj])
        objects.append(obj)
    run(["c++", *objects, "-Wl,--gc-sections", "-Wl,--start-group",
         *archives[:-1], "-Wl,--end-group", archives[-1], "-Wl,-rpath," + str(dns),
         "-lssl", "-lcrypto", "-ldl", "-lm", "-pthread",
         "-Wl,-Map=" + str(WORK / "replay.map"), "-o", WORK / "replay"])
    link_map = (WORK / "replay.map").read_text()
    assert "libpresonus_cs18_components.a(" in link_map
    assert "libpresonus_cs18_components.a(MappingTableAddItem.cpp.o)" not in link_map
    assert bindings == {str(path): sha(path) for path in archives}
    print(json.dumps(bindings))


def symbols(variant):
    original = f"_ZN8Presonus12MappingTableC{variant[1]}Ev"
    defined = run(["nm", "--defined-only", WORK / "production.o"], output=True)
    line, = [line for line in defined.splitlines() if line.split()[-1:] == [original]]
    assert line.split()[-2] == "T"
    for obj in ("driver.o", "replay"):
        mode = "--undefined-only" if obj.endswith(".o") else "--defined-only"
        rows = run(["nm", mode, WORK / obj], output=True).splitlines()
        assert len([row for row in rows if row.split()[-1:] == [original]]) == 1
    print(line)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("format", "compile", "symbols", "replay"))
    parser.add_argument("variant", choices=("c1", "c2"))
    parser.add_argument("--packet", type=Path)
    parser.add_argument("--fixture", type=Path)
    parser.add_argument("--exe", type=Path, default=WORK / "replay")
    args = parser.parse_args()
    if args.mode == "format":
        run([FORMATTER, "--style=file", "--fallback-style=LLVM", "--dry-run",
             "--Werror", LIBRARY / "include/presonus/MappingTable.hpp",
             SRC, SHARED / "Replay.cpp"])
    elif args.mode == "compile":
        build()
    elif args.mode == "symbols":
        symbols(args.variant)
    else:
        task = "sqlite11_mapping_table_default_" + args.variant
        packet = args.packet or (Path("temp/recovery-work/sqlite-issued/packet") / task / "CONTEXT.json")
        fixture = args.fixture or (TESTS / task / "fixtures.json")
        original = json.loads(fixture.read_text())["original"]["mangled"]
        assert original == f"_ZN8Presonus12MappingTableC{args.variant[1]}Ev"
        run([PYTHON, "-B", SHARED / "native.py", packet, fixture])
        observed = run([args.exe.resolve(), args.variant], output=True)
        expected = (args.variant + " empty roster, 1024 slots, typed Item forwarding,"
                    " independent instances and injected contracts")
        assert observed.splitlines() == [expected], observed
        print(expected)


if __name__ == "__main__":
    main()
