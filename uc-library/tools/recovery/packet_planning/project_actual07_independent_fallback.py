"""Stage the exact independent Actual07 reserve and its retained dependency ledger."""
from collections import defaultdict
from contextlib import closing
from datetime import datetime, timezone

from project_actual07_partitions import P, S, ROOT, previous_compiler_deps, ref, scoped_proposals
from packet_cycle import read, save, target_of, verify_planned_equivalence, work_targets
from dedup_work import active_index
from context_runtime import sha


def main():
    projection_path = P / "ACTUAL07-PRECOPY-EXACT67-TWO-WAVES01.json"
    projection = read(projection_path)
    copy_file = ROOT / projection["inputs"]["accepted_copy_plan"]["path"]
    assert sha(copy_file) == projection["inputs"]["accepted_copy_plan"]["sha256"]
    copy = read(copy_file)
    source_copies = {
        row["path"] for row in copy["files"] + copy["patch_files"]
        if row.get("before") != row.get("after")
    }
    pending = {row["task"] for row in copy["tasks"]}
    tasks = projection["tasks"]
    held = {}
    projected_reads = {}
    for task_id, task in tasks.items():
        current_deps = list(previous_compiler_deps(task["owned"]))
        compiler_reads = set(task["historical_compiler_reads"]) | set().union(*(r for _, r in current_deps))
        declared = set(task["declared_reads"])
        owned = set(task["owned"])
        projected_reads[task_id] = declared | compiler_reads
        predecessor = set(task["previous_prerequisites"]) & pending
        affected = (declared | compiler_reads | owned) & source_copies
        if predecessor or affected:
            held[task_id] = dict(
                pending_canonical_providers=sorted(predecessor),
                pending_copy_owned_paths=sorted(affected & owned),
                pending_copy_declared_reads=sorted(affected & declared),
                pending_copy_compiler_reads=sorted(affected & compiler_reads),
                included_pending_work=[],
                release="Verify exact normal canonical admission and final copied content before preparing.",
            )
    while True:
        downstream = {
            name: sorted(set(task["same_capture_prerequisites"]) & held.keys())
            for name, task in tasks.items() if name not in held
            and set(task["same_capture_prerequisites"]) & held.keys()
        }
        if not downstream:
            break
        for name, dependencies in downstream.items():
            held[name] = dict(
                pending_canonical_providers=[], pending_copy_owned_paths=[], pending_copy_declared_reads=[],
                pending_copy_compiler_reads=[], included_pending_work=dependencies,
                release="Keep exact same-owner provider in the future packet scope and order it first.",
            )

    phases, candidate = [], set()
    for phase in projection["phases"]:
        groups, owned_paths, read_paths = {}, defaultdict(set), defaultdict(set)
        for owner, packet_order in phase["exact_groups"].items():
            order = [name for name in packet_order if name not in held]
            if not order:
                continue
            groups.setdefault(owner, []).extend(order)
            for name in order:
                for path in tasks[name]["owned"]:
                    owned_paths[path].add(owner)
                for path in projected_reads[name]:
                    read_paths[path].add(owner)
        overlaps = [
            dict(path=path, writer=writer, reader=reader)
            for path, owners in sorted(owned_paths.items())
            for writer in owners for reader in sorted(read_paths[path] - {writer})
        ]
        assert not any(len(owners) > 1 for owners in owned_paths.values())
        assert len(groups) <= 10 and all(len(members) <= 10 for members in groups.values())
        for owner, members in groups.items():
            prior = set()
            for name in members:
                required = set(tasks[name]["same_capture_prerequisites"])
                assert required <= prior and tasks[name]["owner"] == owner
                assert name not in candidate
                candidate.add(name)
                prior.add(name)
        phases.append(dict(number=phase["number"], groups=groups, planned_read_write_conflicts=overlaps))
    assert candidate.isdisjoint(held) and set(tasks) == candidate | held.keys()
    database, pointer = active_index(ROOT)
    requests = []
    with closing(database):
        for name in sorted(candidate):
            entry = tasks[name]
            proposal, _ = scoped_proposals(ROOT / entry["proposal"]["path"])[name]
            exact = work_targets(database, proposal, target_of(proposal))
            assert not database.execute(
                "SELECT 1 FROM work_claims WHERE work_item_id=? AND state='active'",
                (entry["upstream_work_id"],),
            ).fetchone(), name
            requests.append(dict(task_id=name, targets=exact, existing_work_item_id=entry["upstream_work_id"]))
    verify_planned_equivalence(requests)
    output = P / "ACTUAL07-PRECOPY-INDEPENDENT-FALLBACK01.json"
    save(output, dict(
        status="read-only reserve. Applicable only if normal live admission blocks and Actual07 stays fresh.",
        observed_utc=datetime.now(timezone.utc).isoformat(),
        copied_actual06_plan=ref(copy_file), full_projection=ref(projection_path),
        exact_source_paths_from_pending_copy=sorted(source_copies),
        proposed_phases=phases,
        held=held, exact_fallback_requests=requests, catalog_pointer=pointer,
        graph_or_claim_writes=0, provider_independence_not_dispatch_authority=True,
    ))
    print(output,sha(output),len(candidate),len(held))
    for phase in phases:
        print(phase["number"], {owner:len(group) for owner,group in phase["groups"].items()},
              phase["planned_read_write_conflicts"])


if __name__ == "__main__":
    main()
