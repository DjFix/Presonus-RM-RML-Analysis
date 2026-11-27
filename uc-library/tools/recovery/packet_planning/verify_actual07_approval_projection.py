"""Verify the exact proposed Actual07 wave lists after live registration and admission."""
from collections import defaultdict
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import sys

from project_actual07_partitions import P, S, ROOT, previous_compiler_deps, ref, scoped_proposals, source_paths
from packet_cycle import (
    check_parked_assignment, check_vendor_source_route, read, save, target_of, verify_planned_equivalence,
    work_targets,
)
from context_runtime import guard, sha
from dedup_work import active_index
from execution_review import batch_validation, checked_digest

sys.path.insert(0, str(ROOT / "uc-library/tools/recovery"))
from select_context import adapter


PROJECTION = P / "ACTUAL07-PRECOPY-EXACT67-TWO-WAVES01.json"
PROJECTION_SHA256 = "ff73b3be6b7f8515114b2ba35335592f3c908b9afeaddde993df39b15249a864"
PRIOR_PACKET_ROOT = P / "actual06-first-capture01/packets"
FIELD_PACKET_ROOT = P / "actual04-next-batch01/packets"
BOOK_ORIGINALS = ("_ZN8Presonus5Panel4BookC1Ei", "_ZN8Presonus5Panel4BookC2Ei")
PRIOR_TYPED_BASES = {
    "DecayTimeFormatter": "_ZN8Presonus5Mixer18DecayTimeFormatterD1Ev",
    "Element": "_ZN8Presonus5Panel7ElementD2Ev",
    "OffscreenElement": "_ZN8Presonus5Panel16OffscreenElementD1Ev",
}
CURRENT_REVIEWS = {
    "ACTUAL07_TYPED_G02_G03_MAX13_REVIEW_CANONICAL01.json":
        "631e8b83961f6dce45e6b66140b1c03335a57017bcf9d35185afd3545080a71a",
    "ACTUAL07_TAIL_EARLY15_EXACT_REVIEW_CANONICAL01.json":
        "c1148e333840da7076632cdb87ebc10fad1f700d23b847271a01576046edc675",
}


def verify_record(view, elf, mangled, label):
    row = view.c.execute("SELECT * FROM records WHERE elf=? AND mangled=?", (elf, mangled)).fetchone()
    if row is None or row["status"] not in {"ready", "pending"}:
        raise ValueError(f"{label}: missing live exact predecessor {elf}/{mangled}")
    material = view.restore(row)
    lib = ROOT / "uc-library"
    proof = lib / material["validation"]
    assert checked_digest(ROOT, proof) == material["validation_sha256"]
    for file, expected in material["sources"].items():
        assert checked_digest(ROOT, lib / file) == expected, (label, file)
    return dict(label=label, elf=elf, original=mangled, status=row["status"],
                proof=ref(proof), source_hashes=material["sources"])


def main():
    admission_path = Path(sys.argv[1]).resolve(strict=True)
    output = Path(sys.argv[2]).resolve()
    assert output.is_relative_to(P) and not output.exists()
    assert sha(PROJECTION) == PROJECTION_SHA256
    phase_projection = read(PROJECTION)
    registered = S.parent / "graph/actual07/VERIFIED.json"
    receipt = read(registered)
    active_path = ROOT / "dependency-graph/ACTIVE.json"
    active = read(active_path)
    assert active == receipt["active"] and not receipt["pending_or_unregistered"]
    state = guard(ROOT, active)
    copy_ref = phase_projection["inputs"]["accepted_copy_plan"]
    copy_file = ROOT / copy_ref["path"]
    assert sha(copy_file) == copy_ref["sha256"]
    # The exact live SQLite records below, not the presence of this receipt,
    # determine whether each prerequisite can serve the next wave.
    assert admission_path.is_file()
    source_files = {row["path"]: row for row in read(copy_file)["files"]}
    from context_runtime import inside

    for path, item in source_files.items():
        if Path(path).suffix in {".h", ".hpp", ".cpp"}:
            assert checked_digest(ROOT, inside(ROOT, path)) == item["after"], path
    phases = phase_projection["phases"]
    tasks = phase_projection["tasks"]
    canonical_reviews = {}
    for name, digest in CURRENT_REVIEWS.items():
        path = S / name
        assert sha(path) == digest
        review = read(path)
        assert not review.get("pending_exact_canonical_providers")
        canonical_reviews.update(review["tasks"])
    assert len(canonical_reviews) == 28 and set(canonical_reviews) <= tasks.keys()
    predecessor_tasks = {item for task in tasks.values() for item in task["previous_prerequisites"]}
    native_targets, prerequisites = {}, defaultdict(list)
    catalog, pointer = active_index(ROOT)
    with closing(catalog), adapter.snapshot(ROOT / "uc-library") as view, batch_validation(ROOT):
        for task_id in sorted(predecessor_tasks | {"cycle20_g06_s12", "cycle20_g06_s13", "cycle20_g07_s19"}):
            factory = FIELD_PACKET_ROOT if task_id in {"cycle20_g06_s12", "cycle20_g06_s13"} else PRIOR_PACKET_ROOT
            request = read(factory / task_id / "request.json")
            for target in request["targets"]:
                prerequisites[task_id].append(verify_record(
                    view, target["original_elf_sha256"], target["mangled"], task_id
                ))
        elves = sorted({record["elf"] for record in prerequisites["cycle20_g07_s19"]})
        assert len(elves) == 2
        for elf in elves:
            for original in BOOK_ORIGINALS:
                prerequisites["Book(int)"].append(verify_record(view, elf, original, "Book(int)"))
            for label, original in PRIOR_TYPED_BASES.items():
                prerequisites[label].append(verify_record(view, elf, original, label))
        for task_id, task in tasks.items():
            proposal = ROOT / task["proposal"]["path"]
            assert sha(proposal) == task["proposal"]["sha256"]
            candidate, _ = scoped_proposals(proposal)[task_id]
            assert candidate["work_item_id"] == task["upstream_work_id"]
            originals = work_targets(catalog, candidate, target_of(candidate))
            if "exact_originals" in task:
                assert originals == task["exact_originals"]
            check_parked_assignment(task_id, candidate["work_item_id"], originals)
            assert not catalog.execute(
                "SELECT 1 FROM work_claims WHERE work_item_id=? AND state='active'",
                (candidate["work_item_id"],),
            ).fetchone(), task_id
            for original in originals:
                check_vendor_source_route(original)
                key = original["original_elf_sha256"], original["mangled"]
                current = view.c.execute("SELECT status FROM records WHERE elf=? AND mangled=?", key).fetchone()
                assert current is None or current["status"] not in {"ready", "pending"}, (task_id, key)
            native_targets[task_id] = originals
    verify_planned_equivalence([
        dict(task_id=task_id, targets=originals, existing_work_item_id=tasks[task_id]["upstream_work_id"])
        for task_id, originals in native_targets.items()
    ])

    seen = set()
    reports = []
    for phase in phases:
        readers, writers, packets = defaultdict(set), defaultdict(set), {}
        for owner, task_ids in phase["exact_groups"].items():
            batch = []
            assert 1 <= len(task_ids) <= 10
            for task_id in task_ids:
                task = tasks[task_id]
                assert task["owner"] == owner and task_id not in seen
                seen.add(task_id)
                originals = native_targets[task_id]
                current_deps = list(previous_compiler_deps(task["owned"]))
                fresh_review = canonical_reviews.get(task_id, {})
                current_reads = (set(task["declared_reads"]) | set().union(*(p for _, p in current_deps))
                                 | set(source_paths(fresh_review)) | set(fresh_review.get("extra_source_reads", [])))
                current_sources = sorted({p for p in current_reads if (ROOT / p).is_file()} |
                                         {p for p in task["owned"] if (ROOT / p).is_file()})
                for path in task["owned"]:
                    writers[path].add(owner)
                for path in current_reads:
                    readers[path].add(owner)
                batch.append(dict(task=task_id, work_item_id=task["upstream_work_id"],
                                  originals=originals, owned_files=task["owned"],
                                  source_sha256={path: checked_digest(ROOT, ROOT / path) for path in current_sources},
                                  compiler_observations=[p for p, _ in current_deps]))
            packets[owner] = batch
        overlaps = {path: sorted(readers[path] | owners) for path, owners in writers.items()
                    if readers[path] - owners or len(owners) > 1}
        if overlaps:
            raise ValueError(f"Refine Actual07 phase {phase['number']} on current compiler inputs: {overlaps}")
        reports.append(dict(number=phase["number"], owners=packets, count=phase["count"]))
    assert len(seen) == 67 and [phase["count"] for phase in reports] == [41, 26]
    occurrences = {(t["original_elf_sha256"], t["mangled"], t["address"], t["size"])
                   for originals in native_targets.values() for t in originals}
    assert len(occurrences) == sum(map(len, native_targets.values()))
    assert read(active_path) == active
    save(output, dict(
        status="exact read-only proposed wave list awaiting specific Root authorization",
        observed_utc=datetime.now(timezone.utc).isoformat(),
        verified_actual07=ref(registered), active=active, source_guard_count=len(state["files"]),
        canonical_provider_admission=ref(admission_path), precopy_projection=ref(PROJECTION),
        canonical_review_bindings=[ref(S / name) for name in CURRENT_REVIEWS],
        prerequisites=dict(prerequisites), phases=reports, original_elf_count=len(occurrences),
        required_cross_wave_releases=phase_projection["cross_phase_read_release"],
        same_owner_release=phase_projection["same_owner_release"],
        claims_mutated=False, graph_mutated=False, packet_preparations=0,
    ))
    print(output, sha(output), len(seen), len(occurrences))


if __name__ == "__main__":
    main()
