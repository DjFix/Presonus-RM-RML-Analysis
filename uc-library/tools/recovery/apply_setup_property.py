"""Fixed guarded six-method setup-property application; no readiness admission."""
import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

repo = Path.cwd().resolve()
lib = repo / "uc-library"
out = repo / "evidence/recovery/2026-10-28/property-event-eq-batch"
own = lib / "candidates/noaa-setup-property"
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
read = lambda path: json.loads(path.read_text())

def once(text, marker, replacement):
    assert text.count(marker) == 1, marker
    return text.replace(marker, replacement, 1)

def counts(text):
    return [len(re.search(r"set\(PRESONUS_" + name + r"_SOURCES\n(.*?)\n\)", text, re.S).group(1).split()) for name in ("common", "cs18", "rm")]

parser = argparse.ArgumentParser()
parser.add_argument("--apply", action="store_true")
args = parser.parse_args()
mapping = own / "CONTROLLED-APPLY.json"
assert sha(mapping) == "f9abeaa2a1a34bb5538ba30f058537cbaedfb032ce7ec3eee3e22eadfea908c3"
control = read(mapping)
proof = read(own / "validation/candidate-01/validation.json")
assert proof["passed"]
result = read(own / "validation/candidate-01/merge-result.json")
assert (result["portable_ready_entries"], result["unique_mangled_methods"], result["compiled_declaration_pending_entries"]) == (745, 407, 692)
assert not any(result[name] for name in ("stale_previous_entries", "demoted_entries", "promoted_pending_entries"))
for name in ("CMakeLists.txt", "cmake/ProductionSourceGroups.cmake", "validation/ready-functions.json", "validation/compiled-functions.json"):
    assert (lib / name).read_bytes() == (out / "before" / name).read_bytes(), name
products, previous, origins, candidate_paths = {}, {}, {}, []
formatting = read(lib / "validation/formatting.json")
for row in control["products"]:
    source = (lib / row["source"] if row["source"].startswith("candidates/") else own / row["source"]).resolve()
    name = row.get("target", row.get("destination"))
    target = (lib / name).resolve()
    old = row.get("previous_sha256", row.get("required_destination_sha256"))
    assert source.is_relative_to(lib) and target.is_relative_to(lib)
    assert name not in products and not (lib / name).is_symlink()
    assert sha(source) == row["sha256"]
    assert not target.exists() if old is None else target.is_file() and sha(target) == old
    products[name], previous[name], origins[name] = source.read_bytes(), old, str(source.relative_to(lib))
    if source.suffix in (".cpp", ".hpp", ".h"):
        assert formatting["files"][origins[name]] == sha(source)
        candidate_paths.append(origins[name])
groups = (lib / "cmake/ProductionSourceGroups.cmake").read_text()
assert counts(groups) == [96, 45, 23]
partition = control["production_cpp_partition"]
assert len(partition) == 6 and set(partition.values()) == {"rm"}
assert all(name not in groups for name in partition)
marker = "set(PRESONUS_rm_SOURCES\n"
groups = once(groups, marker, marker + "".join("  " + name + "\n" for name in sorted(partition)))
assert counts(groups) == [96, 45, 29]
headers = [name.removeprefix("include/") for name in control["new_public_headers"]]
assert len(headers) == len(set(headers)) == 4 and all(name not in groups for name in headers)
marker = "set(PRESONUS_PUBLIC_HEADERS\n"
groups = once(groups, marker, marker + "".join("  " + name + "\n" for name in headers))
cmake = (lib / "CMakeLists.txt").read_text()
marker = "set(PRESONUS_UC_PUBLIC_HEADERS\n"
cmake = once(cmake, marker, marker + "".join("  " + name + "\n" for name in headers))
properties = ['set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/' + name + '" APPEND PROPERTY COMPILE_OPTIONS -fno-lto)' for name in sorted(partition)]
cmake = once(cmake, "presonus_build_common_objects()", "presonus_build_common_objects()\n" + "\n".join(properties))
tests = []
for target in control["test_targets"]:
    name = target["name"]
    assert "add_executable(" + name not in cmake and "-UNDEBUG" in target["compile_options"]
    tests += ["  add_executable(" + name + " " + target["source"] + ")", "  target_link_libraries(" + name + " PRIVATE " + target["link"] + ")", "  target_compile_options(" + name + " PRIVATE " + " ".join(target["compile_options"]) + ")"]
    for case in target["ctests"]:
        tests.append("  add_test(NAME " + case["name"] + " COMMAND " + name + (" " + " ".join(case["arguments"]) if case["arguments"] else "") + ")")
marker = "  add_library(uc_symbol_catalog_check OBJECT tests/symbol_catalog.cpp)"
cmake = once(cmake, marker, "\n".join(tests) + "\n" + marker)
for name, content in (("CMakeLists.txt", cmake), ("cmake/ProductionSourceGroups.cmake", groups)):
    products[name], previous[name], origins[name] = content.encode(), sha(lib / name), "Root fixed property recipe"
changed = {name for name, old in previous.items() if old is not None and hashlib.sha256(products[name]).hexdigest() != old}
affected = {kind: [row for row in read(lib / "validation" / ledger)["functions"] if changed.intersection(row["sources"])] for kind, ledger in (("ready", "ready-functions.json"), ("pending", "compiled-functions.json"))}
assert (len(affected["ready"]), len(affected["pending"])) == (6, 18)
plan = dict(products=len(products), partitions=counts(groups), production_cpp=170, suites=184, public_headers=116, affected_ready=6, affected_pending=18, scope="Setup-property only; MessageEvent/EQ remain separate candidates")
print(json.dumps(dict(plan, apply=args.apply)), flush=True)
if not args.apply:
    (out / "application-plan.json").write_text(json.dumps(plan, indent=2) + "\n")
else:
    assert not (out / "application.json").exists() and read(out / "application-plan.json") == plan
    for name, data in products.items():
        target = lib / name
        if target.exists():
            backup = out / "before" / name
            backup.parent.mkdir(parents=True, exist_ok=True)
            if backup.exists():
                assert backup.read_bytes() == target.read_bytes()
            else:
                shutil.copyfile(target, backup)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    (out / "application.json").write_text(json.dumps({name: dict(previous_sha256=previous[name], applied_sha256=sha(lib / name), source=origins[name]) for name in products}, indent=2) + "\n")
    (out / "affected-source-closure.json").write_text(json.dumps(affected, indent=2) + "\n")
    active_paths = [name for name in products if Path(name).suffix in (".cpp", ".hpp", ".h")]
    (lib / "validation/format-setup-property-paths.json").write_text(json.dumps(sorted(set(candidate_paths + active_paths)), indent=2) + "\n")
    additions = sorted(set(products) | {str(mapping.relative_to(lib)), str(Path(__file__).relative_to(lib))})
    (lib / "validation/integration-setup-property-additions.json").write_text(json.dumps(additions, indent=2) + "\n")
