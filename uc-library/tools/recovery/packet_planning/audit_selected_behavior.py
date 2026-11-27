"""Audit direct selected application dependencies before publishing sequenced scopes."""
import argparse
from collections import defaultdict
from pathlib import Path

from packet_cycle import ROOT, read, reference, save
from context_runtime import sha

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("batch", type=Path)
parser.add_argument("manifest", type=Path)
parser.add_argument("output", type=Path)
args = parser.parse_args()
manifest = read(args.manifest)
frozen = read(args.batch / "FROZEN.json")
if frozen["manifest_sha256"] != sha(args.manifest):
    raise ValueError("Actual frozen task manifest changed")
contexts, requests, owner, sequence = {}, {}, {}, {}
native_roots = defaultdict(set)
for group in manifest["groups"]:
    lane = group["task_name"]
    for index, name in enumerate(group["execution_order"]):
        packet = ROOT / name
        task = packet.name
        context = read(packet / "context.json")
        if (context["task_id"] != task or context["task_sha256"] != sha(packet / "request.json")
                or context["generation_sha256"] != frozen["inputs"]["active"]["state_sha256"]):
            raise ValueError("Selected input generation or exact owner diverged for " + task)
        contexts[task] = context
        requests[task] = read(packet / "request.json")
        owner[task] = lane
        sequence[task] = index
        for root in context["native_context"]["roots"]:
            native_roots[root].add(task)

actual, unresolved = [], set()
for task, context in contexts.items():
    target_roots = set(context["native_context"]["roots"])
    for edge in context["native_context"]["edges"]:
        if (edge["src"] not in target_roots or not edge["kind"] in {"ELF_CALLS", "ELF_TAIL_BRANCH"}
                or edge["dst"] not in native_roots):
            continue
        for destination in sorted(native_roots[edge["dst"]] - {task}):
            work = requests[destination]["work_binding"]["work_item_id"]
            provided_in_order = (owner[task] == owner[destination] and sequence[destination] < sequence[task]
                                 and work in requests[task].get("included_dependency_work", []))
            actual.append(dict(caller=task, provider=destination, site=edge["site"], kind=edge["kind"],
                               target=edge["dst"], provided_in_order=provided_in_order))
            if not provided_in_order:
                unresolved.add(task)

save(args.output, {
    "manifest": reference(args.manifest, "review_record", "Exact frozen task composition"),
    "snapshot_sha256": sha(args.batch / "SNAPSHOT.json"),
    "direct_exact_selected_provider_edges": actual,
    "direct_unavailable_behavior": sorted(unresolved),
    "scope": "Selected primary native entry/call identity only, with distinct writer ownership. Indirect and other typed obligations still require individual contract review.",
})
print(len(actual), "exact native edges among selected tasks;", len(unresolved), "need external or reordered provider review")
