"""One-cycle guarded relocation of active same-owner packet claims after the mount alias failure."""
import argparse
from contextlib import ExitStack, closing
import fcntl
from pathlib import Path
import shlex
import subprocess
from packet_cycle import ROOT, CYCLE, read, rel, save
from context_batch import previous_container_absent, validate_tasks
from context_runtime import sha
from dedup_index import connect, dump, now
from dedup_work import active_index, validate_claim
from snapshot_runtime import immutable_mounts

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--old", nargs=1, type=Path, required=True)
parser.add_argument("--out", type=Path, required=True)
parser.add_argument("--manifest", type=Path, required=True)
parser.add_argument("--receipt", type=Path, required=True)
parser.add_argument("--check", type=Path, help="Require exact claim plan from prior read-only run and apply")
a = parser.parse_args()
a.out = a.out.resolve()
for path in [*a.old, a.out, a.manifest, a.receipt]:
    if not path.resolve().is_relative_to(CYCLE):
        parser.error("All outputs and originals must be below the cycle")
if a.out.exists() or a.receipt.exists():
    parser.error("New output and receipt paths required")
if a.check is None and a.manifest.exists():
    parser.error("New reviewed manifest required")

groups, tasks, plans, records, receipts = [], [], [], [], []
with ExitStack() as stack:
    for batch in a.old:
        batch = batch.resolve()
        lock = stack.enter_context((batch / "coordinator.lock").open("rb"))
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    lock = stack.enter_context((ROOT / "dependency-graph/state/context.lock").open("rb"))
    fcntl.flock(lock, fcntl.LOCK_EX)
    for batch in a.old:
        batch = batch.resolve()
        if (batch / "BATCH_DISPATCH.json").exists():
            raise ValueError(f"Existing dispatch must be preserved: {batch}")
        frozen_path = batch / "FROZEN.json"
        frozen = read(frozen_path)
        if frozen["inputs"]["active"] != read(ROOT / "dependency-graph/ACTIVE.json"):
            raise ValueError("Graph generation changed since failed attempt")
        failure, = batch.glob("attempt-*/FAILED.json")
        error = read(failure)
        if not error.get("claims_retained") or not error["error"].startswith("Immutable reference mount target shadowed: "):
            raise ValueError("Exact inactive snapshot mount planning failure required")
        if list(batch.glob("environment-runner-*.json")):
            raise ValueError("Unexpected runner launch before the mount planning failure")
        probe_path = batch.parent / "actual05-mounted-reference-repair-probe.json"
        probe = read(probe_path)
        snapshot = read(batch / "SNAPSHOT.json")
        if (probe["snapshot_sha256"] != sha(batch / "SNAPSHOT.json")
                or probe["reference_count"] != len(snapshot["references"])
                or probe["payload_hashes_recomputed"] != 0):
            raise ValueError("Full unchanged reference guard required")
        if len(immutable_mounts(ROOT, batch, snapshot)) != probe["emitted_mounts"]:
            raise ValueError("Corrected emitted mount list changed")
        changed = {path for path, digest in frozen["inputs"]["files"].items() if sha(ROOT/path) != digest}
        if changed != {"dependency-graph/snapshot_runtime.py", "dependency-graph/test_snapshot_provenance_mounts.py"}:
            raise ValueError("Unexpected frozen producer or task changes: " + repr(changed))
        for handle in batch.glob("environment-handles-*.json"):
            for name in read(handle)["containers"].values():
                argv = ["sg", "docker", "-c", shlex.join(["docker", "inspect", "--format", "{{.State.Running}}", name])]
                res = subprocess.run(argv, cwd=ROOT, text=True, capture_output=True)
                if not previous_container_absent(res, name) and (res.returncode or res.stdout.strip() != "false"):
                    raise ValueError(f"Prior environment running/uninspectable: {name}")
                receipts.append(dict(name=name, argv=argv, code=res.returncode, stdout=res.stdout, stderr=res.stderr))
        paths = [ROOT / path for path, digest in frozen["inputs"]["files"].items()
                 if path.endswith("/actual05-independent-draft10.json") and digest == frozen["manifest_sha256"]]
        manifest_path, = paths
        if sha(manifest_path) != frozen["manifest_sha256"]:
            raise ValueError("Original task manifest changed")
        manifest = read(manifest_path)
        packet_dirs = [ROOT / name for name in frozen["packets"]]
        if not all(p.is_relative_to(batch / "packets") for p in packet_dirs):
            raise ValueError("Frozen packet paths escape original batch")
        old_group_paths = {packet for g in manifest["groups"] for packet in g["packets"]}
        if old_group_paths != set(frozen["packets"]):
            raise ValueError("Frozen groups do not cover claimed packets")
        if any({x.name for x in p.iterdir()} != {"request.json", "BATCH_MEMBER.json"} for p in packet_dirs):
            raise ValueError("Only exclusively unselected, unpublished packets may carry forward")
        for path, directory in zip(manifest["tasks"], packet_dirs, strict=True):
            task_path = ROOT / path
            if sha(task_path) != frozen["inputs"]["files"][path]:
                raise ValueError(f"Original task changed: {path}")
            task = read(task_path)
            req = read(directory / "request.json")
            if not all(req.get(key) == task.get(key) for key in ("task_id", "targets", "owned_files", "reconstruction_contract", "uncertainty_work", "existing_work_item_id")):
                raise ValueError(f"Frozen exact original request unexpectedly differs: {path}")
            member = read(directory / "BATCH_MEMBER.json")
            if member["state"] != "pending" or member["manifest"] != rel(batch / "BATCH_DISPATCH.json"):
                raise ValueError("Packet already published or foreign")
            binding = req["work_binding"]
            owner = task["task_id"]
            if owner != binding["claim_owner"] or owner != directory.name:
                raise ValueError("Same-owner requirement failed")
            newid = rel(a.out / "packets" / owner)
            tasks.append(path)
            plans.append((binding, rel(directory), newid))
            records.append({"claim_id": binding["claim_id"], "owner": owner,
                            "work_item_id": binding["work_item_id"], "old_packet": rel(directory),
                            "new_packet": newid, "request_sha256": sha(directory / "request.json"),
                            "failed_frozen_sha256": sha(frozen_path), "probe_sha256": sha(probe_path),
                            "failure_sha256": sha(failure), "targets": req["targets"]})
        for group in manifest["groups"]:
            mapped = lambda paths: [rel(a.out / "packets" / Path(path).name) for path in paths]
            groups.append(dict(group, packets=mapped(group["packets"]), execution_order=mapped(group["execution_order"])))
    validate_tasks([read(ROOT / t) for t in tasks], groups)
    if len(tasks) != 10:
        raise ValueError("Expected exactly ten unchanged unselected tasks")
    planned_manifest = dict(manifest, groups=groups)
    if a.check is None:
        save(a.manifest, planned_manifest)
    elif read(a.manifest) != planned_manifest:
        raise ValueError("Reviewed carry-forward task manifest changed")
    result = {"old_batches": [rel(p) for p in a.old], "new_batch": rel(a.out),
        "manifest": rel(a.manifest), "manifest_sha256": sha(a.manifest), "claims": records,
        "environment_checks": receipts, "applied": False}
    ro, pointer = active_index(ROOT)
    ro.close()
    with closing(connect(ROOT / pointer["database"], readonly=a.check is None)) as c:
        c.execute("BEGIN IMMEDIATE")
        try:
            for binding, oldpath, _ in plans:
                validate_claim(c, binding, oldpath)
            if a.check is not None:
                if result != read(a.check):
                    raise ValueError("Claim or environment state changed across read-only check")
                for record, (binding, oldpath, newpath) in zip(records, plans, strict=True):
                    claim = binding["claim_id"]
                    if c.execute("SELECT id FROM work_claims WHERE packet_path=? AND state='active'", (newpath,)).fetchone():
                        raise ValueError(f"New packet already actively bound: {newpath}")
                    updated = c.execute(
                        "UPDATE work_claims SET packet_path=? WHERE id=? AND owner=? AND packet_path=? AND state='active'",
                        (newpath, claim, binding["claim_owner"], oldpath))
                    if updated.rowcount != 1:
                        raise ValueError(f"Claim changed during transaction: {claim}")
                    c.execute("INSERT INTO claim_history(claim_id,state,reason,observations,created_at) VALUES(?,?,?,?,?)",
                            (claim, "active", "same-owner packet carry-forward after verified read-only mount alias failure",
                             dump(dict(record, manifest=result["manifest"], manifest_sha256=result["manifest_sha256"],
                                       preflight_sha256=sha(a.check))), now()))
                c.commit()
                result["applied"] = True
            else:
                c.rollback()
        except BaseException:
            c.rollback()
            raise
    save(a.receipt, result)
print(f"Validated {len(records)} retained claims; transaction applied={result['applied']}")
