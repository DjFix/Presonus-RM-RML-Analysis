"""Audit both preliminary Actual07 waves without selecting or claiming work."""
from collections import defaultdict
from contextlib import closing
from itertools import combinations

from project_actual07_partitions import (
    P, S, ROOT, exact_dependency_ids, previous_compiler_deps, ref, scoped_proposals, source_paths,
)
from packet_cycle import check_parked_assignment, check_vendor_source_route, read, save, target_of
from context_runtime import sha
from dedup_work import active_index


PROJECTION = S / "ACTUAL07_67_EARLY_TAIL_COMPATIBILITY_PROJECTION01.json"
REVIEW = S / "ACTUAL07_TAIL_EARLY15_EXACT_REVIEW_PREVIEW02.json"
COPY = S.parent / "integration/preview-actual06-next42/ACCEPTED_PLAN.json"
INVENTORY = S / "actual07-tail-early15-inventory01/INVENTORY.json"
BOOK = S / "ACTUAL07_BOOK_G07_SCANNERS_CURRENT_REVIEW01.json"


def checked_ref(spec):
    path = ROOT / spec["path"]
    if sha(path) != spec["sha256"]:
        raise ValueError("Changed bound projection input " + spec["path"])
    return path


def logical_name(chunk):
    return "cycle20_g05" if chunk.startswith("g05_") else chunk


def main():
    proposal = read(PROJECTION)
    base = read(checked_ref(proposal["base"]))
    tail_source = checked_ref(proposal["bundle"])
    tail = scoped_proposals(tail_source)
    statuses = read(REVIEW)
    reviews = statuses["tasks"]
    current_inventory = {
        row["task_id"]: row for group in read(INVENTORY)["lanes"] for row in group["tasks"]
    }
    assert set(tail) == set(reviews) == set(current_inventory) == set(proposal["added_early_tasks"])
    assert len(tail) == 15 and len(base["tasks"]) == 52
    by_work = {row["work_item_id"]: name for name, (row, _) in tail.items()}
    copies = {item["path"]: item for item in read(COPY)["files"]}
    tasks = {name: row.copy() for name, row in base["tasks"].items()}
    for name, (candidate, scope) in tail.items():
        row = current_inventory[name]
        review = reviews[name]
        assert candidate["work_item_id"] == review["work_item_id"] == row["candidate"]["work_item_id"]
        assert row["native"]["sha256"] == review["native_evidence_sha256"]
        for target in row["targets"]:
            check_vendor_source_route(target)
        check_parked_assignment(name, candidate["work_item_id"], row["targets"])
        owned = set(scope["owned_headers"]) | set(scope["owned_sources"])
        declared = set(candidate.get("frozen_provider_files", {})) | set(source_paths(review))
        declared.update(review.get("extra_source_reads", []))
        deps = list(previous_compiler_deps(owned))
        observed = set().union(*(paths for _, paths in deps))
        previous = set(candidate.get("accepted_predecessor_task_ids", []))
        if name in statuses["pending_exact_canonical_providers"]:
            previous.add(statuses["pending_exact_canonical_providers"][name])
        tasks[name] = dict(
            owner="_".join(name.split("_")[:2]), proposal=ref(tail_source), review=ref(REVIEW),
            upstream_work_id=candidate["work_item_id"], owned=sorted(owned),
            exact_originals=row["targets"],
            declared_reads=sorted(declared), historical_compiler_reads=sorted(observed),
            historical_depfiles=[value for value, _ in deps],
            previous_prerequisites=sorted(previous),
            same_capture_prerequisites=sorted(exact_dependency_ids(review, by_work) - {name}),
        )

    # The constructor contract requires the real native Book provider.
    alert = tasks["cycle20_g08_s20"]
    alert["declared_reads"] = sorted(set(alert["declared_reads"]) | {
        "uc-library/include/presonus/panel/Book.hpp", "uc-library/src/Presonus/Panel/Book.cpp",
    })
    for name in ("cycle20_g07_s08", "cycle20_g07_s09"):
        task = tasks[name]
        review = read(BOOK)["tasks"][name]
        task["declared_reads"] = sorted(set(task["declared_reads"]) | set(source_paths(review)) |
                                        set(review.get("extra_source_reads", [])))
        task["rebound_book_review"] = ref(BOOK)

    seen, phases = set(), []
    for phase_number, row in enumerate(proposal["phases"], 1):
        groups = {logical_name(name): group for name, group in row["groups"].items()}
        assert len(groups) == len(row["groups"]) <= 10
        writers, readers, observed = defaultdict(set), defaultdict(set), defaultdict(set)
        for owner, ordered_tasks in groups.items():
            assert 1 <= len(ordered_tasks) <= 10
            complete = set()
            for name in ordered_tasks:
                assert name not in seen
                seen.add(name)
                task = tasks[name]
                assert task["owner"] == owner and set(task["same_capture_prerequisites"]) <= complete
                complete.add(name)
                for path in task["owned"]:
                    writers[path].add(owner)
                for path in task["declared_reads"]:
                    readers[path].add(owner)
                for path in task["historical_compiler_reads"]:
                    observed[path].add(owner)
                task["canonical_copy_intersections"] = {
                    path: dict(before=copies[path]["before"], after=copies[path]["after"])
                    for path in sorted((set(task["owned"]) | set(task["declared_reads"]) |
                                        set(task["historical_compiler_reads"])) & copies.keys())
                }
        conflicts = [
            dict(path=path, writer=writer, reader=reader)
            for path, owners in sorted(writers.items())
            for writer in owners for reader in sorted(readers[path] - {writer})
        ]
        projected_compiler_conflicts = [
            dict(path=path, writer=writer, reader=reader)
            for path, owners in sorted(writers.items())
            for writer in owners for reader in sorted(observed[path] - {writer})
        ]
        assert not any(len(owners) > 1 for owners in writers.values())
        phases.append(dict(number=phase_number, exact_groups=groups, count=sum(map(len, groups.values())),
                           declared_conflicts=conflicts, projected_compiler_conflicts=projected_compiler_conflicts))
    assert set(tasks) == seen and [row["count"] for row in phases] == [41, 26]

    first, latter = phases
    early = {task for group in first["exact_groups"].values() for task in group}
    late = {task for group in latter["exact_groups"].values() for task in group}
    shared_owner = set(first["exact_groups"]) & set(latter["exact_groups"])
    assert shared_owner == {"cycle20_g05"}
    g05_early = set().union(*(set(tasks[t]["owned"]) for t in first["exact_groups"]["cycle20_g05"]))
    g05_late = set().union(*(set(tasks[t]["owned"]) for t in latter["exact_groups"]["cycle20_g05"]))
    assert not g05_early & g05_late
    cross = []
    for reader in early:
        for writer in late:
            read_set = set(tasks[reader]["declared_reads"])
            old_deps = set(tasks[reader]["historical_compiler_reads"])
            owned = set(tasks[writer]["owned"])
            if read_set & owned or old_deps & owned:
                cross.append(dict(reader=reader, writer=writer, declaration=sorted(read_set & owned),
                                  previous_compiler_observation=sorted(old_deps & owned)))
    catalog, pointer = active_index(ROOT)
    with closing(catalog):
        active = []
        for name, task in sorted(tasks.items()):
            row = catalog.execute(
                "SELECT owner,packet_path FROM work_claims WHERE work_item_id=? AND state='active'",
                (task["upstream_work_id"],),
            ).fetchone()
            if row:
                active.append(dict(task=name, **dict(row)))
    result = P / "ACTUAL07-PRECOPY-EXACT67-TWO-WAVES01.json"
    save(result, dict(
        status="preapproval read-only projection, no capture or claim authorized",
        inputs=dict(projection=ref(PROJECTION), review=ref(REVIEW), tail_inventory=ref(INVENTORY),
                    book_review=ref(BOOK), accepted_copy_plan=ref(COPY)),
        currently_observed_active_claims=active, catalog_pointer=pointer,
        frozen_integration_provider_requirements=statuses["pending_exact_canonical_providers"],
        phases=phases, cross_phase_read_release=sorted(cross,key=lambda x:(x["reader"],x["writer"])),
        same_owner_release={"cycle20_g05":"first wave delivery/source release before second wave activation"},
        withheld=proposal["withheld"], tasks=dict(sorted(tasks.items())), captures=0, claims_acquired=0,
    ))
    print(result, sha(result))
    for phase in phases:
        print(phase["number"], phase["count"], {n:len(v) for n,v in phase["exact_groups"].items()})
        print("Declared or predicted conflict:",phase["declared_conflicts"],phase["projected_compiler_conflicts"])
    print("Cross-scope exact or previous compiler reader/writer pairs",len(cross))
    print("Current active candidates",active)


if __name__ == "__main__":
    main()
