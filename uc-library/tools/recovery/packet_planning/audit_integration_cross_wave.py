"""Bind exact packet or physical read overlaps to the complete staged canonical write plan."""
import argparse
from pathlib import Path

from packet_cycle import ROOT, read, reference, rel, save
from context_runtime import sha

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--manifest", required=True, type=Path)
write_input = parser.add_mutually_exclusive_group(required=True)
write_input.add_argument("--integration", type=Path)
write_input.add_argument("--accepted-plan", type=Path)
write_input.add_argument("--repair-provenance", type=Path)
parser.add_argument("--out", required=True, type=Path)
parser.add_argument("--physical", nargs="+", type=Path)
args = parser.parse_args()
if args.repair_provenance:
    plan = paths = args.repair_provenance
    repair = read(plan)
    if sha(ROOT / repair["patch"]["path"]) != repair["patch"]["sha256"]:
        raise ValueError("Exact guarded repair patch changed")
    files = set()
    for item in repair["previous_files"]:
        if (sha(ROOT / item["archive"]) != item["before"] or
                sha(ROOT / item["validated_candidate"]) != item["after"] or
                sha(ROOT / item["path"]) != item["before"]):
            raise ValueError("Exact current repair inputs changed: " + item["path"])
        files.add(item["path"])
elif args.accepted_plan:
    plan = paths = args.accepted_plan
    accepted = read(plan)
    files = {item["path"] for item in accepted["files"] + accepted["patch_files"]}
else:
    plan = args.integration / "PLAN.json"
    paths = args.integration / "VERSIONABLE_PATHS.json"
    files = {item["path"] for item in read(plan)["files"]} | set(read(paths)["paths"])

receipts = []
grouped = read(args.manifest)["groups"]
expected = {group["task_name"] for group in grouped}
for group in grouped:
    owner = group["task_name"]
    reads, writes, context_seals = set(), set(), {}
    for name in group["packets"]:
        packet = ROOT / name
        context = read(packet / "context.json")
        request = read(packet / "request.json")
        if context["task_sha256"] != sha(packet / "request.json"):
            raise ValueError("Exact selected request claims changed")
        context_seals[name] = sha(packet / "context.json")
        reads.update(context["selected_file_sha256"])
        writes.update(request["owned_files"])
    receipts.append(dict(owner=owner, read_overlap=sorted(reads & files), write_overlap=sorted(writes & files),
                         selected_reads=len(reads), context_seals=context_seals))

physical = []
if args.physical:
    for path in args.physical:
        row = read(path)
        if not row["applied"]:
            raise ValueError("Exact physical read capture did not apply")
        for assignment in row["assignments"]:
            lane = assignment["lane"]
            readmap = Path(assignment["read_inputs"])
            if lane not in expected or row["input_seals"][str(readmap)] != sha(readmap):
                raise ValueError("Unknown or changed captured workspace reads")
            writable = assignment.get("owned_files", [])
            physical.append(dict(owner=lane, read_overlap=sorted(set(read(readmap)) & files),
                                 write_overlap=sorted(set(writable) & files), receipt=rel(path),
                                 receipt_sha256=sha(path), readmap=rel(readmap), readmap_sha256=sha(readmap)))
    if {record["owner"] for record in physical} != expected:
        raise ValueError("Capture receipts must cover every exact group")
save(args.out, dict(manifest=reference(args.manifest,"review_record","Exact production task wave"),
                    integration_copy=reference(plan,"review_record","Exact canonical copy producer plan"),
                    integration_writes=reference(paths,"review_record","Complete intended canonical versionable writes"),
                    canonical_write_count=len(files), selected=receipts, physical=physical,
                    actual_reads=bool(physical)))
for item in physical or receipts:
    if item["read_overlap"] or item["write_overlap"]:
        print(item["owner"], item["read_overlap"], item["write_overlap"])
print(len(receipts), "selected owners;", len(physical), "exact physical read maps")
