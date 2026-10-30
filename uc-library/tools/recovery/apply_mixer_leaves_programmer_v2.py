"""Fixed Router/Decay/Feedback application; plan first, no readiness admission."""
import argparse
import hashlib
import json
from pathlib import Path
from apply_queue_gate_geq import once, counts

repo = Path.cwd().resolve()
lib = repo / "uc-library"
out = repo / "evidence/recovery/2026-10-28/mixer-leaves-programmer-batch"
read = lambda p: json.loads(p.read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
expected = {
    "mixer-next-leaf-current-260": "535001fb6625baef55f1be38100b9f43c8eeadcbc36e617f6356fe25609ae2ef",
    "noaa-programmer-safe-host-v2": "73399bb6a414ed4c68a27e06add6394a639191734adc396fee5cfc9d376eadee",
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    pre = read(out / "candidate-preflight-02/validation.json")
    assert pre["passed"]
    for name, digest in {**pre["unchanged_state"], **pre["inputs"]}.items():
        assert sha(lib / name) == digest, name
    recipe_path = lib / "candidates/noaa-programmer-safe-host-v2/CMAKE-RECIPE.json"
    assert sha(recipe_path) == "52dcc04886a7d45d45b4531a916c9f442db49c776b303c75e42fd4149825f632"
    recipe = read(recipe_path)
    products, previous, origins, maps = {}, {}, {}, {}
    for family, digest in expected.items():
        own = lib / "candidates" / family
        control = own / "CONTROLLED-APPLY.json"
        assert sha(control) == digest
        maps[family] = mapping = read(control)
        for row in mapping["products"]:
            source = lib / row["source"] if row["source"].startswith("candidates/") else own / row["source"]
            name = row.get("target", row.get("destination"))
            target = lib / name
            assert source.resolve().is_relative_to(lib) and target.resolve().is_relative_to(lib)
            assert not target.is_symlink() and name not in products and sha(source) == row["sha256"]
            old = row.get("previous_sha256", row.get("required_destination_sha256"))
            assert not target.exists() if old is None else target.is_file() and sha(target) == old
            products[name], previous[name], origins[name] = source.read_bytes(), old, str(source.relative_to(lib))
    partitions = dict(recipe["production_cpp_partition"])
    for family in ("mixer-next-leaf-current-260",):
        partitions.update({n: "common" for n in maps[family]["new_production_cpp"]})
    assert len(partitions) == 7
    groups = (lib / "cmake/ProductionSourceGroups.cmake").read_text()
    assert counts(groups) == [111, 46, 59]
    for name, group in partitions.items():
        assert name not in groups
        groups = once(groups, f"set(PRESONUS_{group}_SOURCES\n", f"set(PRESONUS_{group}_SOURCES\n  {name}\n")
    assert counts(groups) == [114, 46, 63]
    headers = [n.removeprefix("include/") for m in maps.values() for n in m["new_public_headers"]]
    assert len(headers) == len(set(headers)) == 3
    cmake = (lib / "CMakeLists.txt").read_text()
    added_headers = []
    for header in headers:
        if header in groups:
            assert header == "presonus/uc/firmware_update_listener.hpp"
            assert groups.split().count(header) == cmake.split().count(header) == 1
            assert previous["include/" + header] is not None
            continue
        added_headers.append(header)
        groups = once(groups, "set(PRESONUS_PUBLIC_HEADERS\n", f"set(PRESONUS_PUBLIC_HEADERS\n  {header}\n")
        cmake = once(cmake, "set(PRESONUS_UC_PUBLIC_HEADERS\n", f"set(PRESONUS_UC_PUBLIC_HEADERS\n  {header}\n")
    assert len(added_headers) == 3
    options = dict(recipe["production_compile_options"])
    for name in maps["mixer-next-leaf-current-260"]["new_production_cpp"]:
        options[name] = maps["mixer-next-leaf-current-260"]["production_compile_options"]
    properties = [f'set_property(SOURCE "${{CMAKE_CURRENT_SOURCE_DIR}}/{n}" APPEND PROPERTY COMPILE_OPTIONS {" ".join(flags)})' for n, flags in options.items()]
    # Insert after the broad source-property resets; never overwrite old flags.
    cmake = once(cmake, "include(CTest)", "\n".join(properties) + "\ninclude(CTest)")
    targets = recipe["test_targets"] + maps["mixer-next-leaf-current-260"]["tests"]
    tests = []
    suites = []
    for target in targets:
        name = target["name"]
        assert "add_executable(" + name not in cmake and "-UNDEBUG" in target["compile_options"]
        sources = target.get("sources", [target.get("source")])
        assert all(n in products for n in sources)
        tests += [f'  add_executable({name} {" ".join(sources)})',
                  f'  target_link_libraries({name} PRIVATE {target["link"]})',
                  f'  target_compile_options({name} PRIVATE {" ".join(target["compile_options"])})']
        if target.get("link_options"):
            tests.append(f'  target_link_options({name} PRIVATE {" ".join(target["link_options"])})')
        cases = target.get("ctests", [dict(name=target.get("ctest_name", name), args=target.get("arguments", []))])
        for case in cases:
            suites.append(case["name"])
            tests.append(f'  add_test(NAME {case["name"]} COMMAND {name} {" ".join(case.get("args", []))})')
    assert len(targets) == len(suites) == len(set(suites)) == 8
    marker = "  add_library(uc_symbol_catalog_check OBJECT tests/symbol_catalog.cpp)"
    cmake = once(cmake, marker, "\n".join(tests) + "\n" + marker)
    for name, text in (("CMakeLists.txt", cmake), ("cmake/ProductionSourceGroups.cmake", groups)):
        assert (out / "before" / name).read_bytes() == (lib / name).read_bytes()
        products[name], previous[name], origins[name] = text.encode(), sha(lib / name), "Fixed Scaled/FilterQ/GeqGain and Programmer recipe"
    changed = {n for n, old in previous.items() if old and hashlib.sha256(products[n]).hexdigest() != old}
    impact = {kind: [r for r in read(lib / "validation" / file)["functions"] if changed.intersection(r["sources"])]
              for kind, file in (("ready", "ready-functions.json"), ("pending", "compiled-functions.json"))}
    assert (len(impact["ready"]), len(impact["pending"])) == (15, 55)
    plan = dict(products=len(products), partitions=counts(groups), cpp=223, suites=268, headers=152,
                affected_ready=15, affected_pending=55, new_suites=suites, origins=origins,
                previous=previous, result_hashes={n: hashlib.sha256(b).hexdigest() for n, b in products.items()})
    if not args.apply:
        (out / "application-plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    else:
        assert not (out / "application.json").exists() and read(out / "application-plan.json") == plan
        for name, data in products.items():
            target = lib / name
            if target.exists():
                backup = out / "before" / name
                if not backup.exists():
                    backup.parent.mkdir(parents=True, exist_ok=True)
                    backup.write_bytes(target.read_bytes())
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        (out / "application.json").write_text(json.dumps(plan, indent=2) + "\n")
        (out / "affected-source-closure.json").write_text(json.dumps(impact, indent=2) + "\n")
        paths = [n for n in products if Path(n).suffix in (".cpp", ".hpp", ".h")]
        paths += [n for n in origins.values() if n.startswith("candidates/") and Path(n).suffix in (".cpp", ".hpp", ".h")]
        (lib / "validation/format-mixer-leaves-programmer-paths.json").write_text(json.dumps(sorted(set(paths)), indent=2) + "\n")
        additions = set(products) | {f"candidates/{n}/CONTROLLED-APPLY.json" for n in expected}
        additions |= {str(Path(__file__).relative_to(lib)), "tools/recovery/apply_queue_gate_geq.py",
                      "candidates/noaa-programmer-safe-host-v2/CMAKE-RECIPE.json",
                      "candidates/mixer-scaled-time-formatter/validation/native-01/fixtures.txt",
                      "candidates/mixer-filter-q-formatter/validation/native-01/fixtures.txt",
                      "candidates/mixer-geq-gain-formatter/validation/native-01/fixtures.txt"}
        (lib / "validation/integration-mixer-leaves-programmer-additions.json").write_text(json.dumps(sorted(additions), indent=2) + "\n")
    print(json.dumps({k: v for k, v in plan.items() if k not in ("origins", "previous", "result_hashes")}))


if __name__ == "__main__":
    main()
