"""Count current unique host obligations using the audited fixed workload policy."""
import hashlib
import json
import argparse
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'registry'))
from adapter import snapshot
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--repository',type=Path,default=Path(__file__).resolve().parents[3])
parser.add_argument('--registry-db',type=Path)
parser.add_argument('--output',type=Path)
args=parser.parse_args()
ROOT = args.repository.resolve()
LIB = ROOT/'uc-library'
OUT = args.output.resolve() if args.output else ROOT/'evidence/recovery/2026-10-27/file-transfer-panel-root/unique-current.json'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
policy_path = LIB/"candidates/unique-workload-audit/validation/unique-02/validation.json"
assert sha(policy_path) == "e5ff76ffef4b7b0254ead72cb791a21172e6c46d3d8a5f269cc7649d01a7687e"
policy = json.loads(policy_path.read_text())
wrappers = set(policy["core_keyed_initializers_additional_to_tracker_policy"])
assert len(wrappers) == 13
paths = [LIB/"tracking/coverage.json"]
before = {str(p.relative_to(ROOT)):sha(p) for p in paths}
coverage = json.loads(paths[0].read_text())
with snapshot(LIB,args.registry_db) as registry:
    ready=registry.ready['functions'];pending=registry.pending['functions'];registry_source=registry.provenance()
ready_keys = {(r["original_elf_sha256"],r["mangled"]) for r in ready}
pending_keys = {(r["original_elf_sha256"],r["mangled"]) for r in pending}
assert len(ready_keys)==len(ready) and len(pending_keys)==len(pending) and ready_keys.isdisjoint(pending_keys)
required, eligible = {}, set()
for role,data in coverage["roles"].items():
    identity = data["summary"]["sha256"]
    for row in data["symbols"]:
        if row["kind"] != "STT_FUNC" or not row["defined"] or not row["size"]:
            continue
        name = row["mangled"]
        required.setdefault(name,set()).add((identity,name))
        if not row["work_deferred"]:
            eligible.add(name)
names = set(required)
complete = {name for name,keys in required.items() if keys<=ready_keys}
any_ready = {name for name,keys in required.items() if keys&ready_keys}
pending_names = {name for name,keys in required.items() if keys&pending_keys}
manual_names = eligible-wrappers
manual_left = manual_names-complete
core_left = (names-manual_names)-complete
partial = manual_left&any_ready
declaration_pending = manual_left&pending_names-any_ready
uncompiled = manual_left-any_ready-pending_names
assert manual_left == partial|declaration_pending|uncompiled
assert len(partial)+len(declaration_pending)+len(uncompiled) == len(manual_left)
assert len(names)==10173
after = {str(p.relative_to(ROOT)):sha(p) for p in paths}
assert before==after
result = {
    "scope":"Defined nonempty host functions; exact original-name union; every applicable per-ELF role must be admitted ready. Raw MCU entries and eleven zero-size shared names are separate.",
    "unique_total":len(names),"complete_all_roles":len(complete),
    "ready_any_role":len(any_ready),"remaining_unique":len(names-complete),
    "manual_remaining":len(manual_left),"core_source_route_remaining":len(core_left),
    "manual_buckets":{"no_current_admitted_compiled_reconstruction":len(uncompiled),"declaration_pending":len(declaration_pending),"partial_role_ready":len(partial)},
    "per_elf_ready":len(ready),"per_elf_pending":len(pending),
    "partial_role_names":sorted(partial),"policy_sha256":sha(policy_path),
    "inputs":before,"registry_source":registry_source,"tool_sha256":sha(Path(__file__)),"global_inputs_unchanged":True,
}
OUT.parent.mkdir(parents=True,exist_ok=True)
with OUT.open("x") as stream: stream.write(json.dumps(result,indent=2)+"\n")
print(json.dumps(result))
