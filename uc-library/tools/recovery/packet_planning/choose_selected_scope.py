"""Propose a maximal exact compatible selected subset, preserving local work closure."""
import argparse
from functools import lru_cache
from itertools import combinations
from pathlib import Path
import sys

from packet_cycle import ROOT, read, reference, save
from context_runtime import sha

parser=argparse.ArgumentParser(description=__doc__)
for name in ("manifest","batch","audit","output"):
    parser.add_argument(name,type=Path)
parser.add_argument("--partition",action="store_true",
    help="Partition selected tasks into sequential scopes and keep shared owned source files together")
parser.add_argument("--first-owner", help="Keep every packet of this exact logical owner in the first partition")
parser.add_argument("--defer-first-owner", help="Exclude this exact owner only from the first partition")
args=parser.parse_args()
if (args.first_owner or args.defer_first_owner) and not args.partition:
    raise ValueError("Owner sequencing applies only to complete actual partitions")
manifest_file,batch,audit,output=args.manifest,args.batch,args.audit,args.output
manifest=read(manifest_file)
owner={Path(p).name:g["task_name"] for g in manifest["groups"] for p in g["packets"]}
contexts, requests = {}, {}
for task,lane in owner.items():
    path=batch/"packets"/task
    context=read(path/"context.json")
    request=read(path/"request.json")
    if context["task_sha256"]!=sha(path/"request.json") or context["task_id"]!=task:
        raise ValueError("Context task identity/bytes mismatch "+task)
    contexts[task]=context
    requests[task]=request
ids={r["work_binding"]["work_item_id"]:i for i,r in requests.items()}
predecessors={i:{ids[k] for k in r["included_dependency_work"] if ids[k]!=i}
              for i,r in requests.items() if r.get("included_dependency_work")}
if args.partition:
    for task,providers in [(task,tuple(needs)) for task,needs in predecessors.items()]:
        for provider in providers:
            predecessors.setdefault(provider,set()).add(task)
writes={i:set(r["owned_files"]) for i,r in requests.items()}
reads={i:set(c["selected_file_sha256"]) for i,c in contexts.items()}
pairs={}
for a,b in combinations(sorted(owner),2):
    if owner[a]==owner[b]:
        if args.partition and writes[a]&writes[b]:
            predecessors.setdefault(a,set()).add(b)
            predecessors.setdefault(b,set()).add(a)
        continue
    paths=(writes[a]&writes[b]) | (writes[a]&reads[b]) | (writes[b]&reads[a])
    if paths:
        pairs[(a,b)]=sorted(paths)


def remove(current, items):
    current=current-set(items)
    while True:
        missing={task for task in current if not predecessors.get(task,set())<=current}
        if not missing:
            return frozenset(current)
        current-=missing


def score(current):
    impl={i for i in current if requests[i]["mode"]=="reconstruct"}
    # Prioritize real implemented work, added original coverage, then kept lead-time lanes.
    return (len(impl),len(current),sum("_s" in item for item in impl),
            len({owner[i] for i in current}),tuple(sorted(current,reverse=True)))


@lru_cache(maxsize=None)
def choose(current, required=frozenset()):
    if not required <= current:
        return None
    conflicts=[pair for pair in pairs if set(pair)<=current]
    if not conflicts:
        return current
    degrees={i:sum(i in pair for pair in conflicts) for i in current}
    left,right=max(conflicts,key=lambda pair:sum(degrees[i] for i in pair))
    branches = (choose(remove(current,{item}), required) for item in (left,right))
    return max((branch for branch in branches if branch is not None), key=score, default=None)


bad=set(read(audit)["direct_unavailable_behavior"])
required_first=frozenset(task for task,lane in owner.items() if lane==args.first_owner)
deferred_first=frozenset(task for task,lane in owner.items() if lane==args.defer_first_owner)
if (args.first_owner and not required_first) or (args.defer_first_owner and not deferred_first):
    raise ValueError("Approved first or deferred group absent from exact capture")
active=choose(remove(frozenset(owner),bad|deferred_first),required_first)
if active is None:
    raise ValueError("No compatible actual selected scope retaining approved first owner")
other=set(owner)-active
scopes={}
if args.partition:
    if bad:
        raise ValueError("Exact unavailable behavior dependencies must be reviewed before a full partition")
    remaining=frozenset(owner)
    while remaining:
        chosen=active if not scopes else choose(remaining)
        if not chosen:
            raise ValueError("No compatible complete owned scope in "+str(sorted(remaining)))
        scopes[f"scoped{len(scopes)+1:02}"]=sorted(chosen)
        remaining=remaining-chosen
save(output,dict(wave=reference(manifest_file,"review_record","Full actual selected manifest"),
    selected_generation=sorted({c["generation_sha256"] for c in contexts.values()}),
    gate_audit=reference(audit,"review_record","Parked exact behavior dependency audit"),
    conflicts=[dict(first=a,second=b,paths=paths) for (a,b),paths in pairs.items()],
    required_same_owner={k:sorted(v) for k,v in predecessors.items()},
    active=sorted(active),defer=sorted(other),scopes=scopes,scoped_claims_unchanged=True,
    first_owner=args.first_owner,defer_first_owner=args.defer_first_owner,
    original_and_audit_counts={"implementation":score(active)[0],"audit_only":len(active)-score(active)[0]}))
print("Active",len(active),"deferred",len(other),"partition",[len(x) for x in scopes.values()],";",*sorted(other))
