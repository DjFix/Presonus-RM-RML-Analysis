"""Fixed, hash-guarded BPM/Queue/Router application; never admits readiness."""
import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

REPO = Path.cwd().resolve()
LIB = REPO / "uc-library"
OUT = REPO / "evidence/recovery/2026-10-28/bpm-queue-router-batch"
EXPECTED = {
    "dsp-bpm-counter-lifecycle": "eed8d4f430341f5478905ec3ea6006763a5d16846a1b2f2f0f6b6a3d1b344c10",
    "uc-packet-queue-operations": "7f51f64c6e924b577b888907ddf982261abcfbc756d4153986bd00edbd900249",
    "noaa-router-continuation": "c68a072d7ff3a3365b5ab2ac4e14234470305a17e0fefa4cd8b12a9e2cc03dc8",
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
    products, previous, origins, maps = {}, {}, {}, {}
    candidate_paths = []
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
    bpm, queue, router = (maps[name] for name in EXPECTED)
    partition = {name: queue["production_partition"] for name in queue["production_cpp"]}
    partition.update(router["production_cpp_partition"])
    assert len(partition) == 2 and set(partition.values()) == {"rm"}
    assert not bpm["production_common_cpp"] and not queue["public_headers"] and not router["new_public_headers"]
    groups = (LIB / "cmake/ProductionSourceGroups.cmake").read_text()
    assert counts(groups) == [94, 45, 14]
    assert all(name not in groups for name in partition)
    marker = "set(PRESONUS_rm_SOURCES\n"
    groups = once(groups, marker, marker + "".join("  " + name + "\n" for name in sorted(partition)))
    assert counts(groups) == [94, 45, 16]
    cmake = (LIB / "CMakeLists.txt").read_text()
    properties = ['set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/' + name + '" APPEND PROPERTY COMPILE_OPTIONS -fno-lto)' for name in sorted(partition)]
    cmake = once(cmake, "presonus_build_common_objects()", "presonus_build_common_objects()\n" + "\n".join(properties))
    targets = [dict(name=bpm["test_target"], source="tests/dsp_bpm_counter_lifecycle_tests.cpp", link=bpm["test_link_target"], compile_options=bpm["test_compile_options"], link_options=bpm["test_link_options"], ctests=[dict(name=bpm["test_target"], arguments=[])])] + router["test_targets"]
    tests = []
    for target in targets:
        name = target["name"]
        assert "add_executable(" + name not in cmake and "-UNDEBUG" in target["compile_options"]
        tests += ["  add_executable(" + name + " " + target["source"] + ")", "  target_link_libraries(" + name + " PRIVATE " + target["link"] + ")", "  target_compile_options(" + name + " PRIVATE " + " ".join(target["compile_options"]) + ")", "  target_link_options(" + name + " PRIVATE " + " ".join(target["link_options"]) + ")"]
        for case in target["ctests"]:
            tests.append("  add_test(NAME " + case["name"] + " COMMAND " + name + (" " + " ".join(case["arguments"]) if case["arguments"] else "") + ")")
    block = LIB / "candidates/uc-packet-queue-operations" / queue["test_block"]
    assert sha(block) == queue["test_block_sha256"] and "-UNDEBUG" in block.read_text()
    marker = "  add_library(uc_symbol_catalog_check OBJECT tests/symbol_catalog.cpp)"
    cmake = once(cmake, marker, "\n".join(tests) + "\n" + block.read_text() + marker)
    for name, content in (("CMakeLists.txt", cmake), ("cmake/ProductionSourceGroups.cmake", groups)):
        assert (OUT / "before" / name).read_bytes() == (LIB / name).read_bytes()
        products[name], previous[name], origins[name] = content.encode(), sha(LIB / name), "Root fixed three-map recipe"
    changed = {name for name, old in previous.items() if old is not None and hashlib.sha256(products[name]).hexdigest() != old}
    affected = {kind: [row for row in read(LIB / "validation" / ledger)["functions"] if changed.intersection(row["sources"])] for kind, ledger in (("ready", "ready-functions.json"), ("pending", "compiled-functions.json"))}
    actual_closure = (len(affected["ready"]), len(affected["pending"]))
    assert actual_closure == (19, 42), actual_closure
    plan = dict(products=len(products), partitions=counts(groups), production_cpp=155, suites=179, public_headers=108, affected_ready=19, affected_pending=42)
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
    (LIB / "validation/format-bpm-queue-router-paths.json").write_text(json.dumps(sorted(set(candidate_paths + active_paths)), indent=2) + "\n")
    additions = sorted(set(products) | {"candidates/" + name + "/CONTROLLED-APPLY.json" for name in EXPECTED} | {str(block.relative_to(LIB)), str(Path(__file__).relative_to(LIB))})
    (LIB / "validation/integration-bpm-queue-router-additions.json").write_text(json.dumps(additions, indent=2) + "\n")

if __name__ == "__main__":
    main()
