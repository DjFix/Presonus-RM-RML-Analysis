"""Check sealed captured packet writes/reads across active waves."""
import argparse
from pathlib import Path
from packet_cycle import ROOT, read, rel, save
from context_runtime import sha
from context_publication import authorization

p=argparse.ArgumentParser(description=__doc__)
p.add_argument("--active", type=Path, nargs="+", required=True, help="Complete current BATCH_DISPATCH.json")
group=p.add_mutually_exclusive_group(required=True)
group.add_argument("--proposed", type=Path, help="Unclaimed candidate task manifest with declared reads")
group.add_argument("--selected", type=Path, help="Complete candidate BATCH_DISPATCH.json")
p.add_argument("--known-read-set",type=Path)
p.add_argument("--out", type=Path, required=True)
a=p.parse_args()
inputs=[]
owners={}
def snapshots(manifest, sealed):
    data=read(manifest)
    if sealed:
        if data.get("publication_state")!="complete":
            raise ValueError("No complete dispatch at "+str(manifest))
        lanes={w["arguments"]["task_name"]:w["packets"] for w in data["workers"]}
    else:
        lanes={g["task_name"]:g["packets"] for g in data["groups"]}
        task_paths={Path(t).stem:ROOT/t for t in data["tasks"]}
    known={} if sealed or not a.known_read_set else read(a.known_read_set)
    result={}
    for lane, packets in lanes.items():
        reads=set(known.get(lane,[])); writes=set()
        for packet in packets:
            path=ROOT/packet
            if sealed:
                authorization(ROOT,path)
                entry=read(path/"context.json")
                reads.update(entry["selected_file_sha256"])
                req=read(path/"request.json")
            else:
                req=read(task_paths[path.name])
                reads.update(req["declared_source_dependencies"])
            writes.update(req["owned_files"])
        result[lane]=(reads,writes)
    inputs.append({"manifest":rel(manifest),"sha256":sha(manifest),"sealed":sealed})
    return result
for path in a.active:
    for owner, paths in snapshots(path,True).items():
        if owner in owners:raise ValueError("Duplicate active lane "+owner)
        owners[owner]=paths
candidates=snapshots(a.selected or a.proposed,bool(a.selected))
conflicts=[]
for lane,(reads,writes) in candidates.items():
    if lane in owners:raise ValueError("Candidate duplicates active lane "+lane)
    for active,(active_reads,active_writes) in owners.items():
        for label, overlap in (
            ("write_write",writes&active_writes),
            ("candidate_writes_active_reads",writes&active_reads),
            ("active_writes_candidate_reads",active_writes&reads),
        ):
            if overlap:conflicts.append(dict(candidate=lane,active=active,kind=label,paths=sorted(overlap)))
save(a.out,dict(inputs=inputs,conflicts=conflicts,pass_=not conflicts,
                review_scope="Full selected file hashes and ownership for sealed inputs. Proposed reads prove declared/known overlap only."))
if conflicts:
    raise SystemExit("Cross-wave read/write conflict")
