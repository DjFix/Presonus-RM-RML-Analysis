"""Preserve successful unlaunched exact owners after one stale decision blocks a fresh freeze."""
import argparse
from contextlib import closing
import fcntl
from pathlib import Path

from packet_cycle import CYCLE, ROOT, read, rel, save, validate_request
from context_batch import validate_tasks
from context_runtime import sha
from dedup_index import connect, dump, now
from dedup_work import active_index, validate_claim
from execution_review import batch_validation

parser = argparse.ArgumentParser(description=__doc__)
for flag in ("source-batch","source-manifest","new-batch","new-manifest","receipt"):
    parser.add_argument("--"+flag,required=True,type=Path)
parser.add_argument("--apply-plan",type=Path)
args=parser.parse_args()
paths=args.source_batch,args.source_manifest,args.new_batch,args.new_manifest,args.receipt
if not all(path.resolve().is_relative_to(CYCLE) for path in paths) or args.new_batch.exists() or args.receipt.exists():
    raise ValueError("Use exact preserved cycle inputs and fresh destinations")
before,after=read(args.source_manifest),read(args.new_manifest)
excluded=set(after["retained_blocked_tasks"])
before_tasks={Path(name).stem:name for name in before["tasks"]}
after_tasks={Path(name).stem:name for name in after["tasks"]}
if set(before_tasks)-set(after_tasks)!=excluded or len(after_tasks)!=8 or len(excluded)!=3:
    raise ValueError("Unexpected exact setup scope")
if any(before_tasks[k]!=v for k,v in after_tasks.items()):
    raise ValueError("Successful earlier task content path changed")
validate_tasks([read(ROOT/name) for name in after["tasks"]],after["groups"])
with (args.source_batch/"coordinator.lock").open("rb") as owner,(ROOT/"dependency-graph/state/context.lock").open("rb") as graph:
    fcntl.flock(owner,fcntl.LOCK_EX|fcntl.LOCK_NB)
    fcntl.flock(graph,fcntl.LOCK_SH if args.apply_plan is None else fcntl.LOCK_EX)
    frozen=read(args.source_batch/"FROZEN.json")
    failure,=args.source_batch.glob("attempt-*/FAILED.json")
    if read(failure)["error"]!="Evidence changed: uc-library/include/presonus/panel/Element.hpp":
        raise ValueError("Actual retained setup failure mismatch")
    if frozen["manifest_sha256"]!=sha(args.source_manifest) or read(ROOT/"dependency-graph/ACTIVE.json")!=frozen["inputs"]["active"]:
        raise ValueError("Earlier exact frozen setup controls changed")
    if any((args.source_batch/name).exists() for name in ("SNAPSHOT.json","BATCH_DISPATCH.json","snapshot")):
        raise ValueError("Earlier state now has physical capture or dispatch")
    if set(frozen["packets"]) != {rel(args.source_batch/"packets"/name) for name in before_tasks}:
        raise ValueError("Original interrupted exact scope changed")
    database,pointer=active_index(ROOT)
    database.close()
    moves,blocked=[],[]
    receipt=dict(old_source_manifest_sha256=frozen["manifest_sha256"],old_failure_sha256=sha(failure),
                 fresh_manifest_sha256=sha(args.new_manifest),active_generation=frozen["inputs"]["active"],
                 moves=moves,retained=blocked,applied=False)
    with closing(connect(ROOT/pointer["database"],readonly=args.apply_plan is None)) as db,batch_validation(ROOT):
        db.execute("BEGIN" if args.apply_plan is None else "BEGIN IMMEDIATE")
        try:
            for task_id,task_path in before_tasks.items():
                packet=args.source_batch/"packets"/task_id
                expected={"manifest":rel(args.source_batch/"BATCH_DISPATCH.json"),"state":"pending","version":1}
                if read(packet/"BATCH_MEMBER.json")!=expected or (packet/"context.json").exists():
                    raise ValueError("Original request no longer in unopened pending state")
                request=read(packet/"request.json")
                task=read(ROOT/task_path)
                for field in ("task_id","mode","owned_files","targets","existing_work_item_id","namespace"):
                    if request[field]!=task[field]:
                        raise ValueError(f"Exact normal earlier request differs at {task_id}/{field}")
                binding=request["work_binding"]
                previous=rel(packet)
                row=db.execute("SELECT id,owner,packet_path,state FROM work_claims WHERE id=?",(binding["claim_id"],)).fetchone()
                if row is None or tuple(row)!=(binding["claim_id"],task_id,previous,"active"):
                    raise ValueError("Exact prior active ownership changed")
                changes=[item for item in binding["equivalence_evidence"] if sha(ROOT/item["path"])!=item["sha256"]]
                details=dict(task=task_id,claim_id=binding["claim_id"],work_item_id=binding["work_item_id"],
                             existing_packet=previous, earlier_request_sha256=sha(packet/"request.json"))
                if task_id in excluded:
                    if {item["path"] for item in changes}!={"uc-library/include/presonus/panel/Element.hpp"}:
                        raise ValueError("Unexpected evidence drift in retained task")
                    blocked.append(dict(details,stale_decision_evidence=changes))
                else:
                    if changes:
                        raise ValueError("Fresh subset includes stale evidence")
                    validate_request(ROOT,task)
                    validate_claim(db,binding,previous)
                    moves.append(dict(details,new_packet=rel(args.new_batch/"packets"/task_id)))
            if args.apply_plan is None:
                db.rollback()
            else:
                if read(args.apply_plan)!=receipt:
                    raise ValueError("Guarded scope differs from read-only plan")
                for entry in moves:
                    changed=db.execute("UPDATE work_claims SET packet_path=? WHERE id=? AND owner=? AND packet_path=? AND state='active'",
                        (entry["new_packet"],entry["claim_id"],entry["task"],entry["existing_packet"]))
                    if changed.rowcount!=1:
                        raise ValueError("Exact claim moved concurrently")
                    db.execute("INSERT INTO claim_history(claim_id,state,reason,observations,created_at) VALUES(?,?,?,?,?)",
                        (entry["claim_id"],"active","same exact eligible unlaunched owner after independent setup evidence failure",
                         dump(dict(entry,source_attempt_sha256=receipt["old_failure_sha256"],dry_run_sha256=sha(args.apply_plan))),now()))
                db.commit()
                receipt["applied"]=True
        except BaseException:
            db.rollback()
            raise
save(args.receipt,receipt)
print(len(moves),"exact prior owners preserved;",len(blocked),"unchanged blocked claims; applied",receipt["applied"])
