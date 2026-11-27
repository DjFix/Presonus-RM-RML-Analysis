"""Canonical bounded SPIControlGroup replay; stdlib and explicit inputs only."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def family(name):
    for token, mode in (("C1Eiii", "ctor"), ("C2Eiii", "ctor"), ("D0Ev", "d0"),
                        ("D1Ev", "d1"), ("3addE", "add"), ("7bitBangE", "bitbang"),
                        ("4openE", "open"), ("7readMsgE", "read"), ("8writeMsgE", "write"),
                        ("13enableHISpeed", "hispeed"), ("9broadcastE", "broadcast"),
                        ("5closeE", "close"), ("4sortE", "sort"), ("6onIdle", "idle")):
        if token in name:
            return mode
    raise ValueError(name)


def require(value, detail):
    if not value:
        raise RuntimeError(detail)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--exe", type=Path, required=True)
    parser.add_argument("--object", type=Path, required=True)
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--fixtures-sha256", required=True)
    args = parser.parse_args()
    fixture_bytes = args.fixtures.read_bytes()
    require(hashlib.sha256(fixture_bytes).hexdigest() == args.fixtures_sha256,
            "Immutable native fixture hash differs")
    fixture = json.loads(fixture_bytes)
    require(fixture["version"] == 1, "Unsupported fixture")
    symbols = subprocess.check_output(["/usr/bin/nm", "--defined-only", str(args.object)], text=True)
    compiled_names = {line.split()[-1] for line in symbols.splitlines()}
    ordinary = [t["original"]["mangled"] for t in fixture["targets"]
                if not t["original"]["mangled"].startswith("_ZTh")]
    for name in ordinary:
        require(name in compiled_names, "Missing ordinary original symbol: " + name)
    cases = 0
    deallocations = []
    for target in fixture["targets"]:
        name = target["original"]["mangled"]
        mode = family(name)
        for case in target["cases"]:
            i = case["input"]
            argv = [str(args.exe), mode, str(i.get("n", 3)), str(i.get("fd", -1)),
                    str(i.get("dirty", 0)), str(i.get("enabled", 0)), str(i.get("count", 0)),
                    str(i.get("value", 0)), str(i.get("open_result", i.get("fd", -1))),
                    str(i.get("group", 1)), i.get("slots", "empty")]
            result = subprocess.run(argv, capture_output=True, text=True)
            require(result.returncode == 0, repr((argv, result.returncode, result.stdout, result.stderr)))
            lines = result.stdout.splitlines()
            require(bool(lines), "Replay produced no observation")
            actual = json.loads(lines[-1])
            prefix = "\n".join(lines[:-1])
            if prefix:
                require(prefix == "error opening SPI device /offline/spi", "Unexpected provider log: " + prefix)
                actual["events"].append(["debug", "error opening SPI device %s\n", "/offline/spi"])
            expected = case["expected_native"]
            keys = ["result", "descriptor", "dirty", "tx", "rx", "count", "io_assigned", "events"]
            if mode in ("ctor", "add", "d0", "d1", "close", "sort", "idle"):
                keys.remove("result")
            if mode == "ctor":
                keys = [key for key in keys if key not in ("tx", "rx")]
            if mode in ("d0", "d1"):
                keys = ["events"]
                free = actual["deallocation"]
                require(free["group_frees"] == 1, "Receiver allocation freed other than once")
                require(free["child_frees"] == (1 if i.get("slots") in ("owned", "full") else 0),
                        "Retained or rejected child ownership differs")
                require(0 <= free["sized_group_frees"] <= free["group_frees"], "Group delete count differs")
                require(0 <= free["sized_child_frees"] <= free["child_frees"], "Child delete count differs")
                if mode == "d1":
                    require(free["sized_group_frees"] == 0, "D1 receiver cleanup differs from explicit caller cleanup")
                deallocations.append({"original": name, "input": i, "actual": free})
            require({key: actual[key] for key in keys} == {key: expected[key] for key in keys},
                    repr((name, i, actual, expected)))
            cases += 1
    print(json.dumps({"native_identity_count": len(fixture["targets"]),
                      "ordinary_symbols_matched": len(ordinary), "cases_matched": cases,
                      "actual_host_thunks": sorted(name for name in compiled_names if name.startswith("_ZTh")),
                      "original_thunks_are_research_only": True,
                      "deallocation_observations": deallocations}, sort_keys=True))


if __name__ == "__main__":
    main()
