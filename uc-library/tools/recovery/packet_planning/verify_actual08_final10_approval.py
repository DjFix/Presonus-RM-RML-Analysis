"""Read-only exact final10 verification after Actual08 registration and canonical admission."""
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import sys

from verify_actual07_approval_projection import adapter, verify_record
from project_actual07_partitions import P, S, ROOT, previous_compiler_deps, ref
from packet_cycle import check_parked_assignment, check_vendor_source_route, read, save, verify_planned_equivalence
from context_runtime import guard, sha
from dedup_work import active_index
from execution_review import batch_validation, checked_digest

PROJECTION = P / "ACTUAL08-FINAL10-PRECOPY-READONLY01.json"
PROJECTION_SHA256 = "7d1d975df1489a5d3beaf23ed26a84bc950878ecba4cd721b4b58fcc0b3abe23"
RM_PROBE = P / "ACTUAL08-R22-RM-PROVIDER-PROBE-READBACK01.json"
RM_PROBE_SHA256 = "c04f5b63d49c50f04d6e3cc5b83a6eeba32047247ff393c7de7c8e9c7b6eeb87"
PRIOR_PACKET_ROOTS = (
    P / "actual06-first-capture01/packets",
    P / "actual07-authorized-wave01-capture02/packets",
    P / "actual07-authorized-wave02-capture02/packets",
)


def verified_path(binding):
    path = ROOT / binding["path"]
    assert sha(path) == binding["sha256"], path
    return path


def exact_targets(catalog, view, task_id, plan):
    work_id = plan["work_item_id"]
    work = catalog.execute(
        "SELECT work_kind,status,decision_id FROM reconstruction_work_items WHERE id=?", (work_id,),
    ).fetchone()
    assert work is not None and tuple(work) == ("reconstruct", "todo", plan["decision_id"]), task_id
    assert not catalog.execute(
        "SELECT 1 FROM work_claims WHERE work_item_id=? AND state='active'", (work_id,),
    ).fetchone(), task_id
    observed = catalog.execute(
        "SELECT o.* FROM work_item_members m JOIN symbol_occurrences o ON o.id=m.occurrence_id "
        "WHERE m.work_item_id=?", (work_id,),
    ).fetchall()
    indexed = {(r["elf_sha256"], r["original_mangled"]): r for r in observed}
    assert len(indexed) == len(plan["exact_originals"]), task_id
    targets = []
    for item in plan["exact_originals"]:
        elf, name = item["original_elf_sha256"], item["mangled"]
        row = indexed[elf, name]
        assert (row["original_address"], row["original_size"]) == (item["address"], item["size"]), task_id
        assert item["anchor"] in {row["id"], row["catalog_anchor"]}, task_id
        assert item.get("catalog_anchor", row["catalog_anchor"]) == row["catalog_anchor"], task_id
        (firmware, role), = catalog.execute(
            "SELECT DISTINCT firmware_version,role FROM binary_releases WHERE elf_sha256=?", (elf,),
        ).fetchall()
        target = dict(
            original_elf_sha256=elf, mangled=name, address=item["address"], size=item["size"],
            section=int(row["section_index"]), anchor=row["catalog_anchor"], firmware=firmware, role=role,
        )
        check_vendor_source_route(target)
        registry = view.c.execute("SELECT status FROM records WHERE elf=? AND mangled=?", (elf, name)).fetchone()
        assert registry is None or registry["status"] not in {"ready", "pending"}, task_id
        targets.append(target)
    check_parked_assignment(task_id, work_id, targets)
    return targets


def main():
    admission_path = Path(sys.argv[1]).resolve(strict=True)
    output = Path(sys.argv[2]).resolve()
    assert output.is_relative_to(P) and not output.exists()
    assert sha(PROJECTION) == PROJECTION_SHA256 and sha(RM_PROBE) == RM_PROBE_SHA256
    plan, probe = read(PROJECTION), read(RM_PROBE)
    assert read(verified_path(plan["accepted65"]))["accepted_tasks"] == 65
    contract_file = verified_path(plan["proposal"])
    binder = verified_path(plan["isolation_guard"])
    assert "For every mutating shell call" in binder.read_text()
    register = S.parent / "graph/actual08/VERIFIED.json"
    receipt = read(register)
    active_path = ROOT / "dependency-graph/ACTIVE.json"
    active = read(active_path)
    assert active == receipt["active"] and not receipt["pending_or_unregistered"]
    state = guard(ROOT, active)
    channel = plan["slchannel_successor"]
    verified_path(channel["apply"])
    verified_path(channel["plan"])
    for path, row in channel["sources"].items():
        assert checked_digest(ROOT, ROOT / path) == state["files"][path]["sha256"] == row["current"]
    for path, digest in probe["actual08_frozen_source_paths"].items():
        assert checked_digest(ROOT, ROOT / path) == state["files"][path]["sha256"] == digest

    prerequisite_ids = {x for t in plan["tasks"].values() for x in t["prior_live_required"]}
    prerequisite_ids.update(channel["exact_tasks"])
    checked, targets = {}, {}
    catalog, pointer = active_index(ROOT)
    with closing(catalog), adapter.snapshot(ROOT / "uc-library") as view, batch_validation(ROOT):
        for name in sorted(prerequisite_ids):
            packet, = [root / name / "request.json" for root in PRIOR_PACKET_ROOTS
                       if (root / name / "request.json").is_file()]
            checked[name] = [
                verify_record(view, item["original_elf_sha256"], item["mangled"], name)
                for item in read(packet)["targets"]
            ]
        for task_id, task in plan["tasks"].items():
            targets[task_id] = exact_targets(catalog, view, task_id, task)
    verify_planned_equivalence([
        dict(task_id=name, existing_work_item_id=plan["tasks"][name]["work_item_id"], targets=row)
        for name, row in targets.items()
    ])

    # Source bindings cover the actual current owned sources, previous compiler
    # observations, and the explicit cross-owner reader relations established
    # from the typed canonical and native contract.
    typed_reads = {
        "cycle20_g01_s20": ("uc-library/include/presonus/SLChannel.hpp",
                            "uc-library/src/Presonus/SLChannel.cpp"),
        "cycle20_g07_r22": tuple(probe["actual08_frozen_source_paths"]),
        "cycle20_g10_s17": ("uc-library/include/presonus/mixer_state/MixerState.hpp",),
        "cycle20_g10_s18": ("uc-library/include/presonus/mixer_state/MixerState.hpp",),
    }
    waves, started = [], set()
    for index, members in enumerate(plan["current_order_projection"], 1):
        inventory = P / f"actual08-final10-projected-wave{index:02}-inventory01/INVENTORY.json"
        staged = {row["task_id"]: row for lane in read(inventory)["lanes"] for row in lane["tasks"]}
        assert set(staged) == set(members)
        groups = {}
        for task_id in members:
            assert task_id not in started
            started.add(task_id)
            task = plan["tasks"][task_id]
            owner = "_".join(task_id.split("_")[:2])
            assert staged[task_id]["targets"] == targets[task_id]
            assert sorted(staged[task_id]["production"]) == sorted(task["owned"])
            declared = set(typed_reads.get(task_id, ()))
            observations = list(previous_compiler_deps(task["owned"]))
            reads = declared | set().union(*(deps for _, deps in observations))
            read_hashes = {path: checked_digest(ROOT, ROOT / path) for path in sorted(reads)
                           if (ROOT / path).is_file()}
            groups.setdefault(owner, []).append(dict(
                task=task_id, work_item_id=task["work_item_id"], originals=targets[task_id],
                owned_files=task["owned"], observed_source_hashes=read_hashes,
                previous_compiler_observations=[meta for meta, _ in observations],
            ))
        writers = {path: owner for owner, entries in groups.items()
                   for entry in entries for path in entry["owned_files"]}
        conflicts = [(path, writers[path], owner) for owner, entries in groups.items()
                     for entry in entries for path in entry["observed_source_hashes"]
                     if path in writers and writers[path] != owner]
        if conflicts:
            raise ValueError(f"Refine phase {index} on real current input overlaps: {conflicts}")
        assert all(1 <= len(entries) <= 10 for entries in groups.values())
        waves.append(dict(wave=index, owners=groups, exact_count=len(members), native_inventory=ref(inventory)))
    assert started == set(targets) and [row["exact_count"] for row in waves] == [7, 2, 1]
    original_keys = {(x["original_elf_sha256"], x["mangled"], x["address"], x["size"])
                     for originals in targets.values() for x in originals}
    assert len(original_keys) == sum(map(len, targets.values())) == 18
    assert read(active_path) == active and sha(binder) == plan["isolation_guard"]["sha256"]
    save(output, dict(
        status="exact read-only final 10 for separate Root approval",
        observed_utc=datetime.now(timezone.utc).isoformat(),
        registered_graph=ref(register), active=active, verified_file_count=len(state["files"]),
        canonical_admission=ref(admission_path), exact_provider_records=checked,
        rm_roster_probe=ref(RM_PROBE), immutable_contracts=ref(contract_file),
        protected_source_transition=channel, worker_isolation_guard=ref(binder), waves=waves,
        cross_phase_release=plan["source_order_reason"], total_tasks=10, total_originals=18,
        claims_or_dispatch_mutated=False,
    ))
    print(output, sha(output), len(checked), sum(map(len, checked.values())))


if __name__ == "__main__":
    main()
