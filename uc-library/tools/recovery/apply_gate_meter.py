"""Fixed Gate/Meter application with frozen input and destination guards."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

repo = Path.cwd().resolve()
lib = repo / "uc-library"
phase = repo / "evidence/recovery/2026-10-28/gate-attributes-noaa-batch"
own = lib / "candidates/dsp-gate-meter-lifecycle"
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
read = lambda path: json.loads(path.read_text())

def once(text, marker, replacement):
    assert text.count(marker) == 1, marker
    return text.replace(marker, replacement, 1)

parser = argparse.ArgumentParser()
parser.add_argument("--apply", action="store_true")
args = parser.parse_args()
mapping = own / "CONTROLLED-APPLY.json"
assert sha(mapping) == "0d7ce418f3d09b2ba3725c1cc5057f9d5a9deefbd7dbfad435bcc7c8a1e05d30"
control = read(mapping)
proof = read(own / "validation/candidate-preflight-01/audit.json")
assert proof["passed"]
result = proof["actual_merger"]
assert (result["portable_ready_entries"], result["unique_mangled_methods"], result["compiled_declaration_pending_entries"]) == (735, 401, 666)
assert not any(result[name] for name in ("stale_previous_entries", "demoted_entries", "promoted_pending_entries"))
for name in ("CMakeLists.txt", "cmake/ProductionSourceGroups.cmake", "validation/ready-functions.json", "validation/compiled-functions.json"):
    assert (lib / name).read_bytes() == (phase / "before" / name).read_bytes(), name
products = {}
origins = {}
formatting = read(lib / "validation/formatting.json")
for row in control["products"]:
    source = lib / row["source"]
    target = lib / row["target"]
    assert not target.exists() and not target.is_symlink()
    assert sha(source) == row["sha256"] == formatting["files"][row["source"]]
    products[row["target"]] = source.read_bytes()
    origins[row["target"]] = row["source"]
groups = (lib / "cmake/ProductionSourceGroups.cmake").read_text()
source = control["production_common_cpp"][0]
header = control["public_headers"][0].removeprefix("include/")
assert source not in groups and header not in groups
marker = "set(PRESONUS_common_SOURCES\n"
groups = once(groups, marker, marker + "  " + source + "\n")
marker = "set(PRESONUS_PUBLIC_HEADERS\n"
groups = once(groups, marker, marker + "  " + header + "\n")
cmake = (lib / "CMakeLists.txt").read_text()
marker = "set(PRESONUS_UC_PUBLIC_HEADERS\n"
cmake = once(cmake, marker, marker + "  " + header + "\n")
options = control["strict_compile_options"] + ["-fno-rtti"]
property_line = 'set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/' + source + '" APPEND PROPERTY COMPILE_OPTIONS ' + " ".join(options) + ")"
cmake = once(cmake, "presonus_build_common_objects()", "presonus_build_common_objects()\n" + property_line)
target = control["test_target"]
assert "add_executable(" + target not in cmake
tests = ["  add_executable(" + target + " " + control["test_source"] + ")", "  target_link_libraries(" + target + " PRIVATE " + control["test_link_target"] + ")", "  target_compile_options(" + target + " PRIVATE " + " ".join(control["test_compile_options"]) + ")", "  target_link_options(" + target + " PRIVATE " + " ".join(control["test_link_options"]) + ")", "  add_test(NAME " + target + " COMMAND " + target + ")"]
marker = "  add_library(uc_symbol_catalog_check OBJECT tests/symbol_catalog.cpp)"
cmake = once(cmake, marker, "\n".join(tests) + "\n" + marker)
products["CMakeLists.txt"] = cmake.encode()
products["cmake/ProductionSourceGroups.cmake"] = groups.encode()
old_sources = {"CMakeLists.txt", "cmake/ProductionSourceGroups.cmake"}
closure = {kind: [row for row in read(lib / "validation" / name)["functions"] if old_sources.intersection(row["sources"])] for kind, name in (("ready", "ready-functions.json"), ("pending", "compiled-functions.json"))}
assert (len(closure["ready"]), len(closure["pending"])) == (6, 10)
plan = dict(products=5, production_cpp=156, partitions=dict(common=95, cs18=45, rm=16), suites=180, public_headers=109, affected_ready=6, affected_pending=10, scope="Gate/Meter only; MessageAttributes and NOAA peers remain candidate work")
print(json.dumps(dict(plan, apply=args.apply)), flush=True)
if not args.apply:
    (phase / "gate-application-plan.json").write_text(json.dumps(plan, indent=2) + "\n")
else:
    assert not (phase / "application.json").exists()
    assert read(phase / "gate-application-plan.json") == plan
    receipts = {}
    for name, data in products.items():
        target = lib / name
        previous = sha(target) if target.exists() else None
        if previous:
            backup = phase / "before" / name
            assert backup.read_bytes() == target.read_bytes()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        receipts[name] = dict(previous_sha256=previous, applied_sha256=sha(target), source=origins.get(name, "Root fixed Gate/Meter CMake recipe"))
    (phase / "application.json").write_text(json.dumps(receipts, indent=2) + "\n")
    (phase / "affected-source-closure.json").write_text(json.dumps(closure, indent=2) + "\n")
    paths = sorted(set(origins) | set(origins.values()))
    (lib / "validation/format-gate-meter-paths.json").write_text(json.dumps(paths, indent=2) + "\n")
    additions = sorted(set(products) | {str(mapping.relative_to(lib)), str(Path(__file__).relative_to(lib))})
    (lib / "validation/integration-gate-meter-additions.json").write_text(json.dumps(additions, indent=2) + "\n")
