"""Guarded, fixed Manager/discovery integration; canonical ledgers untouched."""
import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

REPO = Path.cwd().resolve()
LIB = REPO / "uc-library"
OUT = REPO / "evidence/recovery/2026-10-28/manager-discovery-batch"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def once(text, needle, replacement):
    assert text.count(needle) == 1, needle
    return text.replace(needle, replacement, 1)


def counts(text):
    return [len(re.search(r"set\(PRESONUS_" + group + r"_SOURCES\n(.*?)\n\)", text, re.S).group(1).split()) for group in ("common", "cs18", "rm")]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    preflight = read(OUT / "candidate-preflight-01/validation.json")
    assert preflight["passed"]
    for name, digest in preflight["unchanged_state"].items():
        assert sha(LIB / name) == digest, name
    for name, digest in preflight["inputs"].items():
        assert sha(LIB / name) == digest, name
    manager_path = LIB / "candidates/dice-manager-lifecycle/CONTROLLED-APPLY.json"
    network_path = LIB / "candidates/uc-network-discovery-lifecycle/CONTROLLED-APPLY.json"
    assert sha(manager_path) == "a7415efaaa005761da8fffe0ad3fb3ba764753807a57c9b065acc20024105b5a"
    assert sha(network_path) == "923337877497a38677472da3c307824c1e52a880b98d217ceb0a070a844b4bbd"
    manager, network = read(manager_path), read(network_path)
    network_root = network_path.parent
    products, old, origins = {}, {}, {}

    def add(source, target, digest, previous):
        source = source.resolve()
        destination = (LIB / target).resolve()
        assert source.is_relative_to(LIB) and destination.is_relative_to(LIB)
        assert target not in products and not (LIB / target).is_symlink()
        assert sha(source) == digest
        assert not destination.exists() if previous is None else destination.is_file() and sha(destination) == previous
        products[target] = source.read_bytes()
        old[target] = previous
        origins[target] = str(source.relative_to(LIB))

    for row in manager["products"]:
        add(LIB / row["source"], row["target"], row["sha256"], row["previous_sha256"])
    for row in network["products"]:
        add(network_root / row["source"], row["destination"], row["sha256"], row["required_destination_sha256"])
    groups = (LIB / "cmake/ProductionSourceGroups.cmake").read_text()
    assert counts(groups) == [91, 42, 11]
    partition = dict(manager["production_cpp_partition"])
    for name in network["production_cpp"]:
        assert name not in partition
        partition[name] = network["production_partition"]
    assert len(partition) == 5
    for group in ("common", "cs18", "rm"):
        names = sorted(name for name, selected in partition.items() if selected == group)
        for name in names:
            assert name not in groups
        if names:
            marker = "set(PRESONUS_" + group + "_SOURCES\n"
            groups = once(groups, marker, marker + "".join("  " + name + "\n" for name in names))
    assert counts(groups) == [93, 45, 11]
    headers = [name.removeprefix("include/") for name in manager["new_public_headers"] + network["public_headers"]]
    assert len(headers) == len(set(headers)) == 3
    header_marker = "set(PRESONUS_PUBLIC_HEADERS\n"
    groups = once(groups, header_marker, header_marker + "".join("  " + name + "\n" for name in headers))
    cmake = (LIB / "CMakeLists.txt").read_text()
    marker = "set(PRESONUS_UC_PUBLIC_HEADERS\n"
    cmake = once(cmake, marker, marker + "".join("  " + name + "\n" for name in headers))
    properties = []
    for name, group in sorted(partition.items()):
        options = "-fno-lto -fno-rtti" if group == "cs18" else "-fno-lto"
        properties.append('set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/' + name + '" APPEND PROPERTY COMPILE_OPTIONS ' + options + ')')
    cmake = once(cmake, "presonus_build_common_objects()", "presonus_build_common_objects()\n" + "\n".join(properties))
    test_lines = []
    for test in manager["test_targets"]:
        name = test["name"]
        assert "add_executable(" + name not in cmake
        test_lines += ["  add_executable(" + name + " " + test["source"] + ")", "  target_link_libraries(" + name + " PRIVATE " + test["link"] + ")", "  target_compile_options(" + name + " PRIVATE " + " ".join(test["compile_options"]) + ")"]
        if test.get("link_options"):
            test_lines.append("  target_link_options(" + name + " PRIVATE " + " ".join(test["link_options"]) + ")")
        for case in test["ctests"]:
            test_lines.append("  add_test(NAME " + case["name"] + " COMMAND " + name + (" " + " ".join(case["arguments"]) if case["arguments"] else "") + ")")
    block = network_root / network["cmake_test_block"]
    assert sha(block) == network["cmake_test_block_sha256"]
    test_text = "\n".join(test_lines) + "\n" + block.read_text()
    marker = "  add_library(uc_symbol_catalog_check OBJECT tests/symbol_catalog.cpp)"
    cmake = once(cmake, marker, test_text + marker)
    for name, content in (("CMakeLists.txt", cmake), ("cmake/ProductionSourceGroups.cmake", groups)):
        assert (OUT / "before" / name).read_bytes() == (LIB / name).read_bytes()
        products[name] = content.encode()
        old[name] = sha(LIB / name)
        origins[name] = "Root-reviewed final Manager/Network recipes; exactly one CPP partition and both public-header lists"
    changed = {name for name, digest in old.items() if digest is not None and hashlib.sha256(products[name]).hexdigest() != digest}
    affected = {kind: [row for row in read(LIB / "validation" / ledger)["functions"] if changed.intersection(row["sources"])] for kind, ledger in (("ready", "ready-functions.json"), ("pending", "compiled-functions.json"))}
    assert (len(affected["ready"]), len(affected["pending"])) == (46, 188)
    plan = {"apply": args.apply, "products": len(products), "partitions": counts(groups), "suites": 169, "public_headers": 106, "affected_ready": 46, "affected_pending": 188}
    print(json.dumps(plan), flush=True)
    if not args.apply:
        (OUT / "application-plan.json").write_text(json.dumps(plan, indent=2) + "\n")
        return
    assert not (OUT / "application.json").exists()
    assert read(OUT / "application-plan.json")["products"] == len(products)
    for name, content in products.items():
        destination = LIB / name
        if destination.exists():
            backup = OUT / "before" / name
            backup.parent.mkdir(parents=True, exist_ok=True)
            if backup.exists():
                assert backup.read_bytes() == destination.read_bytes()
            else:
                shutil.copyfile(destination, backup)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
    (OUT / "application.json").write_text(json.dumps({"products": {name: {"previous_sha256": old[name], "applied_sha256": sha(LIB / name), "source": origins[name]} for name in products}, "candidate_preflight_sha256": sha(OUT / "candidate-preflight-01/validation.json")}, indent=2) + "\n")
    (OUT / "affected-source-closure.json").write_text(json.dumps(affected, indent=2) + "\n")
    paths = read(OUT / "candidate-format-paths.json") + [name for name in products if Path(name).suffix in (".cpp", ".hpp", ".h")]
    (LIB / "validation/format-manager-discovery-paths.json").write_text(json.dumps(sorted(set(paths)), indent=2) + "\n")
    additions = sorted(set(products) | {str(path.relative_to(LIB)) for path in (manager_path, network_path, block, Path(__file__).resolve(), LIB / "tools/recovery/replay_manager_panel_uart.py", LIB / "tools/recovery/seal_manager_panel_uart.py")})
    (LIB / "validation/integration-manager-discovery-additions.json").write_text(json.dumps(additions, indent=2) + "\n")


if __name__ == "__main__":
    main()
