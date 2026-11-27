"""Audit exact selected work and physical ordering between both Actual07 waves."""
from collections import defaultdict
from pathlib import Path
import sys

from packet_cycle import CYCLE, ROOT, read, reference, save
from context_runtime import sha


P = CYCLE / "packeting"
GENERATION = "e82bb46c1ad32716918acda0b0cb8af4c8239982e64d09712fd70e0ef6e4a3c2"


def selected(wave):
    prefix = f"actual07-authorized-wave{wave:02}"
    manifest_path = P / (prefix + "-plans02/TASKS.json")
    batch = P / (prefix + "-capture02")
    assert read(batch / "FROZEN.json")["manifest_sha256"] == sha(manifest_path)
    manifest = read(manifest_path)
    rows = {}
    for group in manifest["groups"]:
        for order, relative in enumerate(group["execution_order"]):
            packet = ROOT / relative
            request_file = packet / "request.json"
            context_file = packet / "context.json"
            request, context = read(request_file), read(context_file)
            assert context["task_sha256"] == sha(request_file)
            assert context["generation_sha256"] == GENERATION and context["task_id"] == packet.name
            rows[packet.name] = dict(
                owner=group["task_name"],order=order,wave=wave,request=request,context=context,
                reads=set(context["selected_file_sha256"]),writes=set(request["owned_files"]),
                input=reference(context_file,"review_record","Exact selected context"),
            )
    return rows, reference(batch / "SNAPSHOT.json", "review_record", "Exact immutable wave inputs")


def main():
    output = Path(sys.argv[1]).resolve()
    assert output.is_relative_to(P)
    earlier, first_snapshot = selected(1)
    later, second_snapshot = selected(2)
    assert len(earlier) == 41 and len(later) == 26 and not earlier.keys() & later.keys()
    all_tasks = {**earlier, **later}
    roots = defaultdict(set)
    for task, row in all_tasks.items():
        for root in row["context"]["native_context"]["roots"]:
            roots[root].add(task)
    actual_edges, missing_edges = [], []
    for caller, row in all_tasks.items():
        native = row["context"]["native_context"]
        for edge in native["edges"]:
            if edge["kind"] not in {"ELF_CALLS","ELF_TAIL_BRANCH"} or edge["src"] not in native["roots"]:
                continue
            for provider in roots[edge["dst"]] - {caller}:
                dependency = all_tasks[provider]
                work_id = dependency["request"]["work_binding"]["work_item_id"]
                within_order = (
                    row["wave"] == dependency["wave"] and row["owner"] == dependency["owner"]
                    and dependency["order"] < row["order"] and work_id in row["request"]["included_dependency_work"]
                )
                relation = dict(caller=caller,provider=provider,site=edge["site"],kind=edge["kind"],
                                within_approved_order=within_order)
                actual_edges.append(relation)
                if not within_order:
                    missing_edges.append(relation)
    read_releases = []
    for original_name, first in earlier.items():
        for next_name, second in later.items():
            forward = first["reads"] & second["writes"]
            backward = first["writes"] & second["reads"]
            both = first["writes"] & second["writes"]
            if forward or backward or both:
                read_releases.append(dict(
                    prior=original_name, prior_owner=first["owner"], next=next_name, next_owner=second["owner"],
                    prior_read_next_write=sorted(forward), prior_write_next_read=sorted(backward),
                    writes_overlap=sorted(both),
                ))
    save(output, dict(
        generation=GENERATION,
        snapshots=[first_snapshot,second_snapshot],
        selected_count=len(all_tasks),
        selected_contexts={task:r["input"] for task,r in all_tasks.items()},
        exact_direct_native_edges=actual_edges,
        unresolved_native_edges=missing_edges,
        cross_wave_source_release_requirements=read_releases,
        scope="Current selected native call and canonical path observation. Worker binder must separately verify physical captures and dependency release.",
    ))
    print(len(actual_edges),len(missing_edges),len(read_releases),sha(output))
    if missing_edges:
        raise ValueError("A selected cross-owner behavior dependency is not covered by the approved native ordering")


if __name__ == "__main__":
    main()
