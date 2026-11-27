"""Plan compatible exact-owner dispatch phases from the one Actual06 selection."""
from itertools import combinations
from pathlib import Path
import sys

from packet_cycle import ROOT, read, reference, save
from context_runtime import sha


def main():
    manifest_path, batch, behavior_path, output = map(Path, sys.argv[1:])
    manifest = read(manifest_path)
    behavior = read(behavior_path)
    if behavior["direct_unavailable_behavior"]:
        raise ValueError("Unbound exact behavior dependencies need review before any partition")

    # These three directional barriers belong to the exact approved inventory.
    earlier_owners = {
        "cycle20_g07": {"cycle20_g04"},
        "cycle20_g06": {"cycle20_g07", "cycle20_g10"},
    }
    reads, writes, task_seals = {}, {}, {}
    groups = {}
    for group in manifest["groups"]:
        owner = group["task_name"]
        owners_reads, owners_writes = set(), set()
        groups[owner] = group["execution_order"]
        local_work = set()
        for path in group["execution_order"]:
            packet = ROOT / path
            context_path, request_path = packet / "context.json", packet / "request.json"
            context, request = read(context_path), read(request_path)
            work = request["work_binding"]["work_item_id"]
            if (not packet.is_relative_to(batch.resolve() / "packets")
                    or context["task_id"] != packet.name or context["task_sha256"] != sha(request_path)
                    or set(request.get("included_dependency_work", [])) - local_work - {work}):
                raise ValueError("Captured scope, request or provider order changed: " + path)
            local_work.add(work)
            owners_reads.update(context["selected_file_sha256"])
            owners_writes.update(request["owned_files"])
            task_seals[path] = sha(context_path)
        reads[owner], writes[owner] = owners_reads, owners_writes

    conflicts = {}
    for a, b in combinations(sorted(groups), 2):
        paths = (writes[a] & reads[b]) | (writes[b] & reads[a]) | (writes[a] & writes[b])
        if paths:
            conflicts[a, b] = sorted(paths)

    remaining, released, phases = set(groups), set(), []
    while remaining:
        runnable = sorted(owner for owner in remaining if earlier_owners.get(owner, set()) <= released)
        valid = [
            subset
            for n in range(1, len(runnable) + 1)
            for subset in combinations(runnable, n)
            if not any(pair in conflicts for pair in combinations(subset, 2))
        ]
        owners = max(valid, key=lambda group: (sum(len(groups[owner]) for owner in group), len(group), group))
        packet_paths = [path for owner in owners for path in groups[owner]]
        omitted = sorted(Path(path).name for owner, paths in groups.items() if owner not in owners for path in paths)
        phases.append(dict(
            phase=f"scoped{len(phases) + 1:02}",
            owners=owners,
            packets=packet_paths,
            omitted=omitted,
            predecessor_releases={
                owner: sorted(earlier_owners[owner]) for owner in owners if owner in earlier_owners
            },
        ))
        remaining.difference_update(owners)
        released.update(owners)

    save(output, dict(
        manifest=reference(manifest_path, "review_record", "Approved exact Actual06 task manifest"),
        snapshot=reference(batch / "SNAPSHOT.json", "review_record", "Single captured actual06 input"),
        behavior=reference(behavior_path, "review_record", "Exact native provider availability"),
        context_sha256=task_seals,
        conflicts=[dict(first=a, second=b, paths=paths) for (a, b), paths in conflicts.items()],
        phases=phases,
        scope_only=True,
    ))
    for phase in phases:
        print(phase["phase"], len(phase["packets"]), ",".join(phase["owners"]))


if __name__ == "__main__":
    main()
