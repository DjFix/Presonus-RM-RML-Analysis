"""Observe exact failed unopened TextEntry task ownership and prepare maintained release requests."""
from datetime import datetime, timezone
import os
from pathlib import Path
import sys

from packet_cycle import CYCLE, ROOT, read, reference, rel, save
from context_runtime import sha

p=Path(sys.argv[1])
previous=p/"panel-successor-batch01"
old_attempt,=previous.glob("attempt-*/FAILED.json")
active_plan=p/"actual02-salvage08-claim-applied.json"
revised=CYCLE/"selection/text-entry/current-element-revision01/PREFLIGHT_IMMUTABLE02.json"
prior=read(active_plan)
if not prior["applied"] or not read(revised)["same_exact_native_results"]:
    raise ValueError("Require both guarded independent recovery and exact repeated native review")
if any((previous/artifact).exists() for artifact in ("SNAPSHOT.json","BATCH_DISPATCH.json","snapshot")):
    raise ValueError("Failed old task group has dispatch or physical snapshot")
if read(old_attempt)["error"]!="Evidence changed: uc-library/include/presonus/panel/Element.hpp":
    raise ValueError("Observed original failure differs")
targets={row["existing_packet"] for row in prior["retained"]}
if len(targets)!=3:
    raise ValueError("Require exact three previously parked TextEntry task IDs")
for directory in (CYCLE/"workspaces").glob("*"):
    intent=directory/"APPLY_INTENT.json"
    if not intent.exists():
        continue
    plan=directory/"PLAN.json"
    if sha(plan)!=read(intent)["plan_sha256"]:
        raise ValueError("Cannot authenticate actual workspace apply history")
    for item in read(plan)["assignments"]:
        if set(item["packets"])&targets:
            raise ValueError("Old blocked target previously bound to actual physical writer")
live=[]
for item in Path("/proc").glob("[0-9]*"):
    try:
        data=(item/"cmdline").read_bytes()
    except (OSError,PermissionError):
        continue
    argv=[os.fsdecode(spelling) for spelling in data.split(b"\0")]
    if "batch-prepare" in argv and "--out" in argv and Path(argv[argv.index("--out")+1]).resolve()==previous.resolve():
        live.append(item.name)
if live:
    raise ValueError("Original packet coordinator is still active")
root=p/"text-entry-inactive-release-final01"
for row in prior["retained"]:
    packet=ROOT/row["existing_packet"]
    if ((packet/"context.json").exists() or read(packet/"BATCH_MEMBER.json")!={
            "manifest":rel(previous/"BATCH_DISPATCH.json"),"state":"pending","version":1}
            or sha(packet/"request.json")!=row["earlier_request_sha256"]):
        raise ValueError("Original unlaunched packet changed")
    req=read(packet/"request.json")
    if req["work_binding"]["claim_id"] != row["claim_id"] or req["task_id"]!=row["task"]:
        raise ValueError("Exact earlier active owner changed")
    points=[
        reference(old_attempt,"review_record","Exact earlier setup evidence failure"),
        reference(active_plan,"review_record","Exact entire eight independent recovery and three retained original leases"),
        reference(revised,"review_record","Current actual typed source and repeated original cases for same owner"),
        reference(packet/"request.json","review_record","Original unopened exact request and claim identity"),
    ]
    save(root/(row["task"]+".json"),dict(owner=row["task"],reason=
        "Root-authorized inactive same-owner successor review after archived canonical Element evidence changed. "
        "Preserve the earlier exact identity, claim history and pending packet evidence. No transfer to a different owner.",
        live_state_checked=True,resumable_state_checked=True,
        observations=dict(current_utc=datetime.now(timezone.utc).isoformat(),claim_id=row["claim_id"],
            original_packet=row["existing_packet"],active_coordinator_pids=live,physical_owner=False,
            preserved_earlier_frozen_sources=True,verified_evidence=points)))
print(root)
