"""Compose already reviewed compatible tasks for one exact maintained freeze."""
import argparse
from collections import defaultdict
from pathlib import Path

from packet_cycle import CYCLE, PRODUCTION_CONTINUATION, ROOT, check_vendor_source_route, read, reference, rel, save, validate_request, verify_planned_equivalence
from context_batch import validate_tasks

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--manifests", nargs="+", required=True, type=Path)
parser.add_argument("--output", required=True, type=Path)
parser.add_argument("--batch", required=True, type=Path)
parser.add_argument("--sequential-scopes", type=Path,
                    help="Root-approved exact owner overlaps to separate by actual selected scope")
args = parser.parse_args()
for path in (*args.manifests, args.output, args.batch):
    if not path.resolve().is_relative_to(CYCLE):
        raise ValueError("Use exact current cycle paths")
if args.output.exists() or args.batch.exists():
    raise ValueError("Use a fresh wave output and batch directory")

tasks, groups = [], {}
provenance = []
for manifest_path in args.manifests:
    manifest = read(manifest_path)
    provenance.append(reference(manifest_path, "review_record", "Exact input production wave manifest"))
    tasks.extend(manifest["tasks"])
    for group in manifest["groups"]:
        name = group["task_name"]
        if name in groups:
            raise ValueError("Different fragments claim same group without explicit provider ordering: " + name)
        groups[name] = {
            **group,
            **{key: [rel(args.batch / "packets" / Path(path).name) for path in group[key]]
               for key in ("packets", "execution_order")},
        }

requests = [read(ROOT / path) for path in tasks]
validate_tasks(requests, list(groups.values()))
verify_planned_equivalence(requests)
by_id = {item["task_id"]: item for item in requests}
writers, readers = defaultdict(set), defaultdict(set)
for name, group in groups.items():
    if len(group["packets"]) > 10:
        raise ValueError("Small grouped operator maximum exceeded for " + name)
    prior = set()
    for packet in group["execution_order"]:
        request = by_id[Path(packet).name]
        for target in request["targets"]:
            check_vendor_source_route(target)
        dependencies = set(request.get("included_dependency_work", []))
        if not dependencies <= prior | {request["existing_work_item_id"]}:
            raise ValueError("Exact included provider must be in same owner and appear first")
        prior.add(request["existing_work_item_id"])
        validate_request(ROOT, request)
        for path in request["owned_files"]:
            writers[path].add(name)
        for path in request.get("declared_source_dependencies", []):
            readers[path].add(name)
actual_overlap = {(path, writer, reader) for path, owners in writers.items() for writer in owners
                  for reader in readers[path] - owners}
if args.sequential_scopes is None:
    if actual_overlap:
        raise ValueError("Declared overlap requires separately approved sequential scopes: " + repr(actual_overlap))
else:
    if not args.sequential_scopes.resolve().is_relative_to(CYCLE):
        raise ValueError("Sequential scope approval must be cycle-local")
    approval = read(args.sequential_scopes)
    planned = {(row["path"], row["write_owner"], row["read_owner"]) for row in approval["known_cross_scope"]}
    if actual_overlap != planned or not approval["approval"]:
        raise ValueError("Exact declared scope overlap differs from approved sequencing: " + repr(actual_overlap))
    provenance.append(reference(args.sequential_scopes, "review_record", "Root-approved known overlap and execution order. Maintained actual conflict check still mandatory."))

output_manifest = {
    "tasks": tasks,
    "groups": list(groups.values()),
    "allow_smaller": True,
    "smaller_batch_authorization": "Root authorized approved exact independent rolling scopes and guarded same-owner continuations.",
    "composition_provenance": provenance,
}
if any(len(request["targets"]) > 1 for request in requests):
    output_manifest["production_continuation"] = PRODUCTION_CONTINUATION
save(args.output, output_manifest)
print(f"{len(requests)} exact reviewed tasks and {len(groups)} disjoint write owners")
