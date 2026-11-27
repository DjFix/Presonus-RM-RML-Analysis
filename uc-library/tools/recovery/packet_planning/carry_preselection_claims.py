"""Carry exact unlaunched setup-failure claims to reviewed same-owner packets."""
import argparse
from contextlib import closing
import fcntl
from pathlib import Path
import sys

from packet_cycle import CYCLE, ROOT, read, rel, save, validate_request
from context_runtime import sha
from dedup_index import connect, dump, now
sys.path.insert(0, str(ROOT / 'uc-library/tools/recovery'))
from select_context import adapter, enrich
from dedup_work import active_index, plan, validate_claim
from execution_review import batch_validation

cli = argparse.ArgumentParser(description=__doc__)
for field in ("source-batch", "new-batch", "source-manifest", "new-manifest", "out"):
    cli.add_argument("--" + field, type=Path, required=True)
cli.add_argument("--apply-plan", type=Path)
args = cli.parse_args()
paths = args.source_batch, args.new_batch, args.source_manifest, args.new_manifest, args.out
if not all(path.resolve().is_relative_to(CYCLE) for path in paths) or args.out.exists() or args.new_batch.exists():
    raise ValueError("Use cycle-local preserved controls and fresh outputs")
prior = read(args.source_manifest)
fresh = read(args.new_manifest)
old_tasks = {Path(path).stem: read(ROOT / path) for path in prior["tasks"]}
new_tasks = {Path(path).stem: read(ROOT / path) for path in fresh["tasks"]}
if set(old_tasks) != set(new_tasks):
    raise ValueError("Fresh inputs must preserve selected tasks")
with (args.source_batch / "coordinator.lock").open("rb") as owner, (ROOT / "dependency-graph/state/context.lock").open("rb") as graph:
    fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
    fcntl.flock(graph, fcntl.LOCK_SH if args.apply_plan is None else fcntl.LOCK_EX)
    frozen_path = args.source_batch / "FROZEN.json"
    frozen = read(frozen_path)
    failure, = sorted(args.source_batch.glob("attempt-*/FAILED.json"))
    if read(failure)["error"] != "Source-port planning gate: 'address'":
        raise ValueError("Unexpected earlier setup failure")
    if any((args.source_batch / name).exists() for name in ("packets", "SNAPSHOT.json", "BATCH_DISPATCH.json")):
        raise ValueError("Earlier setup created packet payloads or dispatch")
    if frozen["manifest_sha256"] != sha(args.source_manifest) or fresh["failed_original_manifest_sha256"] != frozen["manifest_sha256"]:
        raise ValueError("Earlier frozen manifest changed")
    if read(ROOT / "dependency-graph/ACTIVE.json") != frozen["inputs"]["active"]:
        raise ValueError("Canonical graph changed after failed preselection")
    prior_packets = {name: rel(args.source_batch / "packets" / name) for name in old_tasks}
    if set(prior_packets.values()) != set(frozen["packets"]):
        raise ValueError("Earlier frozen exact task destinations differ")
    active, pointer = active_index(ROOT)
    active.close()
    entries = []
    receipt = {
        "prior_manifest_sha256": frozen["manifest_sha256"], "fresh_manifest_sha256": sha(args.new_manifest),
        "prior_frozen_sha256": sha(frozen_path), "failure_sha256": sha(failure),
        "generation": frozen["inputs"]["active"], "claims": entries, "applied": False,
    }
    with closing(connect(ROOT / pointer["database"], readonly=args.apply_plan is None)) as db, batch_validation(ROOT), adapter.snapshot(ROOT / "uc-library") as ledger:
        db.execute("BEGIN" if args.apply_plan is None else "BEGIN IMMEDIATE")
        try:
            for task_id, old in old_tasks.items():
                new = new_tasks[task_id]
                validate_request(ROOT, new)
                for field in ("task_id", "mode", "work_kind", "namespace", "owned_files", "existing_work_item_id"):
                    if old[field] != new[field]:
                        raise ValueError(f"Exact retained task field differs: {task_id}/{field}")
                old_plan, new_plan = plan(db, enrich(old, ledger)), plan(db, enrich(new, ledger))
                for field in ("work_item_id", "representative_occurrence", "covered_occurrences", "equivalence_decision_id"):
                    if old_plan[field] != new_plan[field]:
                        raise ValueError(f"Current exact unique work closure differs: {task_id}/{field}")
                claim = db.execute("SELECT * FROM work_claims WHERE work_item_id=? AND state='active'", (new_plan["work_item_id"],)).fetchone()
                if claim is None:
                    continue
                if claim["owner"] != task_id or claim["packet_path"] != prior_packets[task_id]:
                    raise ValueError("Unexpected active claim on fresh batch original: " + task_id)
                binding = dict(new_plan, claim_id=claim["id"], claim_owner=task_id)
                validate_claim(db, binding, prior_packets[task_id])
                destination = rel(args.new_batch / "packets" / task_id)
                entries.append(dict(task=task_id, prior_packet=prior_packets[task_id], new_packet=destination,
                                    claim_id=claim["id"], work_item_id=new_plan["work_item_id"],
                                    exact_original_anchors=sorted(item["catalog_anchor"] for item in new_plan["covered_occurrences"])))
            discovered = {row[0] for row in db.execute("SELECT id FROM work_claims WHERE state='active' AND packet_path LIKE ?",
                                                      (rel(args.source_batch) + "/packets/%",))}
            if discovered != {row["claim_id"] for row in entries} or len(entries) != 5:
                raise ValueError("Unexpected partial setup claim coverage")
            if args.apply_plan is None:
                db.rollback()
            else:
                if read(args.apply_plan) != receipt:
                    raise ValueError("Reviewed fresh carry differs from current exact guarded effects")
                for row in entries:
                    moved = db.execute("UPDATE work_claims SET packet_path=? WHERE id=? AND owner=? AND packet_path=? AND state='active'",
                                       (row["new_packet"], row["claim_id"], row["task"], row["prior_packet"]))
                    if moved.rowcount != 1:
                        raise ValueError("Exact active owner moved concurrently")
                    db.execute("INSERT INTO claim_history(claim_id,state,reason,observations,created_at) VALUES(?,?,?,?,?)",
                               (row["claim_id"], "active", "same exact owner preselection retry with complete original alias ranges",
                                dump(dict(row, preselection_failure_sha256=receipt["failure_sha256"],
                                          dry_run_sha256=sha(args.apply_plan))), now()))
                db.commit()
                receipt["applied"] = True
        except BaseException:
            db.rollback()
            raise
save(args.out, receipt)
print(len(entries), "exact active same-owner setup claims; applied", receipt["applied"])
