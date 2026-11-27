"""Convert site-specific lane review bindings into contract input."""
from pathlib import Path
import sys
from packet_cycle import read, reference, save

i, spec_path, o = map(Path, sys.argv[1:])
spec = read(spec_path)
core = "third_party/ccl-framework/core/"
runtime = ["uc-library/tests/recovery/real10_g04_s08/native.py"]
arithmetic = {"__aeabi_fcmpgt", "__aeabi_f2iz", "__fixsfsi", "__aeabi_i2f", "__floatsisf",
              "__divsf3", "__aeabi_fdiv", "__extendsfdf2", "__aeabi_f2d"}

def refs(paths, scope):
    return [reference(p, "provider_source" if p.startswith(core) else
                      {"hpp": "cpp_declaration", "cpp": "cpp_implementation"}.get(p.rsplit(".", 1)[1], "review_record"),
                      scope) for p in paths]

def ccl(name):
    return [core + name + ".h", core + name + ".cpp"]

def generic(name):
    if name.startswith("Core::Portable::Parameter::"):
        return ("pinned_provider", ccl("portable/coreparams"), "Independently observe the exact named parameter call, arguments, and effect on a real CCL parameter and observer.")
    if name.startswith("Core::Portable::Component::"):
        return ("pinned_provider", ccl("portable/corecomponent"), "Independently observe exact named operation, receiver and effects in actual CCL component tree.")
    if name == "Core::DebugPrintf(char const*, ...)":
        return ("pinned_provider", ccl("system/coredebug"), "Observe exact native log format and values and real pinned provider behavior in canonical build profile.")
    if name in arithmetic:
        return ("existing_implementation", runtime, "Use the original runtime target and compare independently observed host numerical outcome. The prior native runner is method evidence.")
    raise ValueError("No reviewed provider for " + name)

review = {}
for lane in read(i)["lanes"]:
    rows = lane["tasks"]
    by_native = {identity: row for row in rows
                 for identity in row.get("native_ids", [row["candidate"]["target"]["native_id"]])}
    execution_index = {row["task_id"]: index for index, row in enumerate(rows)}
    for row in rows:
        task_id = row["task_id"]
        candidate = row["candidate"]
        objective = candidate["bounded_selection_work"]
        deps = {}
        canonical = [p for p in row["production"] if Path(p).is_file()]
        for key, boundary in row["boundaries"].items():
            obs = boundary["observed"]
            names = boundary["routing_context"]["target_names"]
            label = "; ".join(names) or f"ARM indirect receiver at ELF site {obs['site']:#x}"
            extra = {}
            if obs["kind"] == "ARM_INDIRECT_REVIEW_CANDIDATE":
                kind, files, reason = spec["indirect"][str(obs["site"])]
            elif obs.get("destination") in by_native:
                provider = by_native[obs["destination"]]
                if (execution_index[provider["task_id"]] > execution_index[task_id] or
                        (provider["task_id"] == task_id and obs["source"] != obs["destination"])):
                    raise ValueError("Included provider must occur first")
                kind, files = "included_work", [p for p in provider["production"] if Path(p).is_file()]
                extra.update(work_item_id=provider["candidate"]["work_item_id"], owned_files=provider["production"])
                reason = (f"Exact self-recursion into {label}; independently exercise recursive and terminating branches."
                          if provider["task_id"] == task_id else
                          f"Implement and independently validate exact {label} in earlier co-owned packet and compare this call's ordering and arguments.")
            else:
                bindings = {**spec["direct"], **spec.get("direct_by_task", {}).get(task_id, {})}
                resolved = [bindings[name] if name in bindings else generic(name) for name in names]
                if not resolved or any(r != resolved[0] for r in resolved[1:]):
                    raise ValueError("Review multiple native provider identities explicitly: " + label)
                kind, files, reason = resolved[0]
            deps[key] = dict(kind="dependency", reason=reason, dependency=dict(
                kind=kind, name=label, binding_domain=reason, evidence=refs(files, reason) + [row["native"]], **extra))
        assignments = {
            "declarations": "Resolve declaration from actual evidence and preserve unencoded original uncertainty.",
            "state": objective,
            "lifecycle": "Preserve canonical lifetimes and observe receiver/provider state and observer effects independently.",
            "providers": "Resolve each in-domain native binding and compare actual host provider behavior. Record a blocker if an external provider is unavailable.",
        }
        oracle = ("Verify exact original ELF and section-mapped bytes, execute the original ARM application's "
                  "instructions, observe genuine source providers independently, then compile, format, check symbol "
                  "mangling and replay. Use actual canonical compile/link contracts.")
        namespace = candidate["scope"].rpartition("::")[0] or candidate["scope"].split("::")[0]
        review[task_id] = dict(
            target=row["target"], work_item_id=candidate["work_item_id"], native_evidence_sha256=row["native"]["sha256"],
            reviewer=spec["reviewer"], namespace=namespace, objective=objective, domain=spec["domain"],
            requirements={name: dict(status="bounded_work", reason=text,
                evidence=refs(canonical, "Existing canonical owned scope"),
                work=dict(objective=text, oracle_plan=oracle, owned_files=row["production"]))
                for name, text in assignments.items()}, execution_boundaries=deps)
save(o, {"smaller_batch_authorization": "Root authorized reviewed rolling lane preparation in the 10x20 cycle.", "tasks": review})
