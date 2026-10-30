"""Independently replay this packet's full object/header supplemental checks."""
import hashlib
import json
import subprocess
from pathlib import Path

repo = Path.cwd().resolve()
lib = repo / "uc-library"
build = repo / "temp/core-upstream/root-integration-01"
prefix = repo / "temp/recovery-work/install-setup-property-linux"
own = lib / "candidates/noaa-setup-property"
proofdir = own / "validation/active-01"
out = repo / "evidence/recovery/2026-10-28/property-event-eq-batch/supplemental-audit.json"
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
read = lambda path: json.loads(path.read_text())
assert not out.exists()
objects_path = proofdir / "all15-production-objects.json"
headers_path = proofdir / "installed-public-headers.json"
objects = read(objects_path)
headers = read(headers_path)
mapping = read(own / "CONTROLLED-APPLY.json")
assert objects["passed"] and headers["passed"]
expected = set(mapping["production_cpp_partition"])
expected.update("src/Presonus/NOAA/" + name for name in ("TCardRouterCommands.cpp", "TCardRouterControl.cpp", "TCardRouterLookups.cpp"))
expected.update("src/portable/noaa/" + name for name in ("RouterLookupImage.cpp", "GambitRouterSlots.cpp", "BeastRouterSlots.cpp", "StormRouterSlots.cpp", "RogueRouterSlots.cpp", "WolverineRouterSlots.cpp"))
assert len(expected) == 15 and {row["source"] for row in objects["objects"]} == expected
commands = read(build / "compile_commands.json")
archives = {}
for name, digest in objects["archive_hashes"].items():
    assert sha(build / name) == digest == sha(prefix / "lib" / name)
    archives[name] = subprocess.check_output(["ar", "t", str(build / name)], text=True).splitlines()
for row in objects["objects"]:
    obj = (repo / row["object"]).resolve()
    assert obj.is_relative_to(build) and sha(obj) == row["sha256"]
    assert row["compiled_once"] and row["uc_rm_exact"] and row["cs18_absent"]
    compiles = [item for item in commands if Path(item["file"]).resolve() == lib / row["source"]]
    assert len(compiles) == 1
    assert "presonus_rm_objects.dir" in compiles[0].get("command", " ".join(compiles[0].get("arguments", [])))
    assert archives["libpresonus_cs18_components.a"].count(obj.name) == 0
    for name in ("libpresonus_uc.a", "libpresonus_rm_components.a"):
        assert archives[name].count(obj.name) == 1
        assert subprocess.check_output(["ar", "p", str(build / name), obj.name]) == obj.read_bytes()
expected_headers = set(mapping["new_public_headers"] + mapping["replaced_public_headers"])
assert len(expected_headers) == 5 and {row["source"] for row in headers["headers"]} == expected_headers
for row in headers["headers"]:
    installed = (repo / row["installed"]).resolve()
    assert installed == prefix / row["source"]
    assert sha(lib / row["source"]) == row["sha256"] == sha(installed)
report = dict(passed=True, objects=15, headers=5, exact_ar_p_bytes=True, compiled_once_rm=True, cs18_absent=True,
              receipt_hashes={str(path.relative_to(lib)): sha(path) for path in (objects_path, headers_path)},
              archive_hashes=objects["archive_hashes"], tool_sha256=sha(Path(__file__)))
out.write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report))
