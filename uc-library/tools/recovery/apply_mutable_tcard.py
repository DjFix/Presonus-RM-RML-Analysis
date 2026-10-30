"""Fixed guarded MessageMutableMessageEvent/TCard application."""
import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

REPO = Path.cwd().resolve()
LIB = REPO / "uc-library"
OUT = REPO / "evidence/recovery/2026-10-28/mutable-eq8-status-batch"
EXPECTED = {
 "uc-mutable-message-event": "3b3927dcbbe0966f384df32d504b07418ed8f24c0eaf3cccf6fa69d2480448bd",
 "noaa-tcard-status": "429cb7a9c6d3c83915f3333fc852df25915d12a8dabb52713c0154ab67176c22",
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def read(path):
    return json.loads(path.read_text())

def once(text, marker, replacement):
    assert text.count(marker) == 1, marker
    return text.replace(marker, replacement, 1)

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
    products, previous, origins, maps, candidate_paths = {}, {}, {}, {}, []
    for candidate, digest in EXPECTED.items():
        own = LIB / "candidates" / candidate
        path = own / "CONTROLLED-APPLY.json"
        assert sha(path) == digest, candidate
        mapping = maps[candidate] = read(path)
        for row in mapping["products"]:
            source = (LIB / row["source"] if row["source"].startswith("candidates/") else own / row["source"]).resolve()
            name = row.get("target", row.get("destination"))
            target = (LIB / name).resolve()
            old = row.get("previous_sha256", row.get("required_destination_sha256"))
            assert source.is_relative_to(LIB) and target.is_relative_to(LIB)
            assert name not in products and not (LIB / name).is_symlink()
            assert sha(source) == row["sha256"]
            assert not target.exists() if old is None else target.is_file() and sha(target) == old
            products[name], previous[name], origins[name] = source.read_bytes(), old, str(source.relative_to(LIB))
            if source.suffix in (".cpp", ".hpp", ".h"):
                candidate_paths.append(str(source.relative_to(LIB)))
    message, noaa = (maps[name] for name in EXPECTED)
    partition = {name: message["production_partition"] for name in message["production_cpp"]}
    partition.update(noaa["production_cpp_partition"])
    assert len(partition) == 3 and list(partition.values()).count("common") == 1
    groups = (LIB / "cmake/ProductionSourceGroups.cmake").read_text()
    assert counts(groups) == [97, 45, 33]
    for group in ("common", "cs18", "rm"):
        names = sorted(name for name, selected in partition.items() if selected == group)
        assert all(name not in groups for name in names)
        if names:
            marker = "set(PRESONUS_" + group + "_SOURCES\n"
            groups = once(groups, marker, marker + "".join("  " + name + "\n" for name in names))
    assert counts(groups) == [98, 45, 35]
    headers = [name.removeprefix("include/") for name in message["public_headers"] + noaa["new_public_headers"]]
    assert len(headers) == len(set(headers)) == 2 and all(name not in groups for name in headers)
    marker = "set(PRESONUS_PUBLIC_HEADERS\n"
    groups = once(groups, marker, marker + "".join("  " + name + "\n" for name in headers))
    cmake = (LIB / "CMakeLists.txt").read_text()
    marker = "set(PRESONUS_UC_PUBLIC_HEADERS\n"
    cmake = once(cmake, marker, marker + "".join("  " + name + "\n" for name in headers))
    source_block = LIB / "candidates/uc-mutable-message-event" / message["source_block"]
    assert sha(source_block) == message["source_block_sha256"]
    properties = []
    for name in sorted(partition):
        if name in message["production_cpp"]:
            continue
        options = ["-fno-lto"]
        properties.append('set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/' + name + '" APPEND PROPERTY COMPILE_OPTIONS ' + " ".join(options) + ")")
    cmake = once(cmake, "presonus_build_common_objects()", "presonus_build_common_objects()\n" + source_block.read_text() + "\n" + "\n".join(properties))
    tests = []
    for target in noaa["test_targets"]:
        name = target["name"]
        assert "add_executable(" + name not in cmake and "-UNDEBUG" in target["compile_options"]
        tests += ["  add_executable(" + name + " " + target["source"] + ")", "  target_link_libraries(" + name + " PRIVATE " + target["link"] + ")", "  target_compile_options(" + name + " PRIVATE " + " ".join(target["compile_options"]) + ")"]
        if target.get("link_options"):
            tests.append("  target_link_options(" + name + " PRIVATE " + " ".join(target["link_options"]) + ")")
        for case in target["ctests"]:
            arguments = case.get("arguments", case.get("args", []))
            tests.append("  add_test(NAME " + case["name"] + " COMMAND " + name + (" " + " ".join(arguments) if arguments else "") + ")")
    test_block = LIB / "candidates/uc-mutable-message-event" / message["test_block"]
    assert sha(test_block) == message["test_block_sha256"] and "-UNDEBUG" in test_block.read_text()
    marker = "  add_library(uc_symbol_catalog_check OBJECT tests/symbol_catalog.cpp)"
    cmake = once(cmake, marker, "\n".join(tests) + "\n" + test_block.read_text() + marker)
    for name, content in (("CMakeLists.txt", cmake), ("cmake/ProductionSourceGroups.cmake", groups)):
        assert (OUT / "before" / name).read_bytes() == (LIB / name).read_bytes()
        products[name], previous[name], origins[name] = content.encode(), sha(LIB / name), "Root fixed two-map recipe"
    changed = {name for name, old in previous.items() if old is not None and hashlib.sha256(products[name]).hexdigest() != old}
    affected = {kind: [row for row in read(LIB / "validation" / ledger)["functions"] if changed.intersection(row["sources"])] for kind, ledger in (("ready", "ready-functions.json"), ("pending", "compiled-functions.json"))}
    assert (len(affected["ready"]), len(affected["pending"])) == (6, 15)
    plan = dict(products=len(products), partitions=counts(groups), production_cpp=178, suites=193, public_headers=122, affected_ready=6, affected_pending=15)
    print(json.dumps(dict(plan, apply=args.apply)), flush=True)
    if not args.apply:
        (OUT / "application-plan.json").write_text(json.dumps(plan, indent=2) + "\n")
        return
    assert not (OUT / "application.json").exists() and read(OUT / "application-plan.json") == plan
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
    (OUT / "application.json").write_text(json.dumps({name: dict(previous_sha256=previous[name], applied_sha256=sha(LIB / name), source=origins[name]) for name in products}, indent=2) + "\n")
    (OUT / "affected-source-closure.json").write_text(json.dumps(affected, indent=2) + "\n")
    active_paths = [name for name in products if Path(name).suffix in (".cpp", ".hpp", ".h")]
    (LIB / "validation/format-mutable-tcard-paths.json").write_text(json.dumps(sorted(set(candidate_paths + active_paths)), indent=2) + "\n")
    additions = sorted(set(products) | {"candidates/" + name + "/CONTROLLED-APPLY.json" for name in EXPECTED} | {str(source_block.relative_to(LIB)), str(test_block.relative_to(LIB)), str(Path(__file__).relative_to(LIB))})
    (LIB / "validation/integration-mutable-tcard-additions.json").write_text(json.dumps(additions, indent=2) + "\n")

if __name__ == "__main__":
    main()
