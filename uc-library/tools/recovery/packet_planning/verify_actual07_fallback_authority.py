"""Reverify the independent Actual07 reserve against its registered inputs."""
from collections import defaultdict
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import sys

from project_actual07_partitions import P, S, ROOT, previous_compiler_deps, ref, scoped_proposals
from packet_cycle import read, save, target_of, verify_planned_equivalence, work_targets
from context_runtime import guard, sha
from dedup_work import active_index
from execution_review import batch_validation, checked_digest
from verify_actual07_approval_projection import adapter, verify_record


FALLBACK = P / "ACTUAL07-PRECOPY-INDEPENDENT-FALLBACK01.json"
FALLBACK_DIGEST = "ac3c9d73a08451062286d58fa24c549d55feee07e71a3b50e2fbdd1d6f4ca635"
CHECKER = "uc-library/tests/recovery/cycle20_g01_s12/check.py"
APPLICATION_TARGETS = {
    "cycle20_g03_r20": ("_ZN8Presonus5Panel7ControlD2Ev",),
    "cycle20_g04_s07": (
        "_ZN8Presonus5Mixer19GroupChangeObserverC1EPNS0_16ChannelComponentERNS0_22AutoFilterGroupManagerE",
        "_ZN8Presonus2UC15ServerComponentD2Ev",
    ),
    "cycle20_g10_s20": ("_ZNK8Presonus5Panel7Control12getParameterEv",),
}


def main():
    result = Path(sys.argv[1]).resolve()
    assert result.is_relative_to(P) and not result.exists()
    assert sha(FALLBACK) == FALLBACK_DIGEST
    fallback = read(FALLBACK)
    projection = read(ROOT / fallback["full_projection"]["path"])
    copied = set(fallback["exact_source_paths_from_pending_copy"])
    state_path = S.parent / "graph/actual07/VERIFIED.json"
    receipt = read(state_path)
    active_path = ROOT / "dependency-graph/ACTIVE.json"
    active = read(active_path)
    assert active == receipt["active"] and not receipt["pending_or_unregistered"]
    state = guard(ROOT, active)
    assert sha(ROOT / fallback["full_projection"]["path"]) == fallback["full_projection"]["sha256"]
    gate = {task["task_id"]: task for task in fallback["exact_fallback_requests"]}
    assert len(gate) == 27
    proof, phases, seen = defaultdict(list), [], set()
    catalog, pointer = active_index(ROOT)
    with closing(catalog), adapter.snapshot(ROOT / "uc-library") as view, batch_validation(ROOT):
        for phase in fallback["proposed_phases"]:
            owners, reads, writes = {}, defaultdict(set), defaultdict(set)
            for owner, group in phase["groups"].items():
                assert 1 <= len(group) <= 10
                rows, delivered = [], set()
                for task_id in group:
                    task = projection["tasks"][task_id]
                    assert task["owner"] == owner and task_id not in seen
                    assert set(task["same_capture_prerequisites"]) <= delivered
                    assert not task["previous_prerequisites"]
                    seen.add(task_id)
                    delivered.add(task_id)
                    candidate_path = ROOT / task["proposal"]["path"]
                    assert sha(candidate_path) == task["proposal"]["sha256"]
                    candidate, _ = scoped_proposals(candidate_path)[task_id]
                    targets = work_targets(catalog, candidate, target_of(candidate))
                    work = task["upstream_work_id"]
                    assert candidate["work_item_id"] == work == gate[task_id]["existing_work_item_id"]
                    assert targets == gate[task_id]["targets"]
                    assert not catalog.execute(
                        "SELECT 1 FROM work_claims WHERE work_item_id=? AND state='active'", (work,)
                    ).fetchone(), task_id
                    for target in targets:
                        status = view.c.execute(
                            "SELECT status FROM records WHERE elf=? AND mangled=?",
                            (target["original_elf_sha256"], target["mangled"]),
                        ).fetchone()
                        assert status is None or status["status"] not in {"ready", "pending"}, task_id
                    for name in APPLICATION_TARGETS.get(task_id, ()):
                        for elf in sorted({t["original_elf_sha256"] for t in targets}):
                            proof[task_id].append(verify_record(view, elf, name, task_id))
                    current_deps = list(previous_compiler_deps(task["owned"]))
                    read_paths = set(task["declared_reads"]) | set().union(*(r for _, r in current_deps))
                    assert not (read_paths | set(task["owned"])) & copied, task_id
                    for path in read_paths:
                        reads[path].add(owner)
                    for path in task["owned"]:
                        writes[path].add(owner)
                    existing = [p for p in sorted(read_paths | set(task["owned"])) if (ROOT / p).is_file()]
                    rows.append(dict(
                        task=task_id, work_item_id=work, exact_originals=targets,
                        current_source_hashes={p: checked_digest(ROOT, ROOT / p) for p in existing},
                        compiler_observations=[item for item, _ in current_deps], owned_paths=task["owned"],
                    ))
                owners[owner] = rows
            collisions = {path: sorted(reads[path] | writers) for path, writers in writes.items()
                          if reads[path] - writers or len(writers) > 1}
            if collisions:
                raise ValueError("Refine exact independent phase on observed source overlap: " + repr(collisions))
            phases.append(dict(number=phase["number"], owners=owners, count=sum(map(len, owners.values()))))
    assert seen == set(gate)
    verify_planned_equivalence(list(gate.values()))
    assert read(active_path) == active
    save(result, dict(
        status="read-only exact independent scope for separate Root approval if official admission blocks",
        observed_utc=datetime.now(timezone.utc).isoformat(),
        active=active, verified_registration=ref(state_path), source_guard_paths=len(state["files"]),
        checker_graph_membership=dict(file_bound=CHECKER in state["files"],
                                      source_inventory=CHECKER in state["source_inventory"]),
        phases=phases, exact_existing_application_proofs=dict(proof), original_read_only_reserve=ref(FALLBACK),
        held=fallback["held"], catalog_pointer=pointer,
        prepared_or_claimed=False,
    ))
    print(result, sha(result), [phase["count"] for phase in phases])


if __name__ == "__main__":
    main()
