"""Build the newly approved actual06 wave from exact, immutable reviewed inputs."""
from pathlib import Path

from packet_cycle import (
    CYCLE,
    ROOT,
    check_vendor_source_route,
    materialize,
    read,
    reference,
    rel,
    save,
    validate_request,
    verify_planned_equivalence,
)
from context_batch import validate_tasks
from context_runtime import guard, sha
from execution_review import batch_validation

PACKETING = CYCLE / "packeting"
SELECTION = CYCLE / "selection"
APPROVAL_SHA256 = "48b30db65c7025255aa1a19877df792dec4495e167e617a97da83f3536f741ee"
APPROVAL = PACKETING / "ACTUAL06-VERIFIED-PROPOSED42-AUTHORITY-REVIEW01.json"
GENERATION = "4e5e161f560674b3e63d644434c8df2c6ccf5c4c775d13d7171a5fd47cb4c329"
BATCH = PACKETING / "actual06-first-capture01"
TYPED = PACKETING / "actual05-typed-remainder-draft09.json"
OUTPUT = PACKETING / "actual06-authorized42-plans01"
INVENTORY_DEFINITION = PACKETING / "actual06-authorized42-inventory01.json"
REVIEW_DEFINITION = PACKETING / "actual06-authorized42-review01.json"
FINAL = PACKETING / "actual06-authorized42-TASKS.json"
AUTHORIZATION = (
    "Root explicitly approved allow_smaller and production_continuation for the "
    f"exact Actual06 inventory {APPROVAL_SHA256} on generation {GENERATION}. "
    "The 42 implementation assignments are ready under eight owners within "
    "the rolling cap. G04 must release Book reads before G07 writes. G07 and "
    "G10 must release Element and TextEntry reads before G06 writes."
)


def renewed_site(value, changes):
    if isinstance(value, dict):
        result = {key: renewed_site(item, changes) for key, item in value.items()}
        change = changes.get(value.get("path", ""))
        if change and result.get("sha256") == change["previous_draft"]:
            result["sha256"] = change["current_canonical"]
        return result
    if isinstance(value, list):
        return [renewed_site(item, changes) for item in value]
    return value


def new_local_review(row):
    candidate = row["candidate"]
    assert not row["boundaries"] and not candidate.get("accepted_predecessor_task_ids")
    native = candidate["native_lifecycle_observation"]
    assert sha(ROOT / native["path"]) == native["sha256"]
    evidence = [dict(native, kind="review_record", scope="Exact original offline behavior")]
    declared_reads = []
    for path, digest in candidate.get("frozen_provider_files", {}).items():
        assert sha(ROOT / path) == digest
        declared_reads.append(path)
        evidence.append(reference(ROOT / path, "cpp_declaration", "Current typed source provider"))
    objective = candidate["bounded_selection_work"]
    work = dict(
        objective=objective,
        oracle_plan=(
            "Execute exact original application ranges independently and compare the "
            "portable canonical typed cases. Keep the bound local state and genuine "
            "provider contract; do not assign companion ABI or unresolved return credit."
        ),
        owned_files=row["production"],
    )
    return dict(
        target=row["target"],
        work_item_id=candidate["work_item_id"],
        native_evidence_sha256=row["native"]["sha256"],
        reviewer="Actual06 exact native and source evidence reviewed by selection and Root",
        namespace=candidate["scope"].rpartition("::")[0] or candidate["scope"],
        objective=objective,
        domain="Offline application-only typed behavior in the exact independently verified source scope.",
        requirements={
            key: dict(status="bounded_work", reason=objective, work=work, evidence=evidence)
            for key in ("declarations", "state", "lifecycle", "providers")
        },
        execution_boundaries={},
        extra_source_reads=declared_reads,
    )


def exact_rows(path):
    return {row["task_id"]: row for lane in read(path)["lanes"] for row in lane["tasks"]}


def main():
    assert all(not path.exists() for path in (BATCH, OUTPUT, INVENTORY_DEFINITION, REVIEW_DEFINITION, FINAL))
    assert sha(APPROVAL) == APPROVAL_SHA256
    approved = read(APPROVAL)
    active = read(ROOT / "dependency-graph/ACTIVE.json")
    assert active == approved["verified_generation"] and active["state_sha256"] == GENERATION
    guard(ROOT, active)
    candidate_pointer = approved["exact_candidate_inventory"]
    candidate_file = ROOT / candidate_pointer["path"]
    assert sha(candidate_file) == candidate_pointer["sha256"]
    candidate = read(candidate_file)
    inventory_path = PACKETING / "actual06-followon-first27-inventory01.json"
    inventory = read(inventory_path)
    rows = exact_rows(inventory_path)
    rows.update(exact_rows(PACKETING / "actual06-additions-and-corrected-ui08-inventory01/INVENTORY.json"))
    meter_id = "cycle20_g02_s07"
    rows[meter_id] = exact_rows(PACKETING / "actual06-additional-three-draftinventory01/INVENTORY.json")[meter_id]
    reviews = read(PACKETING / "actual06-followon-first27-review01.json")["tasks"]
    reviews[meter_id] = read(SELECTION / "ACTUAL06_G02_S07_TABLE_EXACT_REVIEW01.json")["tasks"][meter_id]
    for task_id in {
        "cycle20_g01_r06", "cycle20_g01_r10", "cycle20_g02_r02",
        "cycle20_g01_s13", "cycle20_g01_s14",
        "cycle20_g01_s17", "cycle20_g01_s18", "cycle20_g01_s19",
    }:
        reviews[task_id] = new_local_review(rows[task_id])
    renewal = candidate["renewal_semantic_evidence"]
    assert sha(ROOT / renewal["path"]) == renewal["sha256"]
    renewal_ref = dict(renewal, kind="review_record", scope="Exact verified post-copy source semantics")
    for task_id, changed in candidate["changed_draft_source_hashes"].items():
        reviews[task_id] = renewed_site(reviews[task_id], changed)
        for requirement in reviews[task_id]["requirements"].values():
            requirement["evidence"].append(renewal_ref)
        for path, delta in changed.items():
            assert sha(ROOT / path) == delta["current_canonical"]

    typed = read(TYPED)
    typed_by_id = {Path(path).stem: path for path in typed["tasks"]}
    approved_groups = approved["work_groups"]
    fresh_inventory = [
        dict(name=g["owner"], tasks=[rows[task_id] for task_id in g["exact_execution_order"]
                                    if task_id not in typed_by_id])
        for g in approved_groups
    ]
    inventory["lanes"] = [lane for lane in fresh_inventory if lane["tasks"]]
    assert sum(len(group["tasks"]) for group in inventory["lanes"]) == 33
    assert set(reviews) == set(rows)
    save(INVENTORY_DEFINITION, inventory)
    save(REVIEW_DEFINITION, dict(
        tasks=reviews,
        smaller_batch_authorization=AUTHORIZATION,
        production_continuation=AUTHORIZATION,
        reviewed_authority=dict(path=rel(APPROVAL), sha256=APPROVAL_SHA256),
    ))
    materialize(INVENTORY_DEFINITION, REVIEW_DEFINITION, OUTPUT, BATCH)

    fresh = read(OUTPUT / "TASKS.json")
    requests = {**typed_by_id, **{Path(path).stem: path for path in fresh["tasks"]}}
    approved_tasks = {row["task_id"]: row for group in candidate["exact_candidate_groups"].values() for row in group}
    groups, ordered_paths = [], []
    for planned in approved_groups:
        order = planned["exact_execution_order"]
        paths = [rel(BATCH / "packets" / task_id) for task_id in order]
        groups.append(dict(
            task_name=planned["owner"],
            packets=paths,
            execution_order=paths,
            scope_reason="Actual06 exact Root-approved same-owner source and native scope",
        ))
        ordered_paths.extend(requests[task_id] for task_id in order)
    all_requests = [read(ROOT / path) for path in ordered_paths]
    assert len(requests) == len(all_requests) == len(approved_tasks) == 42
    assert sum(len(task["targets"]) for task in all_requests) == 83
    with batch_validation(ROOT):
        for task in all_requests:
            prepared = approved_tasks[task["task_id"]]
            assert task["targets"] == prepared["exact_originals"]
            assert sorted(task["owned_files"]) == sorted(prepared["owned_files"])
            assert task["existing_work_item_id"] == prepared["unique_work_item"]
            for target in task["targets"]:
                check_vendor_source_route(target)
            for path, digest in task["declared_source_hashes"].items():
                assert sha(ROOT / path) == digest
            assert task["declared_source_hashes"] == prepared["source_read_sha256"]
            validate_request(ROOT, task)
    validate_tasks(all_requests, groups)
    verify_planned_equivalence(all_requests)
    save(FINAL, dict(
        tasks=ordered_paths,
        groups=groups,
        allow_smaller=True,
        smaller_batch_authorization=AUTHORIZATION,
        production_continuation=AUTHORIZATION,
        authority=dict(path=rel(APPROVAL), sha256=APPROVAL_SHA256),
    ))
    print(f"42 exact working packets, 83 original ranges, eight owners: {rel(FINAL)} {sha(FINAL)}")


if __name__ == "__main__":
    main()
