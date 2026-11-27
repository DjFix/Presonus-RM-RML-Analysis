"""Generate exact read-only final10 proposal input for maintained inventory."""
from collections import defaultdict
from contextlib import closing
from pathlib import Path
import hashlib
import json
import sqlite3

from verify_actual08_final10_approval import PROJECTION, PROJECTION_SHA256
from project_actual07_partitions import P, ROOT
from packet_cycle import read, save
from context_runtime import sha
from execution_review import _node_identities, collect
from dedup_work import active_index


def candidate_for(contract, native, catalog, identities):
    original = contract["exact_originals"][0]
    key = tuple(original[k] for k in ("original_elf_sha256", "mangled", "address", "size"))
    elf, mangled, address, size = key
    native_id, = identities[key]
    assert native_id == original["native_id"]
    candidate = contract["source_proposal"].copy()
    previous_target = candidate.get("target", {})
    assert not previous_target or previous_target["native_id"] == native_id
    node = catalog.execute(
        "SELECT id,catalog_anchor,section_index FROM symbol_occurrences WHERE "
        "elf_sha256=? AND original_mangled=? AND original_address=? AND original_size=?", key,
    ).fetchone()
    assert original["anchor"] in {node["id"], node["catalog_anchor"]}
    assert original.get("catalog_anchor", node["catalog_anchor"]) == node["catalog_anchor"]
    (firmware, role), = catalog.execute(
        "SELECT DISTINCT firmware_version,role FROM binary_releases WHERE elf_sha256=?", (elf,),
    ).fetchall()
    target = dict(
        previous_target, elf_sha256=elf, original_mangled=mangled,
        original_address=address, original_size=size, catalog_anchor=node["catalog_anchor"],
        section_index=node["section_index"], native_id=native_id, id=node["id"], firmware=firmware, role=role,
    )
    requested = dict(original_elf_sha256=elf, mangled=mangled, address=address, size=size)
    routes = []
    for edge in collect(native, [requested], identities).values():
        dest = edge.get("destination")
        row = native.execute("SELECT metadata FROM nodes WHERE id=?", (dest,)).fetchone() if dest else None
        meta = json.loads(row["metadata"]) if row else {}
        label = meta.get("demangled") or meta.get("mangled")
        routes.append(dict(kind=edge["kind"], site=edge["site"], native_id=dest,
                           target_names=[label] if label else [], routing="exact scoped review required"))
    (body,) = native.execute("SELECT payload FROM bodies WHERE id=?", (native_id,)).fetchone()
    assert json.loads(body)["instructions"]
    candidate.update(target=target, native_body_sha256=hashlib.sha256(body.encode()).hexdigest(),
                     direct_boundaries=routes)
    exact_members = []
    for item in contract["exact_originals"]:
        fields = tuple(item[key] for key in ("original_elf_sha256", "mangled", "address", "size"))
        occurrence = catalog.execute(
            "SELECT o.id,o.catalog_anchor FROM work_item_members m JOIN symbol_occurrences o "
            "ON o.id=m.occurrence_id WHERE m.work_item_id=? AND o.elf_sha256=? "
            "AND o.original_mangled=? AND o.original_address=? AND o.original_size=?",
            (contract["work_item_id"], *fields),
        ).fetchone()
        assert item["anchor"] in {occurrence["id"], occurrence["catalog_anchor"]}
        assert item.get("catalog_anchor", occurrence["catalog_anchor"]) == occurrence["catalog_anchor"]
        exact_members.append(dict(elf=fields[0], mangled=fields[1], anchor=occurrence["catalog_anchor"]))
    candidate["covered_originals"] = exact_members
    candidate.setdefault("bounded_selection_work", contract["typed_provider_and_replay_contract"])
    for key in ("prior_history", "dependency_blockers", "co_owned_dependencies"):
        candidate.setdefault(key, [])
    return candidate


def main():
    assert sha(PROJECTION) == PROJECTION_SHA256
    projection = read(PROJECTION)
    contract_file = ROOT / projection["proposal"]["path"]
    assert sha(contract_file) == projection["proposal"]["sha256"]
    contracts = {item["task"]: item for item in read(contract_file)["contracts"]}
    native_pointer = read(ROOT / "dependency-graph/NATIVE_ACTIVE.json")
    path = ROOT / native_pointer["database"]
    assert sha(path) == native_pointer["sha256"]
    catalog, _ = active_index(ROOT)
    with closing(catalog), closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as native:
        native.row_factory = sqlite3.Row
        identities = _node_identities(native)
        for wave, order in enumerate(projection["current_order_projection"], 1):
            entries = defaultdict(list)
            scopes = defaultdict(dict)
            for name in order:
                contract = contracts[name]
                lane = int(contract["lane"])
                entries[lane].append(candidate_for(contract, native, catalog, identities))
                owned = dict(
                    scope=contract["scope"],
                    owned_headers=[p for p in contract["owned_files"] if Path(p).suffix in (".h",".hpp")],
                    owned_sources=[p for p in contract["owned_files"] if Path(p).suffix in (".cpp",".cc")],
                )
                assert scopes[lane].setdefault(contract["scope"], owned) == owned
            lanes = [dict(lane=lane, candidates=rows, scope_ownership=list(scopes[lane].values()))
                     for lane, rows in entries.items()]
            save(P / f"actual08-final10-projected-wave{wave:02}-proposal01.json",
                 dict(lanes=lanes, staged_read_only=True))


if __name__ == "__main__":
    main()
