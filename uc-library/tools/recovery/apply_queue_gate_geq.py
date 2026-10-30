"""Fixed three-candidate product application; readiness admission stays separate."""
import argparse
import hashlib
import json
from pathlib import Path
import re

repo = Path.cwd().resolve()
lib = repo / "uc-library"
out = repo / "evidence/recovery/2026-10-28/queue-gate-geq-batch"
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text())
expected = {
    "uc-event-queue-lifecycle/CONTROLLED-APPLY-02.json": "0cbb0e9267b7ecd4ed8b83f8b817841a14667d31bb5b317bba305817493bf762",
    "dsp-gate-parameter-list/CONTROLLED-APPLY.json": "bc3d0785e8585dc7f45966c1475908ebb68360a40fe68bf08467aa0cb622a6ec",
    "dsp-geq-parameter-list/CONTROLLED-APPLY.json": "4d565e015cce1c0035d2a8909e13150b58010a6411bdf71893792ba022e43d73",
}

def once(text, marker, replacement):
    assert text.count(marker) == 1, marker
    return text.replace(marker, replacement, 1)

def counts(text):
    return [len(re.search(r"set\(PRESONUS_" + group + r"_SOURCES\n(.*?)\n\)", text, re.S).group(1).split())
            for group in ("common", "cs18", "rm")]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    pre = read(out / "candidate-preflight-01/validation.json")
    assert pre["passed"]
    for name, digest in {**pre["unchanged_state"], **pre["inputs"]}.items():
        assert sha(lib / name) == digest, name
    products, previous, origins, mappings = {}, {}, {}, {}
    candidate_paths = []
    for relative, digest in expected.items():
        path = lib / "candidates" / relative
        assert sha(path) == digest, relative
        mapping = mappings[relative.split("/")[0]] = read(path)
        own = path.parent
        for row in mapping["products"]:
            source = lib / row["source"] if row["source"].startswith("candidates/") else own / row["source"]
            name = row.get("target", row.get("destination"))
            target = lib / name
            assert source.resolve().is_relative_to(lib) and target.resolve().is_relative_to(lib)
            assert name not in products and not target.is_symlink()
            assert sha(source) == row["sha256"], source
            old = row.get("previous_sha256", row.get("required_destination_sha256"))
            assert not target.exists() if old is None else target.is_file() and sha(target) == old
            products[name], previous[name], origins[name] = source.read_bytes(), old, str(source.relative_to(lib))
            if source.suffix in (".cpp", ".hpp", ".h"):
                candidate_paths.append(str(source.relative_to(lib)))
    network = mappings["uc-event-queue-lifecycle"]
    gate, geq = mappings["dsp-gate-parameter-list"], mappings["dsp-geq-parameter-list"]
    partition = dict(network["production_cpp_partition"])
    for mapping in (gate, geq):
        for name in mapping["production_rm_cpp"]:
            assert name not in partition
            partition[name] = "rm"
    assert len(partition) == 5 and list(partition.values()).count("common") == 1
    groups = (lib / "cmake/ProductionSourceGroups.cmake").read_text()
    assert counts(groups) == [106, 46, 49]
    for name, group in partition.items():
        assert name not in groups
        marker = "set(PRESONUS_" + group + "_SOURCES\n"
        groups = once(groups, marker, marker + "  " + name + "\n")
    assert counts(groups) == [107, 46, 53]
    headers = [p.removeprefix("include/") for p in network["new_public_headers"] + gate["public_headers"] + geq["public_headers"]]
    assert len(headers) == len(set(headers)) == 5 and all(p not in groups for p in headers)
    groups = once(groups, "set(PRESONUS_PUBLIC_HEADERS\n", "set(PRESONUS_PUBLIC_HEADERS\n" + "".join("  " + p + "\n" for p in headers))
    cmake = (lib / "CMakeLists.txt").read_text()
    cmake = once(cmake, "set(PRESONUS_UC_PUBLIC_HEADERS\n", "set(PRESONUS_UC_PUBLIC_HEADERS\n" + "".join("  " + p + "\n" for p in headers))
    properties = []
    for name, options in network["production_compile_options"].items():
        properties.append('set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/' + name + '" APPEND PROPERTY COMPILE_OPTIONS ' + " ".join(options) + ")")
    for mapping in (gate, geq):
        names = set(mapping["production_rm_cpp"]) | set(mapping.get("existing_replaced_rm_cpp", []))
        for name in sorted(names):
            options = mapping["strict_compile_options"] + (["-fno-rtti"] if name in mapping["no_rtti_sources"] else [])
            properties.append('set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/' + name + '" APPEND PROPERTY COMPILE_OPTIONS ' + " ".join(options) + ")")
        for name, includes in mapping.get("source_private_include_requirements", {}).items():
            properties.append('set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/' + name + '" APPEND PROPERTY INCLUDE_DIRECTORIES ' + " ".join('"${CMAKE_CURRENT_SOURCE_DIR}/' + p + '"' for p in includes) + ")")
    cmake = once(cmake, "presonus_build_common_objects()", "presonus_build_common_objects()\n" + "\n".join(properties))
    tests = []
    target_names, suite_names = [], []
    for mapping, targets in ((network, network["test_targets"]), (gate, gate["tests"]), (geq, geq["tests"])):
        for target in targets:
            name = target["name"]
            assert "add_executable(" + name not in cmake and "-UNDEBUG" in target["compile_options"]
            target_names.append(name)
            tests += ["  add_executable(" + name + " " + target["source"] + ")",
                      "  target_link_libraries(" + name + " PRIVATE " + target["link"] + ")",
                      "  target_compile_options(" + name + " PRIVATE " + " ".join(target["compile_options"]) + ")"]
            if target["link_options"]:
                tests.append("  target_link_options(" + name + " PRIVATE " + " ".join(target["link_options"]) + ")")
            cases = target.get("ctests", [dict(name=name, args=target.get("arguments", []))])
            for case in cases:
                suite_names.append(case["name"])
                tests.append("  add_test(NAME " + case["name"] + " COMMAND " + name + " " + " ".join(case.get("args", case.get("arguments", []))) + ")")
    for case in gate["additional_ctests"]:
        suite_names.append(case["name"])
        tests.append("  add_test(NAME " + case["name"] + " COMMAND " + case["existing_target"] + " " + " ".join(case["args"]) + ")")
    assert len(target_names) == len(set(target_names)) == 8
    assert len(suite_names) == len(set(suite_names)) == 18
    marker = "  add_library(uc_symbol_catalog_check OBJECT tests/symbol_catalog.cpp)"
    cmake = once(cmake, marker, "\n".join(tests) + "\n" + marker)
    for name, text in (("CMakeLists.txt", cmake), ("cmake/ProductionSourceGroups.cmake", groups)):
        assert (out / "before" / name).read_bytes() == (lib / name).read_bytes()
        products[name], previous[name], origins[name] = text.encode(), sha(lib / name), "Fixed Queue/Gate/DSPGEQ root recipe"
    changed = {name for name, old in previous.items() if old and hashlib.sha256(products[name]).hexdigest() != old}
    affected = {kind: [row for row in read(lib / "validation" / filename)["functions"] if changed.intersection(row["sources"])]
                for kind, filename in (("ready", "ready-functions.json"), ("pending", "compiled-functions.json"))}
    assert (len(affected["ready"]), len(affected["pending"])) == (393, 307)
    plan = dict(products=len(products), partitions=counts(groups), cpp=206, suites=243, headers=144,
                affected_ready=393, affected_pending=307, targets=target_names, new_suites=suite_names)
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
        (out / "application.json").write_text(json.dumps({name: dict(previous_sha256=previous[name], applied_sha256=sha(lib / name), source=origins[name]) for name in products}, indent=2) + "\n")
        (out / "affected-source-closure.json").write_text(json.dumps(affected, indent=2) + "\n")
        paths = candidate_paths + [name for name in products if Path(name).suffix in (".cpp", ".hpp", ".h")]
        (lib / "validation/format-queue-gate-geq-paths.json").write_text(json.dumps(sorted(set(paths)), indent=2) + "\n")
        additions = set(products) | {"candidates/" + p for p in expected} | {str(Path(__file__).relative_to(lib)), "candidates/dsp-gate-parameter-list/validation/gate-math-original-01/vectors.txt", "validation/uc-event-queue/arm-vectors.bin"}
        (lib / "validation/integration-queue-gate-geq-additions.json").write_text(json.dumps(sorted(additions), indent=2) + "\n")
    print(json.dumps(dict(plan, apply=args.apply)))

if __name__ == "__main__":
    main()
