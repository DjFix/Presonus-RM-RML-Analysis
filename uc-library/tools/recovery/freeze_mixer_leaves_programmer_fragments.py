"""Freeze this batch's exact active-source inputs; never admit or demote here."""
import hashlib
import json
from pathlib import Path
import re
import shlex

repo = Path.cwd().resolve()
lib = repo / "uc-library"
out = repo / "evidence/recovery/2026-10-28/mixer-leaves-programmer-batch"
read = lambda p: json.loads(p.read_text())
cache = {}
def sha(path):
    if path not in cache:
        cache[path] = hashlib.sha256(path.read_bytes()).hexdigest()
    return cache[path]
workers = read(out / "WORKER-FRAGMENTS.json")
assert workers["all_active_guards_released"] is True
ready, pending = workers["ready"], workers["pending"]
assert len(ready) == len(pending) == 4
source_union, repository_union = {}, {}
key_groups = []
for names, expected in ((ready, 27), (pending, 78)):
    keys = []
    for name in names:
        for row in read(lib / name)["functions"]:
            keys.append((row["original_elf_sha256"], row["mangled"]))
            assert row["domain"].strip()
            proof_path = lib / row["validation"]
            assert sha(proof_path) == row["validation_sha256"]
            proof = read(proof_path)
            assert proof.get("passed", True)
            assert proof["cpp_differential_passed"] and proof["compiled_mangled_names_matched"]
            assert not proof.get("candidate_only", False), str(proof_path)
            for field, union in (("sources", source_union), ("repository_sources", repository_union)):
                for source, digest in row.get(field, {}).items():
                    assert source not in union or union[source] == digest, source
                    union[source] = digest
    assert len(keys) == len(set(keys)) == expected
    key_groups.append(set(keys))
assert key_groups[0].isdisjoint(key_groups[1])
for source, digest in source_union.items():
    assert sha(lib / source) == digest, source
for source, digest in repository_union.items():
    assert Path(source).parts[:3] == ("third_party", "ccl-framework", "core")
    assert sha(repo / source) == digest, source
compile_path = repo / "temp/core-upstream/root-integration-01/compile_commands.json"
compiled = read(compile_path)
tests = {}
names = ["mixer_scaled_time_formatter_tests.cpp", "mixer_filter_q_formatter_tests.cpp",
         "mixer_geq_gain_formatter_tests.cpp", "noaa_programmer_safe_host_serial_tests.cpp",
         "noaa_programmer_safe_host_information_tests.cpp", "noaa_programmer_safe_host_protocol_tests.cpp",
         "noaa_programmer_safe_host_receive_tests.cpp", "noaa_programmer_safe_host_alias_tests.cpp"]
for name in names:
    path = lib / "tests" / name
    rows = [r for r in compiled if Path(r["file"]).resolve() == path]
    assert len(rows) == 1
    command = rows[0]
    tokens = command.get("arguments") or shlex.split(command["command"])
    flags = [t for t in tokens if re.match(r"-[DU]NDEBUG(?:=|$)", t)]
    assert flags and flags[-1] == "-UNDEBUG", name
    tests["tests/" + name] = dict(command=command, ndebug_flags=flags, source_sha256=sha(path))
assert read(lib / "validation/integration.json")["test_suites"] == 268
assert read(lib / "validation/formatting.json")["format_check_passed"]
assertions = dict(passed=True, tests=tests, compile_commands_sha256=sha(compile_path))
(out / "assertions.json").write_text(json.dumps(assertions, indent=2) + "\n")
manifest = dict(passed=True, ready=ready, pending=pending,
                fragment_hashes={n: sha(lib / n) for n in ready + pending},
                source_hashes=source_union, repository_sources=repository_union,
                source_count=len(source_union), ready_entries=27, pending_entries=78,
                cpp_paths=sorted(n for n in source_union if Path(n).suffix in (".cpp", ".hpp", ".h")))
(out / "FINAL-FRAGMENTS.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(json.dumps(dict(passed=True, ready=27, pending=78, unique_sources=len(source_union), tests=8)))
