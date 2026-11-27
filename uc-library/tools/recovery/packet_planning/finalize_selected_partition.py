"""Validate independent selected branches and finalize them in one frozen environment."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import fcntl
import importlib.util
import sys
import time

from packet_cycle import CYCLE, ROOT, read, reference, rel, save
from context_batch import Environment, check_inputs, check_registry_records
from context_resources import choose_limits
from context_runtime import sha
from context_work_batch import BatchWorkValidator
from early_conflicts import SelectedReadGuard

batch,manifest_path,partition_path,out=(Path(raw).resolve() for raw in sys.argv[1:])
if not all(path.resolve().is_relative_to(CYCLE) for path in (batch,manifest_path,partition_path,out)):
    raise ValueError("Use cycle-local paths")
if out.exists():
    raise ValueError("Use fresh result directory")
run=importlib.util.spec_from_file_location("select_context_operator",ROOT/"uc-library/tools/recovery/select_context.py")
operator=importlib.util.module_from_spec(run)
run.loader.exec_module(operator)
started=time.monotonic()
with (batch/"coordinator.lock").open("rb") as lock:
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    frozen=read(batch/"FROZEN.json")
    if frozen["manifest_sha256"]!=sha(manifest_path) or (batch/"BATCH_DISPATCH.json").exists():
        raise ValueError("Selection does not match retained original freeze")
    if not any("Early selected-read conflict" in read(x)["error"] for x in batch.glob("attempt-*/FAILED.json")):
        raise ValueError("Expected actual retained selected-read failure")
    partitions=read(partition_path)["scopes"]
    manifest=read(manifest_path)
    original=[path for group in manifest["groups"] for path in group["packets"]]
    paths={Path(path).name:path for path in original}
    flat=[item for items in partitions.values() for item in items]
    if len(flat)!=len(paths) or set(flat)!=set(paths):
        raise ValueError("Partition must cover each exact previously selected packet once")
    entries={p:read(ROOT/p/"context.json") for p in original}
    requests={p:read(ROOT/p/"request.json") for p in original}
    hashes={p:sha(ROOT/p/"request.json") for p in original}
    expected={"manifest":rel(batch/"BATCH_DISPATCH.json"),"state":"pending","version":1}
    for p in original:
        if entries[p]["task_sha256"]!=hashes[p] or entries[p]["state"] not in ("selected","dispatch_ready"):
            raise ValueError("Unbound or invalid selected context "+p)
        if read(ROOT/p/"BATCH_MEMBER.json")!=expected or (ROOT/p/"DISPATCH.json").exists():
            raise ValueError("Original pending publication is absent "+p)
    groups={}
    for scope,wanted in partitions.items():
        subset={paths[name] for name in wanted}
        selected=[]
        for group in manifest["groups"]:
            order=[path for path in group["execution_order"] if path in subset]
            if order:
                selected.append(dict(group,packets=order,execution_order=order))
                reqs=[requests[p] for p in order]
                needs={dep for r in reqs for dep in r.get("included_dependency_work",[])}
                if not needs <= {r["work_binding"]["work_item_id"] for r in reqs}:
                    raise ValueError("Required provider work removed from "+scope)
        guard=SelectedReadGuard({p:requests[p] for p in subset},frozen["inputs"]["active"]["state_sha256"],
                               {p:hashes[p] for p in subset},selected)
        for p in sorted(subset):
            guard.check(p,entries[p],requests[p])
        groups[scope]=selected
    save(out/"PLAN.json",dict(groups=groups,frozen=reference(batch/"FROZEN.json","review_record","Retained immutable original freeze"),
         partition=reference(partition_path,"review_record","Actual exact compatible partitions"),
         original_context_sha256={p:sha(ROOT/p/"context.json") for p in original},selection_replay=False))
    unfinished=[p for p in original if entries[p]["state"]=="selected"]
    if unfinished:
        env=Environment(ROOT,batch)
        try:
            env.check_previous()
            env.pin_images()
            if env.images!=read(batch/"SNAPSHOT.json")["images"]:
                raise ValueError("Unexpected image drift")
            env.start()
            with (ROOT/"dependency-graph/state/context.lock").open("rb") as graph:
                fcntl.flock(graph,fcntl.LOCK_SH)
                check_inputs(ROOT,operator,frozen["inputs"])
                check_registry_records(operator,list(requests.values()),"Partition work records changed")
                validator=BatchWorkValidator(ROOT)
                try:
                    for p in original:
                        validator.validate(entries[p],p)
                    validator.finish()
                finally:
                    validator.close()
                limits=choose_limits("auto",len(unfinished))
                save(out/"RESOURCES.json",limits)

                def slice_packet(path):
                    if not (ROOT/path/"source-slices.json").exists():
                        env.slice(path,"cycle20-partition-slice-"+Path(path).name+"-"+str(time.time_ns()))

                with ThreadPoolExecutor(max_workers=limits["limits"]["slicing"]) as pool:
                    list(pool.map(slice_packet,unfinished))
                errors=env.selector("finalize",unfinished,"cycle20-partition-finalize-"+str(time.time_ns()))
                if errors:
                    raise ValueError(f"Partition exact finalization failures: {errors}")
                check_inputs(ROOT,operator,frozen["inputs"])
                check_registry_records(operator,list(requests.values()),"Partition work records changed after finalization")
        finally:
            env.close()
    if not all(read(ROOT/p/"context.json")["state"]=="dispatch_ready" for p in original):
        raise ValueError("An exact partition packet did not finalize")
    save(out/"COMPLETED.json",dict(context_sha256={p:sha(ROOT/p/"context.json") for p in original},
         wall_seconds=time.monotonic()-started,selection_replay=False,claims_changed=False,
         finalized=len(unfinished),previously_finalized=len(original)-len(unfinished)))
