"""Read-only planning and explicit reviewed launch command generation for the current 10x20 cycle."""
import argparse
from collections import defaultdict
from contextlib import closing
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re
import shlex
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[4]
CYCLE = ROOT / "temp/recovery-work/control10x20-after-4fed70d11"
PRODUCTION_CONTINUATION = (
    "Root authorized ongoing rolling production with full original identity/range coverage and maintained equivalence validation."
)
sys.path.insert(0, str(ROOT / "dependency-graph"))

from context_runtime import validate_task
from dedup_index import meta
from execution_review import _node_identities, batch_validation, checked_digest, collect
from reconstruction_contract import SCOPES, bound_files, validate_request


def read(path):
    return json.loads(path.read_text())


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as out:
        out.write(json.dumps(value, indent=2, sort_keys=True) + "\n")


def rel(path):
    return str(path.resolve().relative_to(ROOT))


def reference(path, kind, scope):
    path = ROOT / path
    return {"path": rel(path), "sha256": checked_digest(ROOT, path),
            "kind": kind, "scope": scope}


def target_of(candidate):
    item = candidate["target"]
    return dict(original_elf_sha256=item["elf_sha256"], mangled=item["original_mangled"],
                address=item["original_address"], size=item["original_size"],
                section=int(item["section_index"]), anchor=item["catalog_anchor"],
                role=item["role"], firmware=item["firmware"])



sys.path.insert(0, str(ROOT / "uc-library/tools/registry"))
from providers import definitions as provider_definitions, reference as provider_reference
VENDOR_OWNERSHIP_SHA256 = "aa7481c4c75678654e73de1262d5c36070cbad3026cefcaf46350d9cc0ae412e"
PARKED_ASSIGNMENTS = CYCLE / "packeting/INTERRUPTED-SCOPES-PARKED01.json"


def exact_original(target):
    return (target["original_elf_sha256"], target["mangled"], target["address"],
            target["size"], target["section"])


def check_parked_assignment(task_id, work_id, targets):
    selected = {exact_original(target) for target in targets}
    for row in read(PARKED_ASSIGNMENTS)["tasks"]:
        denied = {exact_original(target) for target in row["targets"]}
        if task_id == row["task_id"] or work_id == row["work_item_id"] or selected & denied:
            raise ValueError(f"Root parked the exact scope; no retry in this cycle: {row['task_id']}")


@lru_cache(maxsize=1)
def vendor_owned_originals():
    return {(item["elf_sha256"], item["original_mangled"], item["original_address"], item["original_size"],
             int(item["section_index"])) for item in provider_definitions(VENDOR_OWNERSHIP_SHA256)}


def check_vendor_source_route(target):
    """Keep actual public and private libpng/zlib routines on the pinned source route."""
    identity = (target.get("original_elf_sha256"), target["mangled"], target.get("address"),
                target.get("size"), target.get("section"))
    if identity in vendor_owned_originals():
        raise ValueError("Exact original libpng/zlib ownership requires pinned provider route: " + target["mangled"])
    name = target["mangled"].split("@", 1)[0]
    png = name.startswith("png_")
    zlib = re.fullmatch(
        r"(?:zlib(?:Version|CompileFlags)|z(?:calloc|cfree|Error)|get_crc_table|"
        r"compress(?:2|Bound)?|uncompress(?:2)?|"
        r"(?:adler32|crc32)(?:_[a-zA-Z0-9_]+)?|"
        r"(?:inflate|deflate)[A-Z_].*|inflate|deflate|gz_.*|"
        r"gz(?:open(?:64)?|dopen|buffer|setparams|f?read|f?write|printf|vprintf|puts|gets|putc|getc_?|ungetc|flush|"
        r"seek(?:64)?|rewind|tell(?:64)?|offset(?:64)?|eof|direct|close(?:_[rw])?|error|clearerr)|"
        r"_tr_(?:init|tally|align|flush_bits|flush_block|stored_block))", name)
    if png or zlib:
        raise ValueError("Pinned upstream libpng/zlib source or typed provider binding required: " + name)



def verify_planned_equivalence(tasks):
    """Apply the maintained exact decision evidence checks before acquiring claims."""
    pointer_path = ROOT / "dependency-graph/DEDUP_ACTIVE.json"
    pointer = read(pointer_path)
    database = (ROOT / pointer["database"]).resolve()
    database.relative_to(ROOT)
    with closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)) as conn, batch_validation(ROOT):
        conn.row_factory = sqlite3.Row
        if meta(conn, "generation") != pointer["generation"]:
            raise ValueError("Current dedup generation differs")
        for task in tasks:
            check_parked_assignment(task["task_id"], task["existing_work_item_id"], task["targets"])
            row = conn.execute(
                "SELECT w.status,w.decision_id,d.subject_id,d.revision,d.evidence_refs "
                "FROM reconstruction_work_items w LEFT JOIN equivalence_decisions d ON d.id=w.decision_id "
                "WHERE w.id=?", (task["existing_work_item_id"],)).fetchone()
            if not row or row["status"] in {"completed","superseded"}:
                raise ValueError("Current unique work is unavailable for " + task["task_id"])
            if row["decision_id"] is None:
                continue
            latest, = conn.execute("SELECT max(revision) FROM equivalence_decisions WHERE subject_id=?",
                                   (row["subject_id"],)).fetchone()
            if latest != row["revision"]:
                raise ValueError("Current work equivalence revision changed for " + task["task_id"])
            for item in json.loads(row["evidence_refs"]):
                file = (ROOT / item["path"]).resolve(strict=True)
                file.relative_to(ROOT)
                if checked_digest(ROOT,file) != item["sha256"]:
                    raise ValueError(f"{task['task_id']}: exact equivalence evidence changed: {item['path']}")
    if read(pointer_path) != pointer:
        raise ValueError("Dedup pointer changed during exact decision evidence audit")


def owner_files(lane, candidate, task_id):
    scope, = (row for row in lane["scope_ownership"] if row["scope"] == candidate["scope"])
    production = sorted(set(scope["owned_headers"] + scope["owned_sources"]))
    if not production:
        raise ValueError(f"{task_id} has no canonical source ownership")
    return production, production + [
        f"uc-library/tests/recovery/{task_id}/{name}"
        for name in ("Replay.cpp", "native.py", "check.py", "fixtures.json")
    ] + [
        f"uc-library/candidates/{task_id}/{name}" for name in ("HANDOFF.json", "worker-proof.json")
    ]



def work_targets(dedup, candidate, representative):
    """Bind every already-approved original in this unique work group upfront."""
    members = dedup.execute(
        "SELECT o.* FROM work_item_members m JOIN symbol_occurrences o ON o.id=m.occurrence_id "
        "WHERE m.work_item_id=? ORDER BY o.elf_sha256,o.original_address,o.id",
        (candidate["work_item_id"],)).fetchall()
    selected = {(item["elf"], item["mangled"], item["anchor"])
                for item in candidate.get("covered_originals", [])}
    actual = {(item["elf_sha256"], item["original_mangled"], item["catalog_anchor"])
              for item in members}
    key = (representative["original_elf_sha256"], representative["mangled"], representative["anchor"])
    if key not in actual or (len(actual) > 1 and selected != actual):
        raise ValueError("Choose the exact current reviewed full work-item coverage")
    targets = [representative]
    for member in members:
        if (member["elf_sha256"], member["original_mangled"], member["catalog_anchor"]) == key:
            continue
        (firmware, role), = dedup.execute(
            "SELECT DISTINCT firmware_version,role FROM binary_releases WHERE elf_sha256=?",
            (member["elf_sha256"],)).fetchall()
        targets.append(dict(
            original_elf_sha256=member["elf_sha256"], mangled=member["original_mangled"],
            address=member["original_address"], size=member["original_size"],
            section=int(member["section_index"]), anchor=member["catalog_anchor"],
            firmware=firmware, role=role))
    return targets


def inventory(proposal, output):
    active_path = ROOT / "dependency-graph/NATIVE_ACTIVE.json"
    active = read(active_path)
    database = (ROOT / active["database"]).resolve()
    database.relative_to(ROOT)
    dedup_path = ROOT / "dependency-graph/DEDUP_ACTIVE.json"
    dedup_pointer = read(dedup_path)
    dedup_database = (ROOT / dedup_pointer["database"]).resolve()
    dedup_database.relative_to(ROOT)
    lanes, targets, work, owners = [], set(), set(), {}
    with batch_validation(ROOT), closing(sqlite3.connect(dedup_database.as_uri() + "?mode=ro", uri=True)) as dedup:
        dedup.row_factory = sqlite3.Row
        generation = meta(dedup, "generation")
        if generation != dedup_pointer["generation"]:
            raise ValueError("Dedup table generation differs from approved exposure")
        if checked_digest(ROOT, database) != active["sha256"]:
            raise ValueError("Native database hash mismatch")
        with closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)) as conn:
            conn.row_factory = sqlite3.Row
            identities = _node_identities(conn)
            for lane in proposal["lanes"]:
                number = int(lane["lane"])
                if not 1 <= number <= 10:
                    raise ValueError("Unexpected lane number")
                name = f"cycle20_g{number:02}"
                if name in {item["name"] for item in lanes} or len(lane["candidates"]) > 20:
                    raise ValueError("Duplicate lane or more than twenty candidate slots")
                group = {"name": name, "tasks": []}
                lanes.append(group)
                for index, candidate in enumerate(lane["candidates"], 1):
                    task_id = candidate.get("task_id_override", f"{name}_s{index:02}")
                    if not re.fullmatch(name + r"_(?:s|r)[0-9]{2}", task_id):
                        raise ValueError("Invalid lane task ID")
                    target = target_of(candidate)
                    identity = target["original_elf_sha256"], target["mangled"]
                    all_targets = work_targets(dedup, candidate, target)
                    check_parked_assignment(task_id, candidate["work_item_id"], all_targets)
                    for original in all_targets:
                        check_vendor_source_route(original)
                    new_identities = {(item["original_elf_sha256"],item["mangled"]) for item in all_targets}
                    work_id = candidate["work_item_id"]
                    if new_identities & targets or work_id in work or len(new_identities) != len(all_targets):
                        raise ValueError(f"{task_id} repeats an original or a unique work item")
                    targets.update(new_identities)
                    work.add(work_id)
                    production, owned = owner_files(lane, candidate, task_id)
                    for path in owned:
                        if owners.setdefault(path, name) != name:
                            raise ValueError(f"Cross-lane writer conflict for {path}")
                    observed = collect(conn, all_targets, identities)
                    native_id = candidate["target"]["native_id"]
                    key = identity + (target["address"], target["size"])
                    if identities[key] != [native_id]:
                        raise ValueError(f"{task_id} native range does not match selection")
                    row = conn.execute("SELECT payload FROM bodies WHERE id=?", (native_id,)).fetchone()
                    if hashlib.sha256(row[0].encode()).hexdigest() != candidate["native_body_sha256"]:
                        raise ValueError(f"{task_id} native body hash differs from selection")
                    body = json.loads(row[0])
                    if not body.get("instructions"):
                        raise ValueError(f"{task_id} has no native instructions")
                    direct = {(b["kind"], b["site"], b["native_id"]): b
                              for b in candidate["direct_boundaries"]}
                    exact_representative = {(v["kind"], v["site"], v.get("destination"))
                                            for v in observed.values() if v["source"]==native_id}
                    if set(direct) != exact_representative:
                        raise ValueError(f"{task_id} selection/native representative execution boundary mismatch")
                    bodies = {}
                    for covered in all_targets:
                        exact = (covered["original_elf_sha256"],covered["mangled"],covered["address"],covered["size"])
                        covered_id, = identities[exact]
                        payload = conn.execute("SELECT payload FROM bodies WHERE id=?", (covered_id,)).fetchone()
                        covered_body = json.loads(payload[0])
                        if not covered_body.get("instructions"):
                            raise ValueError(f"{task_id} covered target has no native instructions")
                        bodies[covered_id] = covered_body
                    path = output / "native" / f"{task_id}.json"
                    save(path, {"target": target, "targets":all_targets, "native_id": native_id, "body": body,
                                "covered_bodies":bodies, "boundary_observations": observed, "selection": candidate})
                    native = reference(path, "native_observation", "Exact original app range and execution boundaries")
                    boundaries = {}
                    for k, v in observed.items():
                        route = direct.get((v["kind"], v["site"], v.get("destination"))) if v["source"]==native_id else None
                        if route is None:
                            native_destination = v.get("destination")
                            destination = (conn.execute("SELECT metadata FROM nodes WHERE id=?", (native_destination,)).fetchone()
                                           if native_destination else None)
                            label = (json.loads(destination[0]).get("demangled") or json.loads(destination[0]).get("mangled")
                                     if destination else None)
                            route = dict(kind=v["kind"], site=v["site"], native_id=native_destination,
                                         target_names=[label] if label else [], routing="covered_exact_boundary_requires_review")
                        boundaries[k] = {"observed":v,"routing_context":route}
                    group["tasks"].append(dict(task_id=task_id, candidate=candidate, target=target,
                                               targets=all_targets, native_ids=list(bodies),
                                               production=production, owned=owned, native=native,
                                               boundaries=boundaries))
        if read(active_path) != active or read(dedup_path) != dedup_pointer:
            raise ValueError("Native or dedup generation changed during planning")
    return {"native": active, "lanes": lanes,
            "pinned_vendor_exclusion": provider_reference(VENDOR_OWNERSHIP_SHA256)}


def build_contract(row, review, native_sha):
    candidate, target = row["candidate"], row["target"]
    task_id = row["task_id"]
    native = row["native"]
    if review["target"] != target or review["work_item_id"] != candidate["work_item_id"]:
        raise ValueError(f"{task_id} review belongs to a different original or work item")
    if review["native_evidence_sha256"] != native["sha256"]:
        raise ValueError(f"{task_id} review needs the current native and history evidence")
    owned = sorted(set(row["owned"]) | {
        path for site in review["execution_boundaries"].values()
        if site["kind"] == "dependency" and site["dependency"]["kind"] == "included_work"
        for path in site["dependency"]["owned_files"]
    })
    requirements = review["requirements"]
    if set(requirements) != set(SCOPES):
        raise ValueError(f"{task_id} needs all four requirement reviews")
    requirements = {name: dict(value, evidence=[native, *value.get("evidence", [])])
                    for name, value in requirements.items()}

    dependencies, observations = [], []
    reviewed_sites = review["execution_boundaries"]
    if set(reviewed_sites) != set(row["boundaries"]):
        raise ValueError(f"{task_id} needs review of each exact native boundary")
    for key, site in reviewed_sites.items():
        entry = dict(key=key, kind=site["kind"], reason=site["reason"],
                     evidence=[native, *site.get("evidence", [])],
                     observed=row["boundaries"][key]["observed"])
        if site["kind"] == "dependency":
            entry["dependency_index"] = len(dependencies)
            dependencies.append(site["dependency"])
        observations.append(entry)
    dependencies.extend(review.get("additional_dependencies", []))
    contract = dict(version=1, reviewer=review["reviewer"], targets=row.get("targets",[target]), owned_files=owned,
                    domain=review["domain"], requirements=requirements, dependencies=dependencies,
                    execution_boundary_review=dict(native_sha256=native_sha, observations=observations))
    task = dict(task_id=task_id, mode="reconstruct", work_kind="reconstruct",
                unmapped_policy="block", namespace=review["namespace"],
                targets=row.get("targets",[target]), owned_files=owned,
                existing_work_item_id=candidate["work_item_id"],
                objective=review["objective"], prior_history={
                    "catalog_revision": candidate["catalog_revision"],
                    "selection_evidence": native,
                    "notes": candidate.get("prior_history", candidate.get("notes", [])),
                })
    task.update({key: review[key] for key in ("linkage_scope", "additional_original_scopes")
                 if key in review})
    return task, contract


def materialize(inventory_path, review_path, output, batch):
    manifest = read(inventory_path)
    active = read(ROOT / "dependency-graph/NATIVE_ACTIVE.json")
    if active != manifest["native"]:
        raise ValueError("Native generation changed after evidence inventory")
    review = read(review_path)
    pending = {row["task_id"] for lane in manifest["lanes"] for row in lane["tasks"]}
    if set(review["tasks"]) != pending:
        raise ValueError("Reviewed wave must explicitly cover every selected task")
    claims, groups, audits, reads, writes = [], [], [], defaultdict(set), {}
    grouped_work = {}
    with batch_validation(ROOT):
        for lane in manifest["lanes"]:
            packets = []
            name = lane["name"]
            for row in lane["tasks"]:
                task_id = row["task_id"]
                task_review = review["tasks"][task_id]
                task, contract = build_contract(row, task_review, active["sha256"])
                path = output / "contracts" / f"{task_id}.json"
                save(path, contract)
                binding = reference(path, "review_record", "Reviewed source-port planning contract")
                task["reconstruction_contract"] = {k: binding[k] for k in ("path", "sha256")}
                bounded = {k: v["work"] for k, v in contract["requirements"].items()
                           if v["status"] == "bounded_work"}
                unresolved = row["candidate"].get("dependency_blockers") or any(
                    item["observed"]["kind"] == "ARM_INDIRECT_REVIEW_CANDIDATE"
                    for item in row["boundaries"].values())
                if unresolved and not bounded:
                    raise ValueError(f"{task_id} requires explicit bounded uncertainty")
                if bounded:
                    task["uncertainty_work"] = {
                        "contract": task["reconstruction_contract"], "assigned_scopes": bounded,
                        "preserve_unresolved_context": True, "no_silent_pruning": True,
                    }
                task["included_dependency_work"] = sorted({
                    dep["work_item_id"] for dep in contract["dependencies"]
                    if dep["kind"] == "included_work"})
                grouped_work[task["existing_work_item_id"]] = (name, task["owned_files"], len(audits))
                task["declared_source_dependencies"] = sorted({
                    item for item in bound_files(ROOT, task)
                    if Path(item).suffix in {".h", ".hpp", ".cpp"}
                } | set(task_review.get("extra_source_reads", [])) | {
                    item for item in row["production"] if (ROOT / item).is_file()
                })
                task["declared_source_hashes"] = {
                    item: reference(item, "cpp_implementation", "Explicit prefreeze source read")["sha256"]
                    for item in task["declared_source_dependencies"]
                }
                validate_task(task)
                result = validate_request(ROOT, task)
                task_path = output / "tasks" / f"{task_id}.json"
                save(task_path, task)
                claims.append(rel(task_path))
                packets.append(rel(batch / "packets" / task_id))
                reads[name].update(task["declared_source_dependencies"])
                for path in task["owned_files"]:
                    if writes.setdefault(path, name) != name:
                        raise ValueError(f"Cross-lane writer conflict for {path}")
                audits.append({"task": rel(task_path), "owner": name,
                               "task_sha256": checked_digest(ROOT, task_path), "target": row["target"],
                               "contract": task["reconstruction_contract"],
                               "uncertainty_work": task.get("uncertainty_work"),
                               "native_boundaries": sorted(row["boundaries"]),
                               "work_item_id": task["existing_work_item_id"],
                               "required_work": task["included_dependency_work"],
                               "included_write_paths": {d["work_item_id"]: d["owned_files"]
                                                        for d in contract["dependencies"] if d["kind"] == "included_work"},
                               "exact_self_recursion": any(site.get("destination") == site["source"]
                                                           for site in (b["observed"] for b in row["boundaries"].values())),
                               "planning": result})
            if packets:
                groups.append(dict(task_name=name, packets=packets, execution_order=packets,
                                   scope_reason="Canonical file ownership and exact reviewed native identities"))
        for index, audit in enumerate(audits):
            for work_id in audit["required_work"]:
                if work_id == audit["work_item_id"] and audit["exact_self_recursion"]:
                    continue
                if work_id not in grouped_work or (grouped_work[work_id][0] != audit["owner"]
                        or grouped_work[work_id][2] >= index
                        or not set(audit["included_write_paths"][work_id]) <= set(grouped_work[work_id][1])):
                    raise ValueError(f"Included work belongs outside {audit['owner']}: {work_id}")
        conflicts = [{"reader": name, "writer": writes[path], "path": path}
                     for name, paths in reads.items() for path in sorted(paths)
                     if path in writes and writes[path] != name]
        if conflicts:
            save(output / "DECLARED_CONFLICTS.json", conflicts)
            raise ValueError("Cross-lane declared source reads overlap writes")
        full = len(groups) == 10 and all(len(group["packets"]) == 20 for group in groups)
        tasks = dict(tasks=claims, groups=groups)
        if not full:
            if any(len(group["packets"]) > 10 for group in groups):
                raise ValueError("Maintained rolling publication caps each compatible group at ten packets")
            authorization = review.get("smaller_batch_authorization")
            if not authorization:
                raise ValueError("Partial wave needs explicit Root authorization and recorded replacement state")
            tasks.update(allow_smaller=True, smaller_batch_authorization=authorization)
        has_multiple_roles = any(len(row.get("targets", [row["target"]])) > 1
                                 for lane in manifest["lanes"] for row in lane["tasks"])
        if has_multiple_roles and full:
            raise ValueError("Verified multi-original work requires maintained smaller production mode, not single-original trial mode")
        if has_multiple_roles:
            tasks["production_continuation"] = review.get("production_continuation") or PRODUCTION_CONTINUATION
        elif review.get("production_continuation"):
            tasks["production_continuation"] = review["production_continuation"]
        if not claims:
            raise ValueError("Cannot freeze an empty wave")
        verify_planned_equivalence([read(ROOT / path) for path in claims])
        tasks_path = output / "TASKS.json"
        save(tasks_path, tasks)
        save(output / "PREFREEZE.json", {
            "claims_made": 0, "workers_launched": 0, "inventory": rel(inventory_path),
            "inventory_sha256": checked_digest(ROOT, inventory_path), "review": rel(review_path),
            "review_sha256": checked_digest(ROOT, review_path), "planned_output": rel(batch),
            "tasks": rel(tasks_path), "tasks_sha256": checked_digest(ROOT, tasks_path),
            "lanes": len(groups), "selected_work_items": len(claims), "audits": audits,
            "declared_read_write_conflicts": conflicts,
        })


def command(output, snapshot):
    audit = read(output / "PREFREEZE.json")
    requests = []
    with batch_validation(ROOT):
        for path, expected in [(audit["review"], audit["review_sha256"]),
                               (audit["inventory"], audit["inventory_sha256"]),
                               (audit["tasks"], audit["tasks_sha256"])]:
            if checked_digest(ROOT, ROOT / path) != expected:
                raise ValueError(f"Reviewed input changed: {path}")
        for entry in audit["audits"]:
            path = ROOT / entry["task"]
            if checked_digest(ROOT, path) != entry["task_sha256"]:
                raise ValueError(f"Task changed: {entry['task']}")
            request = read(path)
            validate_request(ROOT, request)
            requests.append(request)
            for path, expected in request["declared_source_hashes"].items():
                if checked_digest(ROOT, ROOT / path) != expected:
                    raise ValueError(f"Declared source read changed: {path}")
    verify_planned_equivalence(requests)
    argv = ["uc-library/.venv/bin/python", "uc-library/tools/recovery/select_context.py",
            "batch-prepare", "--tasks", audit["tasks"], "--out", audit["planned_output"], "--jobs", "auto"]
    if snapshot:
        argv.extend(("--reuse-snapshot", rel(snapshot)))
    print(shlex.join(argv))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    survey = sub.add_parser("inventory")
    survey.add_argument("--proposal", type=Path, required=True)
    survey.add_argument("--out", type=Path, required=True)
    plans = sub.add_parser("materialize")
    plans.add_argument("--inventory", type=Path, required=True)
    plans.add_argument("--review", type=Path, required=True)
    plans.add_argument("--out", type=Path, required=True)
    plans.add_argument("--batch", type=Path, required=True)
    prepare = sub.add_parser("command")
    prepare.add_argument("--out", type=Path, required=True)
    prepare.add_argument("--reuse-snapshot", type=Path)
    args = parser.parse_args()
    args.out = args.out.resolve()
    if not args.out.is_relative_to(CYCLE):
        parser.error("--out must be in this cycle's working tree")
    if args.action != "command" and args.out.exists():
        parser.error("Choose a new output directory")
    if args.action == "inventory":
        save(args.out / "INVENTORY.json", inventory(read(args.proposal), args.out))
    elif args.action == "materialize":
        if not args.batch.resolve().is_relative_to(CYCLE) or args.batch.exists():
            parser.error("--batch must be a new output under this cycle's working tree")
        materialize(args.inventory, args.review, args.out, args.batch)
    else:
        command(args.out, args.reuse_snapshot)


if __name__ == "__main__":
    main()
