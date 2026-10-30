"""Fixed three-packet formatter/MIDI/router product application, not admission."""
import argparse
import hashlib
import json
from pathlib import Path
from apply_queue_gate_geq import once, counts

repo = Path.cwd().resolve()
lib = repo / "uc-library"
out = repo / "evidence/recovery/2026-10-28/formatter-midi-input-batch"
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text())
expected = {
    "dsp-formatter-current-gate-geq": "51cd46b89274d52c135a933dc28325167473f346d5affc4b04012055a9e3ba55",
    "uc-midi-connection": "35fd316bbfa4b9cc86849edb77947ab46529a8ed9381ed452669181cebeb778f",
    "noaa-router-mixer-input-routes": "ce7bb725d5b077a062d5877aee37633c6466ca9d23b1f37bd866a053d1668008",
}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    pre = read(out / "candidate-preflight-01/validation.json")
    assert pre["passed"]
    for name, digest in {**pre["unchanged_state"], **pre["inputs"]}.items():
        assert sha(lib / name) == digest, name
    products, previous, origins, maps = {}, {}, {}, {}
    candidate_paths = []
    for candidate, digest in expected.items():
        own = lib / "candidates" / candidate
        path = own / "CONTROLLED-APPLY.json"
        assert sha(path) == digest, candidate
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
    partition, options, headers = {}, {}, []
    for mapping in maps.values():
        assert not partition.keys() & mapping["production_cpp_partition"].keys()
        partition.update(mapping["production_cpp_partition"])
        options.update(mapping["production_compile_options"])
        headers += [p.removeprefix("include/") for p in mapping["new_public_headers"]]
    assert len(partition) == 3 and list(partition.values()).count("common") == 2
    assert headers == ["presonus/uc/midi_connection.hpp"]
    groups = (lib / "cmake/ProductionSourceGroups.cmake").read_text()
    assert counts(groups) == [107, 46, 53]
    for name, group in partition.items():
        assert name not in groups
        marker = "set(PRESONUS_" + group + "_SOURCES\n"
        groups = once(groups, marker, marker + "  " + name + "\n")
    assert counts(groups) == [109, 46, 54]
    assert headers[0] not in groups
    groups = once(groups, "set(PRESONUS_PUBLIC_HEADERS\n", "set(PRESONUS_PUBLIC_HEADERS\n  " + headers[0] + "\n")
    cmake = (lib / "CMakeLists.txt").read_text()
    cmake = once(cmake, "set(PRESONUS_UC_PUBLIC_HEADERS\n", "set(PRESONUS_UC_PUBLIC_HEADERS\n  " + headers[0] + "\n")
    properties = ['set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/' + name + '" APPEND PROPERTY COMPILE_OPTIONS ' + " ".join(flags) + ")" for name, flags in options.items()]
    cmake = once(cmake, "presonus_build_common_objects()", "presonus_build_common_objects()\n" + "\n".join(properties))
    tests, targets, suites = [], [], []
    for mapping in maps.values():
        for target in mapping["test_targets"]:
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
    assert len(targets) == len(set(targets)) == 5 and len(suites) == len(set(suites)) == 7
    marker = "  add_library(uc_symbol_catalog_check OBJECT tests/symbol_catalog.cpp)"
    cmake = once(cmake, marker, "\n".join(tests) + "\n" + marker)
    for name, text in (("CMakeLists.txt", cmake), ("cmake/ProductionSourceGroups.cmake", groups)):
        assert (out / "before" / name).read_bytes() == (lib / name).read_bytes()
        products[name], previous[name], origins[name] = text.encode(), sha(lib / name), "Fixed formatter/MIDI/input root recipe"
    changed = {n for n, old in previous.items() if old and hashlib.sha256(products[n]).hexdigest() != old}
    affected = {kind: [r for r in read(lib / "validation" / filename)["functions"] if changed.intersection(r["sources"])]
                for kind, filename in (("ready", "ready-functions.json"), ("pending", "compiled-functions.json"))}
    assert (len(affected["ready"]), len(affected["pending"])) == (93, 99)
    plan = dict(products=len(products), partitions=counts(groups), cpp=209, suites=250, headers=145,
                affected_ready=93, affected_pending=99, targets=targets, new_suites=suites)
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
        (lib / "validation/format-formatter-midi-input-paths.json").write_text(json.dumps(sorted(set(paths)), indent=2) + "\n")
        additions = set(products) | {f"candidates/{n}/CONTROLLED-APPLY.json" for n in expected}
        additions |= {str(Path(__file__).relative_to(lib)), "tools/recovery/apply_queue_gate_geq.py"}
        (lib / "validation/integration-formatter-midi-input-additions.json").write_text(json.dumps(sorted(additions), indent=2) + "\n")
    print(json.dumps(dict(plan, apply=args.apply)))

if __name__ == "__main__":
    main()
