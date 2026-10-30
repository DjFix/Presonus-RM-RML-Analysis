#!/usr/bin/env python3
"""Normalize immutable completed outputs; never compile or run behavior again."""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
INPUT = "validation/dice-packet-response-active/runs/20261027T031919.478367Z"
PROOF_SHA = "55d57add94f8d9737a8d05fc24ac63195f6a9e69cc145d61bbfe9155a2889af6"
MANIFEST_SHA = "02de8b074d6df695d1fb5bb731ac3e51d4b038dc498442c73ce8674869a9836b"
LOGS = {
    "packet-constructor": ("packet-constructor", ["PASS: constructor 3072 "]),
    "packet-commands": ("packet-commands", ["PASS: commands 9584 "]),
    "packet-receivers": ("packet-receivers", ["PASS: receivers 18432 "]),
    "wait-client": ("wait-client", ["PASS 11128 original ARM wait"]),
    "wait-server": ("wait-server", ["PASS 11668 original ARM wait"]),
    "dice_response_ccl_smoke": ("dice_response_ccl_smoke", ["PASS actual CCL clock/sleep/debug"]),
    "dice_packet_clock_smoke": ("dice_packet_clock_smoke", ["PASS: actual pinned Core Linux clock provider; 3 packet"]),
    "dice": ("dice-subsystem", ["PASS: 65536 original ARM filter cases, 524 command-string cases"]),
    "avb-protocol": ("avb-protocol", ["PASS 65536 accepts, 6146 reverse, 73932 exact-memory"]),
    "avb-streams": ("avb-streams", ["PASS 572936 original ARM AVB stream"]),
    "avb-receive": ("avb-receive", ["PASS 81520 original ARM receive"]),
    "avb-lookup-client": ("avb-lookup-client", ["PASS 80962 original ARM lookup"]),
    "avb-lookup-server": ("avb-lookup-server", ["PASS 80962 original ARM lookup"]),
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository", type=Path)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    repo = args.repository.resolve()
    library = repo / "uc-library"
    if not library.is_dir():
        library = repo / "uc-library"
    original = library / INPUT
    proof_path = original / "validation.json"
    assert sha(proof_path) == PROOF_SHA
    old = json.loads(proof_path.read_text())
    evidence = repo / "evidence/recovery/2026-10-27/dice-packet-response-active/20261027T031919.478367Z"
    assert sha(evidence / "manifest.json") == MANIFEST_SHA
    for name, digest in json.loads((evidence / "manifest.json").read_text()).items():
        path = evidence / name
        assert path.resolve().is_relative_to(evidence)
        assert sha(path) == digest, name
    commands = json.loads((evidence / "commands.json").read_text())
    by_name = {row["name"]: row for row in commands}
    assert all(row["exit_code"] == 0 for row in commands)
    assert set(old["native_results"]) == set(LOGS) and len(LOGS) == 13
    checked_logs = {}
    for group, (log_name, needles) in LOGS.items():
        text = (evidence / (log_name + ".log")).read_text()
        assert text == old["native_results"][group]
        assert by_name[log_name]["exit_code"] == 0
        assert all(needle in text for needle in needles), group
        checked_logs[group] = dict(sha256=sha(evidence / (log_name + ".log")), expected_count_assertions=needles)
    for relative, digest in old["retained_fixtures"].items():
        assert sha(library / relative) == digest, relative
    # Count retained text records independently; binary protocols retain their
    # immutable fixture hashes plus original fresh driver count assertions.
    text_counts = {}
    expected_counts = {"constructors.txt":3072, "commands.txt":9584, "receivers.txt":18432,
                       "client-response-vectors.txt.gz":11128, "server-response-vectors.txt.gz":11668,
                       "client-lookup-vectors.txt":80962, "server-lookup-vectors.txt":80962,
                       "accept-vectors.txt":65536, "reverse-vectors.txt":6146}
    for relative in old["retained_fixtures"]:
        path = library / relative
        if path.name in expected_counts:
            opener = gzip.open if path.suffix == ".gz" else open
            with opener(path, "rt") as stream:
                count = sum(bool(line.strip()) for line in stream)
            assert count == expected_counts[path.name], (relative, count)
            text_counts[relative] = count
    assert len(text_counts) == len(expected_counts)
    old_ready = json.loads((original / "ready-functions.fragment.json").read_text())["functions"]
    old_pending = json.loads((original / "compiled-functions.fragment.json").read_text())["functions"]
    assert len(old_ready) == 16 and len(old_pending) == 9
    entries = old_ready + old_pending
    assert len({(r["original_elf_sha256"], r["mangled"]) for r in entries}) == 25
    for row in entries:
        assert row["domain"].strip()
        for name, digest in row["sources"].items():
            path = (library / name).resolve()
            assert path.is_relative_to(library) and sha(path) == digest, name
        for name, digest in row["repository_sources"].items():
            path = (repo / name).resolve()
            assert path.is_relative_to(repo / "third_party/ccl-framework/core") and sha(path) == digest, name
    for name, digest in old["fresh_artifacts"].items():
        assert sha(evidence / "artifacts" / name.replace("/", "_")) == digest, name
    names = {line.split()[-1] for line in (evidence / "nm.log").read_text().splitlines() if line.split()}
    assert {row["mangled"] for row in old["functions"]} <= names
    plan = dict(immutable_logs_checked=13, independent_text_fixture_counts=text_counts,
                ready_entries=16, pending_entries=9, immutable_artifacts_checked=len(old["fresh_artifacts"]),
                cpp_recompiled=False, behavior_rerun=False, original_oracle_regenerated=False)
    if not args.execute:
        print(json.dumps(plan, indent=2))
        return
    assert sys.platform.startswith("linux")
    from avb_protocol_reseal import verify_originals
    from merge_readiness import proof_covers, repository_sources_match
    actual_bytes = verify_originals(repo, library, [old["functions"]])
    key = lambda row: (row["role"], row["mangled"], row["byte_sha256"])
    assert sorted(actual_bytes, key=key) == sorted(old["byte_checks"], key=key)
    assert len(actual_bytes) == 25
    actual_nm = subprocess.run(["nm", "--defined-only", str(evidence / "artifacts/libactive_product.a")],
                               text=True, capture_output=True, check=True)
    actual_names = {line.split()[-1] for line in actual_nm.stdout.splitlines() if line.split()}
    assert {row["mangled"] for row in old["functions"]} <= actual_names
    # Preserve exact method caveats despite the merger's aggregate-field update.
    method_notes = {str((r["role"], r["mangled"])):r.get("declaration_uncertainties", []) for r in entries}
    aggregate, seen = [], set()
    for value in method_notes.values():
        for note in value if isinstance(value, list) else [value]:
            encoded = json.dumps(note, sort_keys=True)
            if encoded not in seen:
                seen.add(encoded)
                aggregate.append(note)
    normalized = dict(old)
    normalized.update(cpp_differential_passed=True, compiled_mangled_names_matched=True,
        mangled_names=sorted({row["mangled"] for row in old_ready}),
        compiled_original_mangled_names=sorted({row["mangled"] for row in old["functions"]}),
        declaration_uncertainties=aggregate, function_declaration_uncertainties=method_notes,
        normalization=dict(input_path=str(proof_path.relative_to(library)), input_sha256=PROOF_SHA,
            immutable_evidence_manifest_sha256=MANIFEST_SHA, checked_logs=checked_logs,
            independent_text_fixture_counts=text_counts, original_ranges_rechecked=25,
            actual_archive_nm_checked=True, cpp_recompiled=False, behavior_rerun=False,
            explanation="Schema-only derivative of completed fresh active source replay. Canonical flags are justified by immutable exit0 logs, fixture/hash/count checks, actual archive nm and original byte ranges; no stronger behavioral or declaration claim.",
            seal_tool=dict(path=str(Path(__file__).resolve().relative_to(library)), sha256=sha(Path(__file__)))))
    # Non-mutating use of the ACTUAL merger helpers, not a duplicate predicate.
    ready_checks = [dict(mangled=r["mangled"], original_elf_sha256=r["original_elf_sha256"],
                         proof_covers=proof_covers(normalized, r), repository_sources_match=repository_sources_match(library, r)) for r in old_ready]
    assert all(r["proof_covers"] and r["repository_sources_match"] for r in ready_checks)
    pending_checks = []
    for row in old_pending:
        good = row["portable_ready"] is False and row["cpp_compiled"] is True and row["mangling_namespace_checked"] is True
        assert good and repository_sources_match(library, row)
        pending_checks.append(dict(mangled=row["mangled"], original_elf_sha256=row["original_elf_sha256"], gate_fields=True, repository_sources_match=True))
    formatting = json.loads((library / "validation/formatting.json").read_text())
    missing_format = sorted({name for row in entries for name, digest in row["sources"].items()
                            if Path(name).suffix in (".cpp", ".hpp", ".h") and formatting["files"].get(name) != digest})
    preflight = dict(ready_checks=ready_checks, pending_checks=pending_checks,
        all_current_source_hashes_match=True, missing_global_format_records=missing_format,
        actual_merger_helper_sha256=sha(library / "tools/merge_readiness.py"),
        global_formatting_sha256=sha(library / "validation/formatting.json"),
        passed=not missing_format and formatting["format_check_passed"])
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    output = library / "validation/dice-packet-response-active/normalized" / stamp
    output.mkdir(parents=True, exist_ok=False)
    out_evidence = repo / "evidence/recovery/2026-10-27/dice-packet-response-normalized" / stamp
    out_evidence.mkdir(parents=True, exist_ok=False)
    new_proof = output / "validation.json"
    new_proof.write_text(json.dumps(normalized, indent=2) + "\n")
    for rows, name in ((old_ready,"ready-functions.fragment.json"), (old_pending,"compiled-functions.fragment.json")):
        updated = []
        for row in rows:
            updated.append(dict(row, validation=str(new_proof.relative_to(library)), validation_sha256=sha(new_proof),
                                method_declaration_uncertainties=row.get("declaration_uncertainties", [])))
        (output / name).write_text(json.dumps({"functions":updated}, indent=2) + "\n")
    (output / "merge-preflight.json").write_text(json.dumps(preflight, indent=2) + "\n")
    (output / "NORMALIZATION.md").write_text("# Schema-only derivative seal\n\nNo C++ compilation, fixture replay or original ARM execution was repeated. The complete original proof and logs remain unchanged. This seal independently checks all13 immutable replay logs/exitcodes, retained fixture hashes and text counts, all41 artifacts, actual archive nm membership and25 original byte ranges. Canonical flags describe these completed checks. Only the16 admitted ready symbols appear in mangled_names; all compiled original symbols remain in compiled_original_mangled_names. Per-method declaration caveats are retained separately from aggregate merger metadata.\n")
    for path in output.iterdir():
        shutil.copy2(path, out_evidence / path.name)
    (out_evidence / "actual-archive-nm.log").write_text(actual_nm.stdout + actual_nm.stderr)
    (out_evidence / "manifest.json").write_text(json.dumps({p.name:sha(p) for p in sorted(out_evidence.iterdir()) if p.is_file()}, indent=2) + "\n")
    print(json.dumps(dict(proof=str(new_proof), sha256=sha(new_proof), preflight_passed=preflight["passed"],
                         missing_format_records=missing_format, ready=16, pending=9, evidence=str(out_evidence)), indent=2))


if __name__ == "__main__":
    main()
