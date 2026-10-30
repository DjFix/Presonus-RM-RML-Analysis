"""Fixed disjoint interpolator/programmer source application, not admission."""
import argparse
import hashlib
import json
from pathlib import Path
from apply_queue_gate_geq import once, counts

repo = Path.cwd().resolve()
lib = repo / "uc-library"
out = repo / "evidence/recovery/2026-10-28/interpolator-programmer-batch"
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text())
expected = {
    "dsp-interpolator-lifecycle-combined": "abb12062a76cb0b1ec06d4cb7d8ad163542cff8e52e87bca8fd404730234357e",
    "noaa-programmer-transport": "4cf44fff82ae4060493f11f2e60d647f7d3591247036a36663bbed1f6564a5d9",
}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    pre = read(out / "candidate-preflight-01/validation.json")
    assert pre["passed"]
    for name, digest in {**pre["unchanged_state"], **pre["inputs"]}.items():
        assert sha(lib / name) == digest, name
    products, previous, origins, maps, candidate_paths = {}, {}, {}, {}, []
    for candidate, digest in expected.items():
        own = lib / "candidates" / candidate
        path = own / "CONTROLLED-APPLY.json"
        assert sha(path) == digest
        mapping = maps[candidate] = read(path)
        for row in mapping["products"]:
            source = lib / row["source"] if row["source"].startswith("candidates/") else own / row["source"]
            name = row.get("target", row.get("destination"))
            target = lib / name
            assert source.resolve().is_relative_to(lib) and target.resolve().is_relative_to(lib)
            assert name not in products and not target.is_symlink()
            assert sha(source) == row["sha256"]
            old = row.get("previous_sha256", row.get("required_destination_sha256"))
            assert not target.exists() if old is None else target.is_file() and sha(target) == old
            products[name], previous[name], origins[name] = source.read_bytes(), old, str(source.relative_to(lib))
            if source.suffix in (".cpp", ".hpp", ".h"):
                candidate_paths.append(str(source.relative_to(lib)))
    interp, programmer = maps["dsp-interpolator-lifecycle-combined"], maps["noaa-programmer-transport"]
    assert not interp["new_production_cpp"] and not interp["new_public_headers"]
    partition = programmer["production_cpp_partition"]
    assert len(partition) == 2 and set(partition.values()) == {"rm"}
    groups = (lib / "cmake/ProductionSourceGroups.cmake").read_text()
    assert counts(groups) == [109, 46, 54]
    for name in partition:
        assert name not in groups
        groups = once(groups, "set(PRESONUS_rm_SOURCES\n", "set(PRESONUS_rm_SOURCES\n  " + name + "\n")
    assert counts(groups) == [109, 46, 56]
    headers = [p.removeprefix("include/") for p in programmer["new_public_headers"]]
    assert len(headers) == 1 and headers[0] not in groups
    groups = once(groups, "set(PRESONUS_PUBLIC_HEADERS\n", "set(PRESONUS_PUBLIC_HEADERS\n  " + headers[0] + "\n")
    cmake = (lib / "CMakeLists.txt").read_text()
    cmake = once(cmake, "set(PRESONUS_UC_PUBLIC_HEADERS\n", "set(PRESONUS_UC_PUBLIC_HEADERS\n  " + headers[0] + "\n")
    properties = ['set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/' + name + '" APPEND PROPERTY COMPILE_OPTIONS ' + " ".join(options) + ")" for name, options in programmer["production_compile_options"].items()]
    # Genuine pinned Core::Interpolator has no SDK RTTI provider. Preserve all
    # arithmetic guards used by the validated Bilinear source-port producer.
    properties.append('set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/mixer_dsp/Dsp.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-rtti -fno-lto -fno-fast-math -ffp-contract=off -frounding-math -fno-builtin)')
    cmake = once(cmake, "presonus_build_common_objects()", "presonus_build_common_objects()\n" + "\n".join(properties))
    tests, targets, suites = [], [], []
    for target in interp["tests"] + programmer["test_targets"]:
        name = target["name"]
        assert "add_executable(" + name not in cmake and "-UNDEBUG" in target["compile_options"]
        targets.append(name)
        tests += ["  add_executable(" + name + " " + target["source"] + ")",
                  "  target_link_libraries(" + name + " PRIVATE " + target["link"] + ")",
                  "  target_compile_options(" + name + " PRIVATE " + " ".join(target["compile_options"]) + ")"]
        if target["link_options"]:
            tests.append("  target_link_options(" + name + " PRIVATE " + " ".join(target["link_options"]) + ")")
        for case in target.get("ctests", [dict(name=name, args=target.get("arguments", []))]):
            suites.append(case["name"])
            tests.append("  add_test(NAME " + case["name"] + " COMMAND " + name + " " + " ".join(case.get("args", case.get("arguments", []))) + ")")
    assert len(targets) == len(set(targets)) == 3 and len(suites) == len(set(suites)) == 5
    marker = "  add_library(uc_symbol_catalog_check OBJECT tests/symbol_catalog.cpp)"
    cmake = once(cmake, marker, "\n".join(tests) + "\n" + marker)
    for name, text in (("CMakeLists.txt", cmake), ("cmake/ProductionSourceGroups.cmake", groups)):
        assert (out / "before" / name).read_bytes() == (lib / name).read_bytes()
        products[name], previous[name], origins[name] = text.encode(), sha(lib / name), "Fixed interpolator/programmer root recipe"
    changed = {n for n, old in previous.items() if old and hashlib.sha256(products[n]).hexdigest() != old}
    affected = {kind: [r for r in read(lib / "validation" / filename)["functions"] if changed.intersection(r["sources"])]
                for kind, filename in (("ready", "ready-functions.json"), ("pending", "compiled-functions.json"))}
    assert (len(affected["ready"]), len(affected["pending"])) == (114, 96)
    plan = dict(products=len(products), partitions=counts(groups), cpp=211, suites=255, headers=146,
                affected_ready=114, affected_pending=96, targets=targets, new_suites=suites)
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
                    backup.write_bytes(target.read_bytes())
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        (out / "application.json").write_text(json.dumps({n: dict(previous_sha256=previous[n], applied_sha256=sha(lib / n), source=origins[n]) for n in products}, indent=2) + "\n")
        (out / "affected-source-closure.json").write_text(json.dumps(affected, indent=2) + "\n")
        paths = candidate_paths + [n for n in products if Path(n).suffix in (".cpp", ".hpp", ".h")]
        (lib / "validation/format-interpolator-programmer-paths.json").write_text(json.dumps(sorted(set(paths)), indent=2) + "\n")
        additions = set(products) | {f"candidates/{n}/CONTROLLED-APPLY.json" for n in expected}
        additions |= {str(Path(__file__).relative_to(lib)), "tools/recovery/apply_queue_gate_geq.py",
                      "candidates/dsp-exp-bilinear-lifecycle/validation/original-01/fixtures.txt",
                      "candidates/dsp-ratio-skew-lifecycle/validation/original-01/fixtures.txt"}
        (lib / "validation/integration-interpolator-programmer-additions.json").write_text(json.dumps(sorted(additions), indent=2) + "\n")
    print(json.dumps(dict(plan, apply=args.apply)))

if __name__ == "__main__":
    main()
