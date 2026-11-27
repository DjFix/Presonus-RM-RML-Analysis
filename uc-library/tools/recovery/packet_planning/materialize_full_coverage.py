"""Materialize all covered original range identities and exact execution reviews."""
import argparse
from contextlib import closing
import json
from pathlib import Path
import sys
import sqlite3

from packet_cycle import ROOT, read, reference, rel, save, validate_request
from context_batch import validate_tasks
sys.path.insert(0, str(ROOT / 'uc-library/tools/recovery'))
from select_context import adapter, enrich
from dedup_work import active_index, plan
from execution_review import _node_identities, batch_validation, checked_digest, collect

cli = argparse.ArgumentParser(description=__doc__)
for arg in ("manifest", "source-batch", "new-batch", "out"):
    cli.add_argument("--" + arg, type=Path, required=True)
args = cli.parse_args()
original = read(args.manifest)
frozen = read(args.source_batch / "FROZEN.json")
if checked_digest(ROOT, args.manifest) != frozen["manifest_sha256"]:
    raise ValueError("Failed freeze does not bind original manifest")
if args.out.exists() or args.new_batch.exists():
    raise ValueError("Use fresh recovery outputs")
native = read(ROOT / "dependency-graph/NATIVE_ACTIVE.json")
path = ROOT / native["database"]
if checked_digest(ROOT, path) != native["sha256"]:
    raise ValueError("Pinned native evidence input changed")
connection, _ = active_index(ROOT)
tasks, audit = [], []
with closing(connection) as dedup, closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as db, batch_validation(ROOT), adapter.snapshot(ROOT / "uc-library") as ledger:
    db.row_factory = sqlite3.Row
    identities = _node_identities(db)
    for name in original["tasks"]:
        task = read(ROOT / name)
        binding = plan(dedup, enrich(task, ledger))
        members = binding["covered_occurrences"]
        prior = {item["anchor"]: item for item in task["targets"]}
        requested = set(prior)
        covered = {item["catalog_anchor"] for item in members}
        if not requested <= covered:
            raise ValueError("Initial original anchor is not covered")
        if requested == covered:
            tasks.append(name)
            continue
        new_targets = list(task["targets"])
        native_roots = {}
        for row in members:
            anchor = row["catalog_anchor"]
            identity = (row["elf_sha256"], row["original_mangled"], row["original_address"], row["original_size"])
            node, = identities[identity]
            payload, = db.execute("SELECT payload FROM bodies WHERE id=?", (node,)).fetchone()
            native_roots[node] = json.loads(payload)
            if anchor in prior:
                continue
            (version, role), = dedup.execute("SELECT DISTINCT firmware_version,role FROM binary_releases WHERE elf_sha256=?",
                    (row["elf_sha256"],)).fetchall()
            new_targets.append(dict(original_elf_sha256=identity[0], mangled=identity[1], address=identity[2],
                                    size=identity[3], section=int(row["section_index"]), anchor=anchor,
                                    firmware=version, role=role))
        review = read(ROOT / task["reconstruction_contract"]["path"])
        review["targets"] = task["targets"] = new_targets
        observed = collect(db, new_targets, identities)
        entries = review["execution_boundary_review"]["observations"]
        missing = set(observed) - {item["key"] for item in entries}
        report = args.out / "native" / (task["task_id"] + ".json")
        save(report, dict(targets=new_targets, roots=native_roots, execution_boundaries=observed,
                          work_item_id=binding["work_item_id"], active_native=native))
        evidence = reference(report, "native_observation", "Exact original ranges and execution boundaries for every covered ELF identity.")
        review["requirements"]["state"]["evidence"].append(evidence)
        for key in sorted(missing):
            item = observed[key]
            target = db.execute("SELECT metadata FROM nodes WHERE id=?", (item.get("destination"),)).fetchone()
            name = json.loads(target[0]).get("demangled") if target else None
            if task["task_id"] != "cycle20_g06_s01" or name != "operator delete(void*)@@GLIBCXX_3.4" or item["kind"] != "ELF_CALLS":
                raise ValueError("Additional exact covered boundary requires human review: " + str(item))
            method = reference("uc-library/tests/recovery/real10_g04_s08/native.py", "review_record",
                               "Prior exact genuine Linux/native allocation validation method.")
            reason = ("Observe this exact role's original D0 same-receiver operator delete import at "
                      + hex(item["site"]) + " and separately verify actual Linux unsized deallocation.")
            entries.append(dict(key=key, kind="dependency", reason=reason, evidence=[evidence],
                                observed=item, dependency_index=len(review["dependencies"])))
            review["dependencies"].append(dict(kind="existing_implementation", name=name,
                                               binding_domain=reason, evidence=[evidence, method]))
        contract = args.out / "contracts" / (task["task_id"] + ".json")
        save(contract, review)
        task["reconstruction_contract"] = dict(path=rel(contract), sha256=checked_digest(ROOT, contract))
        task["uncertainty_work"]["contract"] = task["reconstruction_contract"]
        task_path = args.out / "tasks" / (task["task_id"] + ".json")
        validate_request(ROOT, task)
        revised = plan(dedup, enrich(task, ledger))
        if revised["work_item_id"] != binding["work_item_id"] or revised["covered_occurrences"] != members:
            raise ValueError("Complete range materialization changed claim coverage")
        save(task_path, task)
        tasks.append(rel(task_path))
        audit.append(dict(task=task["task_id"], work_item_id=binding["work_item_id"], original_anchors=sorted(requested),
                          covered_anchors=sorted(covered), added_execution_boundaries=len(missing)))

groups = []
for group in original["groups"]:
    groups.append(dict(group, **{key:[rel(args.new_batch / "packets" / Path(path).name)
                                     for path in group[key]] for key in ("packets", "execution_order")}))
validate_tasks([read(ROOT / name) for name in tasks], groups)
save(args.out / "TASKS.json", dict(original, tasks=tasks, groups=groups,
                                   failed_original_manifest_sha256=frozen["manifest_sha256"]))
save(args.out / "COVERAGE.json", dict(
    result=audit, failed_original_freeze_sha256=checked_digest(ROOT, args.source_batch / "FROZEN.json"),
    prior_immutable_files_preserved=True, causes="Covered alias entries need exact range and execution evidence before selector work enrichment."))
print(len(audit), "exact work groups materialized with complete coverage; other tasks unchanged")
