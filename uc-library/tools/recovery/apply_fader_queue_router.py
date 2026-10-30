"""Fixed guarded three-candidate application; no readiness admission."""
import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

REPO = Path.cwd().resolve()
LIB = REPO / "uc-library"
OUT = REPO / "evidence/recovery/2026-10-28/fader-queue-router-batch"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def once(text, needle, replacement):
    assert text.count(needle) == 1, needle
    return text.replace(needle, replacement, 1)


def counts(text):
    return [len(re.search(r"set\(PRESONUS_" + name + r"_SOURCES\n(.*?)\n\)", text, re.S).group(1).split()) for name in ("common", "cs18", "rm")]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    pre = read(OUT / "candidate-preflight-01/validation.json")
    assert pre["passed"]
    for name, digest in {**pre["unchanged_state"], **pre["inputs"]}.items():
        assert sha(LIB / name) == digest, name
    expected = {"dsp-fader-curve": "b74d8f682304ac6543954e32f87f6ffcb4af6221c98eb962fd77dfb0bfdb95c0", "dice-packet-queue-continuation": "b18a173d041023d27abde0612d0ab476fff21d55734fa573266f6293e420b4ad", "noaa-route-commands": "1fa42fe10f6d1707c5afd56f31515f4c18dd4f6bde9520c45de8781b5c66bb83"}
    maps = {}
    products, previous, origins = {}, {}, {}
    for candidate, digest in expected.items():
        own = LIB / "candidates" / candidate
        path = own / "CONTROLLED-APPLY.json"
        assert sha(path) == digest
        mapping = read(path)
        maps[candidate] = mapping
        rows = mapping["products"] + (mapping["fixtures"] if candidate == "dsp-fader-curve" else [])
        for row in rows:
            source = (LIB / row["source"] if row["source"].startswith("candidates/") else own / row["source"]).resolve()
            name = row.get("target", row.get("destination"))
            target = (LIB / name).resolve()
            old = row.get("previous_sha256", row.get("required_destination_sha256"))
            assert source.is_relative_to(LIB) and target.is_relative_to(LIB)
            assert name not in products and not (LIB / name).is_symlink()
            assert sha(source) == row["sha256"]
            assert not target.exists() if old is None else target.is_file() and sha(target) == old
            products[name] = source.read_bytes()
            previous[name] = old
            origins[name] = str(source.relative_to(LIB))
    fader, queue, router = (maps[name] for name in expected)
    partition = {name: "common" for name in fader["production_common_cpp"]}
    partition.update({name: queue["production_partition"] for name in queue["production_cpp"]})
    partition.update(router["production_cpp_partition"])
    assert len(partition) == 4
    groups = (LIB / "cmake/ProductionSourceGroups.cmake").read_text()
    assert counts(groups) == [93, 45, 11]
    for group in ("common", "cs18", "rm"):
        names = sorted(name for name, selected in partition.items() if selected == group)
        assert all(name not in groups for name in names)
        if names:
            marker = "set(PRESONUS_" + group + "_SOURCES\n"
            groups = once(groups, marker, marker + "".join("  " + name + "\n" for name in names))
    assert counts(groups) == [94, 45, 14]
    assert groups.count(fader["existing_shared_math_cpp"]) == 1
    headers = [name.removeprefix("include/") for name in fader["public_headers"] + router["new_public_headers"]]
    assert len(headers) == len(set(headers)) == 2 and not queue["public_headers"]
    marker = "set(PRESONUS_PUBLIC_HEADERS\n"
    groups = once(groups, marker, marker + "".join("  " + name + "\n" for name in headers))
    cmake = (LIB / "CMakeLists.txt").read_text()
    marker = "set(PRESONUS_UC_PUBLIC_HEADERS\n"
    cmake = once(cmake, marker, marker + "".join("  " + name + "\n" for name in headers))
    properties = []
    for name in sorted(partition):
        options = list(fader["strict_compile_options"]) if name in fader["production_common_cpp"] else ["-fno-lto"]
        if name in fader["no_rtti_sources"]:
            options.append("-fno-rtti")
        properties.append('set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/' + name + '" APPEND PROPERTY COMPILE_OPTIONS ' + " ".join(options) + ")")
    for name, directories in fader["source_private_include_directories"].items():
        assert name in fader["production_common_cpp"] and directories == ["src/mixer_dsp"]
        properties.append('set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/' + name + '" APPEND PROPERTY INCLUDE_DIRECTORIES "${CMAKE_CURRENT_SOURCE_DIR}/src/mixer_dsp")')
    cmake = once(cmake, "presonus_build_common_objects()", "presonus_build_common_objects()\n" + "\n".join(properties))
    tests = []
    for target in fader["test_targets"] + router["test_targets"]:
        name = target["name"]
        assert "add_executable(" + name not in cmake
        tests += ["  add_executable(" + name + " " + target["source"] + ")", "  target_link_libraries(" + name + " PRIVATE " + target["link"] + ")", "  target_compile_options(" + name + " PRIVATE " + " ".join(target["compile_options"]) + ")"]
        if target.get("link_options"):
            tests.append("  target_link_options(" + name + " PRIVATE " + " ".join(target["link_options"]) + ")")
        for case in target.get("ctests", [target.get("ctest")]):
            assert case
            if case.get("runner"):
                tests.append("  add_test(NAME " + case["name"] + " COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/" + case["runner"] + " --executable $<TARGET_FILE:" + name + "> --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/" + case["fixtures"] + " --expected ${CMAKE_CURRENT_SOURCE_DIR}/" + case["expected"] + " --cases " + str(case["cases"]) + ")")
            else:
                tests.append("  add_test(NAME " + case["name"] + " COMMAND " + name + (" " + " ".join(case["arguments"]) if case.get("arguments") else "") + ")")
    queue_block = LIB / "candidates/dice-packet-queue-continuation" / queue["test_block"]
    assert sha(queue_block) == queue["test_block_sha256"]
    test_text = "\n".join(tests) + "\n" + queue_block.read_text()
    marker = "  add_library(uc_symbol_catalog_check OBJECT tests/symbol_catalog.cpp)"
    cmake = once(cmake, marker, test_text + marker)
    for name, content in (("CMakeLists.txt", cmake), ("cmake/ProductionSourceGroups.cmake", groups)):
        assert (OUT / "before" / name).read_bytes() == (LIB / name).read_bytes()
        products[name] = content.encode()
        previous[name] = sha(LIB / name)
        origins[name] = "Root-reviewed three-candidate recipe with exact partitions/private includes/test wrappers"
    changed = {name for name, digest in previous.items() if digest is not None and hashlib.sha256(products[name]).hexdigest() != digest}
    affected = {kind: [row for row in read(LIB / "validation" / ledger)["functions"] if changed.intersection(row["sources"])] for kind, ledger in (("ready", "ready-functions.json"), ("pending", "compiled-functions.json"))}
    assert (len(affected["ready"]), len(affected["pending"])) == (8, 10)
    plan = {"apply": args.apply, "products": len(products), "partitions": counts(groups), "production_cpp": 153, "suites": 175, "public_headers": 108, "affected_ready": 8, "affected_pending": 10}
    print(json.dumps(plan), flush=True)
    if not args.apply:
        (OUT / "application-plan.json").write_text(json.dumps(plan, indent=2) + "\n")
        return
    assert not (OUT / "application.json").exists()
    assert read(OUT / "application-plan.json")["products"] == len(products)
    for name, data in products.items():
        target = LIB / name
        if target.exists():
            backup = OUT / "before" / name
            backup.parent.mkdir(parents=True, exist_ok=True)
            if backup.exists():
                assert backup.read_bytes() == target.read_bytes()
            else:
                shutil.copyfile(target, backup)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    (OUT / "application.json").write_text(json.dumps({"products": {name: {"previous_sha256": previous[name], "applied_sha256": sha(LIB / name), "source": origins[name]} for name in products}}, indent=2) + "\n")
    (OUT / "affected-source-closure.json").write_text(json.dumps(affected, indent=2) + "\n")
    candidate_paths = read(OUT / "candidate-format-paths-01.json") + read(OUT / "candidate-queue-format-paths.json")
    active_paths = [name for name in products if Path(name).suffix in (".cpp", ".hpp", ".h")]
    (LIB / "validation/format-fader-queue-router-paths.json").write_text(json.dumps(sorted(set(candidate_paths + active_paths)), indent=2) + "\n")
    additions = sorted(set(products) | {"candidates/" + name + "/CONTROLLED-APPLY.json" for name in expected} | {str(queue_block.relative_to(LIB)), str(Path(__file__).relative_to(LIB))})
    (LIB / "validation/integration-fader-queue-router-additions.json").write_text(json.dumps(additions, indent=2) + "\n")


if __name__ == "__main__":
    main()
