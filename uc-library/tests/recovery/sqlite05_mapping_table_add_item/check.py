"""Build and verify the owned MappingTable source port and exact ARM fixture."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess

TEST = Path("uc-library/tests/recovery/sqlite05_mapping_table_add_item")
SOURCES = [
    "uc-library/src/Presonus/MappingTableAddItem.cpp",
    "uc-library/src/Presonus/MappingTable.cpp",
    "uc-library/src/Presonus/MappingTableItem.cpp",
]
HEADER = "uc-library/include/presonus/MappingTable.hpp"
PYTHON = "uc-library/.venv/bin/python"
FORMATTER = "uc-library/.venv/bin/clang-format"
WORK = Path("temp/recovery-work/mapping-add-item-local")
FIXTURE = TEST / "fixtures.json"
WRAPS = [
    "_Znwm", "_ZdlPv", "_ZdlPvm", "strcmp",
    "_ZN4Core8Portable10AliasParamC1ERKNS0_9ParamInfoEb",
    "_ZN8Presonus12MappingTable4ItemC1EPKcPN4Core8Portable10AliasParamE",
]
TARGETS = {
    "MappingTableAddItem.o": "_ZN8Presonus12MappingTable7addItemEPKc",
    "MappingTable.o": "_ZNK8Presonus12MappingTable8findItemEPKc",
}
FLAGS = [
    "c++", "-std=c++17", "-O2", "-fno-lto", "-Ulinux", "-Wno-multichar",
    "-Iuc-library/include", "-Ithird_party/ccl-framework",
    "-ffunction-sections", "-fdata-sections",
]


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def project():
    return next(path for path in [Path.cwd(), *Path.cwd().parents]
                if (path / "temp/core-upstream/root-integration-01"
                    / "libpresonus_cs18_components.a").is_file())


def run(argv, *, cwd=None, output=False):
    argv = list(map(str, argv))
    print(json.dumps(argv), flush=True)
    path = (Path.cwd() / WORK).resolve()
    path.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "TMPDIR": str(path), "PYTHONDONTWRITEBYTECODE": "1"}
    return subprocess.run(argv, cwd=cwd, check=True, text=True, env=env,
                          stdout=subprocess.PIPE if output else None).stdout


def compile_all(work):
    work.mkdir(parents=True, exist_ok=True)
    root = project()
    build = root / "temp/core-upstream/root-integration-01"
    dns = root / "temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu"
    libraries = [build / "libpresonus_cs18_components.a",
                 *[build / "upstream-core/sdk/lib" / (name + ".a")
                   for name in ("libcorelib", "libpresonus_core_allocator",
                                "libpresonus_png", "libpresonus_zlib")],
                 build / "private-glibc29-provider/libpresonus_private_glibc29.a"]
    hashes = {str(path): sha(path) for path in libraries}
    objects = []
    for src in [*SOURCES, TEST / "Replay.cpp"]:
        obj = work / (Path(src).stem + ".o")
        run([*FLAGS, "-MMD", "-MF", obj.with_suffix(".d"), "-c", src, "-o", obj])
        objects.append(obj)
    run(["c++", *objects, "-Wl,--gc-sections", "-Wl,--start-group", *libraries,
         "-Wl,--end-group", *["-Wl,--wrap=" + name for name in WRAPS],
         "-Wl,-Map=" + str(work / "replay.map"),
         "-Wl,-rpath," + str(dns), dns / "libdns_sd.so", "-lssl", "-lcrypto",
         "-ldl", "-lm", "-pthread", "-o", work / "replay"])
    assert hashes == {str(path): sha(path) for path in libraries}
    print(json.dumps(hashes))


def incumbents(work):
    root = project()
    build = root / "temp/core-upstream/root-integration-01"
    compile_database = build / "compile_commands.json"
    table = json.loads(compile_database.read_text())
    evidence = {str(compile_database): sha(compile_database)}
    role_archive = build / "libpresonus_cs18_components.a"
    archive_hash = sha(role_archive)
    assert "MappingTable.cpp.o" in run(["ar", "t", role_archive], output=True).splitlines()
    rm_archive = build / "libpresonus_rm_components.a"
    assert "MappingTable.cpp.o" not in run(["ar", "t", rm_archive], output=True).splitlines()
    python = Path.cwd() / PYTHON

    def compile_current(template, source, name):
        row, = [row for row in table if row["file"] == str(root / template)]
        argv = shlex.split(row["command"])
        output = (work / (name + ".o")).resolve()
        argv = [item.replace(str(root / "uc-library/include"),
                             str(Path.cwd() / "uc-library/include")) for item in argv]
        argv[argv.index("-c") + 1] = str(Path(source).resolve())
        argv[argv.index("-o") + 1] = str(output)
        run([*argv, "-MMD", "-MF", output.with_suffix(".d")])
        return output

    production = [compile_current(src, src, Path(src).stem + "-canonical")
                  for src in [*SOURCES[1:],
                              "uc-library/src/Presonus/MappingTableConnect.cpp",
                              "uc-library/src/Presonus/MappingTableHardwareParameter.cpp"]]
    production.append(compile_current(SOURCES[1], SOURCES[0],
                                      "MappingTableAddItem-canonical"))
    def build_test(target, source, custom=None):
        if custom:
            driver = (work / (target + "-driver.o")).resolve()
            run([*FLAGS, "-std=c++20", "-c", custom, "-o", driver])
        else:
            driver = compile_current(source, source, target + "-driver")
        link_template = build / "CMakeFiles" / (target + ".dir") / "link.txt"
        evidence[str(link_template)] = sha(link_template)
        args = shlex.split(link_template.read_text())
        args = [arg for arg in args if not arg.startswith("-Wl,--dependency-file=")]
        source_index, = [i for i, value in enumerate(args)
                         if value.startswith("CMakeFiles/" + target + ".dir/") and value.endswith(".o")]
        args[source_index:source_index + 1] = [str(driver), *map(str, production)]
        exe = (work / (target + ("-stabilized" if custom else ""))).resolve()
        args[args.index("-o") + 1] = str(exe)
        run(args, cwd=build)
        return exe

    historical = root / "uc-library/candidates/graph-live-trial-04-mapping"
    run([python, "-B", historical / "native_oracle.py", "--verify"], cwd=root)
    for name in ("native_oracle.py", "native-boundary-fixtures.json", "scope.json"):
        evidence[str(historical / name)] = sha(historical / name)

    for target, source, argv in (
        ("MappingItemReplay", "tests/recovery/MappingItemReplay.cpp",
         ["uc-library/tests/recovery/mapping_item/check.py", "replay", "--driver", "{exe}"]),
        ("MappingStringsReplay", "tests/recovery/MappingStringsReplay.cpp",
         ["uc-library/tests/recovery/mapping_strings/check.py", "replay", "--executable", "{exe}"]),
        ("graph_trial04_mapping_tests", "tests/graph_trial04_mapping_tests.cpp",
         ["uc-library/candidates/graph-live-trial-04-mapping/check.py", "replay", "--executable", "{exe}"]),
        ("graph_trial08_mappingtable_tests", "tests/graph_trial08_mappingtable_tests.cpp",
         ["uc-library/tests/recovery/trial08/mappingtable/replay.py", "--executable", "{exe}",
          "--fixtures", "uc-library/tests/recovery/trial08/mappingtable/fixtures.json"]),
    ):
        exe = build_test(target, "uc-library/" + source)
        run([python, "-B", *[arg.replace("{exe}", str(exe)) for arg in argv]])

    driver = build_test("graph_trial08_mappingtable_tests", None,
                        "uc-library/tests/recovery/stabilized01_mapping/driver.cpp")
    run([python, "-B", "uc-library/tests/recovery/stabilized01_mapping/replay.py",
         "--driver", driver, "--fixtures", "uc-library/tests/recovery/stabilized01_mapping/fixtures.json"])

    shared = "uc-library/tests/recovery/sqlite03_mapping_table_item_setenabled"
    exe = build_test("MappingTableItemControlReplay", shared + "/Replay.cpp")
    packets = Path("temp/recovery-work/rolling-c001-20261124/packeting/sqlite-cycle02"
                   "/mapping_item_control01/packet/tasks")
    for method in ("setenabled", "setfulloff", "setimmediate"):
        task = "sqlite03_mapping_table_item_" + method
        run([python, "-B", shared + "/check.py", "replay", exe,
             "uc-library/tests/recovery/" + task + "/fixtures.json", method,
             "--packet", packets / task / "CONTEXT.json",
             "--object", work / "MappingTableItem-canonical.o"])

    assert sha(role_archive) == archive_hash
    evidence[str(role_archive)] = archive_hash
    print(json.dumps(evidence))
    print("All incumbent MappingTable/Item replays passed against the updated class")

def symbols(work):
    for name, expected in TARGETS.items():
        found = [row for row in run(["nm", "--defined-only", work / name], output=True).splitlines()
                 if row.split()[-1:] == [expected]]
        assert len(found) == 1 and found[0].split()[-2] == "T", found
        print(found[0])


def compare(exe, fixture):
    exe = exe.resolve()
    payload = json.loads(fixture.read_text())
    for case in payload["cases"]:
        inputs = case["input"]
        initial = case["initial"]
        mode = ("fail" if case["failure_boundary_only"] else
                "null" if inputs is None else "name")
        trace = []
        for event, *values in case["events"]:
            if event == "new":
                trace.append(["allocate"])
            elif event == "alias_ctor":
                trace.append(["alias"])
            elif event == "item_ctor":
                trace.append(["item", values[0]])
            elif event == "strcmp":
                trace.append(["compare", *values])
        index = case["new_position"]
        labels = case["labels_after"]
        if labels is None:
            labels = initial
        order = list(range(len(initial)))
        if index is not None:
            order.insert(index, len(initial))
        elif case["failure_boundary_only"]:
            trace.append(["allocation_failed"])
        else:
            # Native refusal leaves the temporary alias unretained, while
            # the source port destroys its RAII temporary immediately.
            trace.extend([["destroy", str(len(initial))], ["free", str(len(initial))]])
        trace.extend(["row", str(slot), label] for slot, label in zip(order, labels))
        for slot in order:
            trace.extend([["destroy", str(slot)], ["free", str(slot)]])
        args = [exe, mode, inputs or "", *initial]
        actual = [shlex.split(line) for line in run(args, output=True).splitlines()]
        if actual != trace:
            for found, expected in zip(actual, trace):
                if found != expected:
                    raise ValueError(f"{mode} at count {len(initial)}: {found!r} != {expected!r}")
            raise ValueError(f"{mode}: expected {len(trace)} events, observed {len(actual)}")
    borrowed = run([exe, "borrowed"], output=True)
    assert borrowed.splitlines() == ["borrowed_lookup_and_lifetime"]
    print(f"{len(payload['cases'])} bounded ARM/portable cases and borrowed copy/move/lifetime passed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("format", "compile", "symbols", "native", "replay", "incumbents"))
    parser.add_argument("--work", type=Path, default=WORK)
    parser.add_argument("--exe", type=Path)
    parser.add_argument("--fixture", type=Path, default=FIXTURE)
    parser.add_argument("--packet", type=Path)
    parser.add_argument("--native", dest="recheck_native", action="store_true")
    args = parser.parse_args()
    if args.mode == "format":
        run([FORMATTER, "--style=file", "--fallback-style=LLVM", "--dry-run",
             "--Werror", HEADER, *SOURCES[:2], TEST / "Replay.cpp"])
    elif args.mode == "compile":
        compile_all(args.work)
    elif args.mode == "incumbents":
        incumbents(args.work)
    elif args.mode == "symbols":
        symbols(args.work)
    else:
        if args.mode == "native" or args.recheck_native:
            context = ["--packet", args.packet] if args.packet else []
            run([PYTHON, "-B", TEST / "native.py", args.fixture, *context])
        if args.mode == "replay":
            compare(args.exe or args.work / "replay", args.fixture)


if __name__ == "__main__":
    main()
