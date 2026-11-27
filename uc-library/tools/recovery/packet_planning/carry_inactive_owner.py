"""Rebind exact inactive current-index claims after changed provider evidence."""
import argparse
from contextlib import closing
import fcntl
from pathlib import Path

from packet_cycle import CYCLE, ROOT, read, reference, rel, save, validate_request
from context_batch import validate_tasks
from context_publication import authorization
from context_runtime import sha
from dedup_index import connect, dump, now
from dedup_work import active_index, validate_claim

parser=argparse.ArgumentParser(description=__doc__)
for label in ("manifest","batch","owner-observation","out"):
    parser.add_argument("--"+label,type=Path,required=True)
parser.add_argument("--apply-plan",type=Path)
a=parser.parse_args()
for path in (a.manifest,a.batch,a.owner_observation,a.out):
    if not path.resolve().is_relative_to(CYCLE):
        raise ValueError("Use cycle-local fresh controls")
if a.batch.exists() or a.out.exists():
    raise ValueError("Fresh output and packet destinations required")

observed=read(a.owner_observation)
if not observed.get("root_authorization") or not observed.get("graph_state_sha256"):
    raise ValueError("Explicit Root authorization and cleared current state required")
conditions=observed["exact_inactive_tasks"]
if not conditions:
    raise ValueError("No exact observed inactive-owner work")
manifest=read(a.manifest)
tasks=[read(ROOT/p) for p in manifest["tasks"]]
validate_tasks(tasks,manifest["groups"])
new={Path(p).name:p for g in manifest["groups"] for p in g["packets"]}
matched={}
for task in tasks:
    task_id=task["task_id"]
    validate_request(ROOT,task)
    if task_id not in conditions:
        continue
    obs=conditions[task_id]
    if not obs["inactive_rechecked"] or not obs["changed_provider_provenance"]:
        raise ValueError("Exact inactive owner or changed prerequisite not established: "+task_id)
    for ref in obs["evidence"]:
        if reference(ref["path"],"review_record","Exact inactive prior source or operator evidence")["sha256"]!=ref["sha256"]:
            raise ValueError("Owner evidence changed: "+ref["path"])
    if len(obs["evidence"])<2:
        raise ValueError("Need real prior blocker and fresh verified provenance objects")
    old=ROOT/obs["prior_packet"]
    if old.name!=task_id:
        raise ValueError("Historical task path and prior owner differ")
    authorization(ROOT,old)
    req=read(old/"request.json")
    for field in ("task_id","targets","existing_work_item_id","namespace","mode","work_kind"):
        if req[field]!=task[field]:
            raise ValueError(f"Exact historical {field} differs for {task_id}")
    def production_scope(files):
        return {name for name in files if not name.startswith(
            ("uc-library/tests/recovery/", "uc-library/candidates/"))}

    if production_scope(req["owned_files"]) != production_scope(task["owned_files"]):
        raise ValueError("Fresh owner changed the exact prior production write scope: " + task_id)
    old_artifacts = set(req["owned_files"]) - production_scope(req["owned_files"])
    for name in set(task["owned_files"]) - production_scope(task["owned_files"]):
        if name not in old_artifacts and not name.startswith((
                f"uc-library/tests/recovery/{task_id}/", f"uc-library/candidates/{task_id}/")):
            raise ValueError("Fresh artifact is not confined to its exact logical owner: " + name)
    binding=req["work_binding"]
    if binding["claim_owner"]!=task_id or obs["prior_claim_id"]!=binding["claim_id"]:
        raise ValueError("Historical exact claim owner unavailable: "+task_id)
    destination=new[task_id]
    if destination!=rel(a.batch/"packets"/task_id):
        raise ValueError("Unexpected fresh packet path")
    matched[task_id]=(binding,dict(task_id=task_id,claim_id=binding["claim_id"],
        work_item_id=binding["work_item_id"],prior_packet=rel(old),new_packet=destination,
        prior_request_sha256=sha(old/"request.json"),targets=req["targets"]))

if set(matched)!=set(conditions):
    raise ValueError("Fresh manifest differs from exact Root-authorized owner set")
with (ROOT/"dependency-graph/state/context.lock").open("rb") as lock:
    fcntl.flock(lock, fcntl.LOCK_SH if a.apply_plan is None else fcntl.LOCK_EX)
    active=read(ROOT/"dependency-graph/ACTIVE.json")
    if active["state_sha256"]!=observed["graph_state_sha256"]:
        raise ValueError("Canonical current graph changed")
    data=dict(active_generation=active,claims=[entry for _,entry in matched.values()],
        manifest=rel(a.manifest),manifest_sha256=sha(a.manifest),
        owner_observation=rel(a.owner_observation),owner_observation_sha256=sha(a.owner_observation),applied=False)
    view,pointer=active_index(ROOT)
    view.close()
    with closing(connect(ROOT/pointer["database"],readonly=a.apply_plan is None)) as db:
        db.execute("BEGIN" if a.apply_plan is None else "BEGIN IMMEDIATE")
        try:
            for binding,entry in matched.values():
                validate_claim(db,binding,entry["prior_packet"])
            if a.apply_plan is None:
                db.rollback()
            else:
                if read(a.apply_plan)!=data:
                    raise ValueError("Applied carry differs from exact guarded dry-run")
                for binding,entry in matched.values():
                    if db.execute("SELECT 1 FROM work_claims WHERE packet_path=? AND state='active'",
                                  (entry["new_packet"],)).fetchone():
                        raise ValueError("Fresh packet path already has a claim")
                    result=db.execute("UPDATE work_claims SET packet_path=? WHERE id=? AND owner=? AND packet_path=? AND state='active'",
                        (entry["new_packet"],entry["claim_id"],entry["task_id"],entry["prior_packet"]))
                    if result.rowcount!=1:
                        raise ValueError("Claim or prior owner changed during apply")
                    db.execute("INSERT INTO claim_history(claim_id,state,reason,observations,created_at) VALUES(?,?,?,?,?)",
                        (entry["claim_id"],"active","verified inactive exact same-owner recovery after changed provider",
                         dump(dict(entry,owner_observation_sha256=data["owner_observation_sha256"],
                                   dry_run_sha256=sha(a.apply_plan))),now()))
                db.commit()
                data["applied"]=True
        except BaseException:
            db.rollback()
            raise
save(a.out,data)
print(len(matched),"historical exact same-owner active claims validated; applied",data["applied"])
