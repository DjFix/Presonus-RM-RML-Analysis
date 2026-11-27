"""Combine already reviewed unclaimed wave inputs without changing task requests."""
import argparse
from collections import defaultdict
from pathlib import Path
import shlex
from packet_cycle import CYCLE, ROOT, check_parked_assignment, check_vendor_source_route, read, rel, save
from execution_review import batch_validation, checked_digest
from reconstruction_contract import validate_request

cli = argparse.ArgumentParser(description=__doc__)
cli.add_argument("--plans", type=Path, nargs="+", required=True)
cli.add_argument("--manifest", type=Path, required=True)
cli.add_argument("--batch", type=Path, required=True)
cli.add_argument("--include", nargs="+", help="Exact task IDs of an independently eligible subset")
cli.add_argument("--known-read-set", type=Path, help="Review JSON mapping owner lane to known compiler/input paths")
cli.add_argument("--reuse-snapshot", type=Path)
args = cli.parse_args()
for path in (args.manifest, args.batch):
    if not path.resolve().is_relative_to(CYCLE) or path.exists():
        cli.error("Choose new output paths within the cycle")
groups, requests, origins = [], [], []
writers, readers, ids, originals, work = {}, defaultdict(set), set(), set(), set()
seen_lanes = set()
include = set(args.include or [])
included_dependencies = {}
declared = {} if args.known_read_set is None else read(args.known_read_set)
with batch_validation(ROOT):
    for folder in args.plans:
        path = folder / "PREFREEZE.json"
        audit = read(path)
        if (ROOT / audit["planned_output"] / "FROZEN.json").exists():
            raise ValueError(f"Input already frozen: {folder}")
        for name, expected in [(audit["review"], audit["review_sha256"]),
                               (audit["inventory"], audit["inventory_sha256"]),
                               (audit["tasks"], audit["tasks_sha256"])]:
            if checked_digest(ROOT, ROOT / name) != expected:
                raise ValueError(f"Planning input changed: {name}")
        origins.append({"path": rel(path), "sha256": checked_digest(ROOT, path)})
        source = read(ROOT / audit["tasks"])
        source_groups = {}
        for group in source["groups"]:
            owner = group["task_name"]
            if owner in seen_lanes:
                raise ValueError(f"Duplicate lane: {owner}")
            seen_lanes.add(owner)
            readers[owner].update(declared.get(owner, []))
            packet_paths = [rel(args.batch / "packets" / Path(p).name) for p in group["packets"]
                            if not include or Path(p).name in include]
            if not packet_paths:
                continue
            source_groups[owner] = dict(group, packets=packet_paths, execution_order=packet_paths)
        groups.extend(source_groups.values())
        for item in audit["audits"]:
            task_path = ROOT / item["task"]
            if checked_digest(ROOT, task_path) != item["task_sha256"]:
                raise ValueError(f"Reviewed task changed: {item['task']}")
            task = read(task_path)
            if include and task["task_id"] not in include:
                continue
            validate_request(ROOT, task)
            owner = item["owner"]
            for path, expected in task["declared_source_hashes"].items():
                if checked_digest(ROOT, ROOT / path) != expected:
                    raise ValueError(f"Declared source changed: {path}")
                readers[owner].add(path)
            for path in task["owned_files"]:
                if writers.setdefault(path, owner) != owner:
                    raise ValueError(f"Cross-lane write conflict: {path}")
            check_parked_assignment(task["task_id"], task["existing_work_item_id"], task["targets"])
            for values, value in [(ids, task["task_id"]), (work, task["existing_work_item_id"])]:
                if value in values:
                    raise ValueError(f"Duplicate task/work: {value}")
                values.add(value)
            for target in task["targets"]:
                check_vendor_source_route(target)
                identity = target["original_elf_sha256"], target["mangled"]
                if identity in originals:
                    raise ValueError(f"Duplicate original: {identity}")
                originals.add(identity)
            included_dependencies[task["task_id"]] = set(task.get("included_dependency_work", []))
            requests.append(item["task"])
    if include and ids != include:
        raise ValueError("Requested subset differs from reviewed packet IDs")
    for task_id, needs in included_dependencies.items():
        if not needs <= work:
            raise ValueError(f"Included provider omitted from subset: {task_id}")
    conflicts = sorted((owner, writers[path], path) for owner, paths in readers.items()
                       for path in paths if path in writers and writers[path] != owner)
    if conflicts:
        raise ValueError(f"Cross-lane observed/declared read/write conflict: {conflicts}")
    manifest = {"tasks": requests, "groups": groups, "prefreeze_provenance": origins}
    full = len(groups) == 10 and all(len(group["packets"]) == 20 for group in groups)
    if not full:
        if any(len(group["packets"]) > 10 for group in groups):
            raise ValueError("Maintained rolling publication caps each compatible group at ten packets")
        manifest.update(allow_smaller=True, smaller_batch_authorization=
                        "Root approved combining compatible eligible lanes into one shared snapshot.")
    save(args.manifest, manifest)
argv = ["uc-library/.venv/bin/python", "uc-library/tools/recovery/select_context.py", "batch-prepare",
        "--tasks", rel(args.manifest), "--out", rel(args.batch), "--jobs", "auto"]
if args.reuse_snapshot:
    argv += ["--reuse-snapshot", rel(args.reuse_snapshot)]
print(shlex.join(argv))
