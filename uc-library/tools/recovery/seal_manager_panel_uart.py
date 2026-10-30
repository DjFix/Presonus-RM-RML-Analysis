"""Fixed active Panel UART closure seal for the Manager/discovery batch."""
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
LIB = REPO / "uc-library"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    replay_path = (REPO / sys.argv[1]).resolve()
    assert replay_path.is_relative_to(REPO / "evidence/recovery/2026-10-28/manager-discovery-batch")
    replay = json.loads(replay_path.read_text())
    assert replay["passed"] and replay["source_mode"] == "active"
    assert set(replay["modes"]) == {"release", "sanitizers"}
    assert all(mode["passed"] and mode["cases_per_role"] == 2405 for mode in replay["modes"].values())
    old_path = LIB / "validation/panel-uart-comm-active/active-01/validation.json"
    previous = json.loads(old_path.read_text())
    assert previous["passed"] and previous["cpp_differential_passed"]
    formatting_path = LIB / "validation/formatting.json"
    integration_path = LIB / "validation/integration.json"
    formatting = json.loads(formatting_path.read_text())
    integration = json.loads(integration_path.read_text())
    assert formatting["format_check_passed"] and integration["ctest_passed"]
    for name, digest in integration["files"].items():
        assert sha(LIB / name) == digest, name
    sources = {}
    repository_sources = {}
    sdk_core = REPO / "temp/core-upstream/root-integration-01/upstream-core/sdk/include/presonus-core-5/core"
    for group in ("source_hashes", "compiler_dependencies"):
        for name, digest in replay[group].items():
            path = (REPO / name).resolve()
            assert sha(path) == digest, name
            if path.is_relative_to(LIB):
                relative = str(path.relative_to(LIB))
                sources[relative] = digest
                if path.suffix in (".cpp", ".hpp", ".h"):
                    assert formatting["files"].get(relative) == digest, relative
            elif path.is_relative_to(sdk_core):
                upstream = REPO / "third_party/ccl-framework/core" / path.relative_to(sdk_core)
                assert sha(upstream) == digest
                repository_sources[str(upstream.relative_to(REPO))] = digest
    assert repository_sources
    sources[str(Path(__file__).relative_to(LIB))] = sha(Path(__file__))
    assert sha(REPO / "temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libcorelib.a") == replay["actual_core_archive_sha256"]
    key = lambda row: (row["original_elf_sha256"], row["mangled"])
    originals = {key(row): row for row in replay["original_ranges"]}
    assert len(originals) == 22
    ledgers = {}
    for kind, name, expected in (("ready", "ready-functions.json", 10), ("pending", "compiled-functions.json", 12)):
        rows = json.loads((LIB / "validation" / name).read_text())["functions"]
        ledgers[kind] = [row for row in rows if key(row) in originals]
        assert len(ledgers[kind]) == expected
    assert not {key(row) for row in ledgers["ready"]} & {key(row) for row in ledgers["pending"]}
    out = LIB / "validation/panel-uart-manager-discovery/active-01"
    out.mkdir(parents=True, exist_ok=False)
    domain = previous["domain"] + " Fresh source-port replay includes the shared-provider UART header growth; newly owned-provider lifetime is separately covered by Manager lifecycle tests. No binary layout or original shared ownership claim."
    proof = {"passed": True, "portable_ready": True, "cpp_differential_passed": True, "compiled_mangled_names_matched": True, "active_source_replay_passed": True, "functions": list(originals.values()), "mangled_names": sorted({row["mangled"] for row in ledgers["ready"]}), "compiled_original_mangled_names": sorted({row["mangled"] for row in originals.values()}), "domain": domain, "sources": sources, "repository_sources": repository_sources, "replay": str(replay_path.relative_to(REPO)), "replay_sha256": sha(replay_path), "previous_proof": str(old_path.relative_to(LIB)), "previous_proof_sha256": sha(old_path), "integration_sha256": sha(integration_path), "formatting_sha256": sha(formatting_path), "formatter_version": replay["formatter_version"], "core_binary_loaded": False, "device_io_executed": False, "hardware_verified": False, "original_function_fully_verified": False, "production_role_archive_checks_separate": True, "tool_sha256": sha(Path(__file__))}
    proof_path = out / "validation.json"
    proof_path.write_text(json.dumps(proof, indent=2) + "\n")
    for kind, rows in ledgers.items():
        refreshed = []
        for old in rows:
            row = dict(old, sources=sources, repository_sources=repository_sources, validation=str(proof_path.relative_to(LIB)), validation_sha256=sha(proof_path), domain=domain, cpp_compiled=True, mangling_namespace_checked=True, portable_ready=kind == "ready")
            original = originals[key(row)]
            row.update(original_address=original["address"], original_size=original["size"], original_section=original["section"], original_byte_sha256=original["sha256"])
            if kind == "pending":
                row.update(compiled_declaration_pending=True, original_return_declaration_proven=False)
            refreshed.append(row)
        (out / (kind + "-functions.fragment.json")).write_text(json.dumps({"functions": refreshed}, indent=2) + "\n")
    print(json.dumps({"passed": True, "ready_refresh": 10, "pending_refresh": 12, "proof_sha256": sha(proof_path), "admitted": False}))


if __name__ == "__main__":
    main()
