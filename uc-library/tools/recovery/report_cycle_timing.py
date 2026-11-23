#!/usr/bin/env python3
"""Report reconstruction timing from intact local receipt trees.

Run `report --help` for receipt aggregation or `compare --help` to compare
existing ledgers. Use the recorded receipt tree from the observation period
for historical replay. No repository, registry, graph or cost data is modified.

The official separate cost receipt is produced by
`uc-library/tools/recovery/collect_cycle_cost.py cutoff` with the saved cost
baseline. Record it after the actual cycle cutoff.
"""
import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[3]


def read(path):
    return json.loads(path.read_text())


def relative(path):
    return str(path.resolve().relative_to(ROOT))


def ref(path):
    with path.open("rb") as stream:
        return {"path": relative(path), "sha256": hashlib.file_digest(stream, "sha256").hexdigest()}


def timestamp(value):
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, timezone.utc)
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError(f"Timestamp needs timezone: {value}")
    return result.astimezone(timezone.utc)


def segment(kind, label, start, end, source, *, status, **extra):
    a, b = timestamp(start), timestamp(end)
    if b < a:
        raise ValueError((kind, label, start, end))
    return {
        "kind": kind, "label": label, "start_utc": a.isoformat(),
        "end_utc": b.isoformat(), "calendar_seconds": (b-a).total_seconds(),
        "status": status, "receipt": ref(source), **extra,
    }


def duration_segment(kind, label, start, seconds, source, *, status, **extra):
    a = timestamp(start)
    return segment(kind, label, a.isoformat(), (a + timedelta(seconds=seconds)).isoformat(),
                   source, status=status, command_wall_seconds=seconds, **extra)


def interval_stats(rows):
    intervals = sorted((timestamp(r["start_utc"]), timestamp(r["end_utc"])) for r in rows)
    if not intervals:
        return {"count": 0, "summed_seconds": 0, "union_seconds": 0}
    start, end = intervals[0]
    total = 0
    for a, b in intervals[1:]:
        if a > end:
            total += (end - start).total_seconds()
            start, end = a, b
        else:
            end = max(end, b)
    return {
        "count": len(rows),
        "summed_seconds": sum(r["calendar_seconds"] for r in rows),
        "union_seconds": total + (end-start).total_seconds(),
        "envelope_seconds": (max(b for _, b in intervals) - intervals[0][0]).total_seconds(),
    }


def intersection_seconds(left, right):
    pieces = []
    for a in left:
        for b in right:
            start = max(timestamp(a["start_utc"]), timestamp(b["start_utc"]))
            end = min(timestamp(a["end_utc"]), timestamp(b["end_utc"]))
            if end > start:
                pieces.append({"start_utc": start.isoformat(), "end_utc": end.isoformat(),
                               "calendar_seconds": (end-start).total_seconds()})
    return interval_stats(pieces)["union_seconds"]


def packet_intervals():
    rows, unmeasured = [], []
    for log in sorted((CYCLE / "packeting").glob("*prepare*.log")):
        exit_path = log.with_suffix(".exit")
        if not exit_path.is_file():
            continue
        content = log.read_text(errors="replace")
        measured = re.findall(r"(?m)^real (\d+(?:\.\d+)?)$", content)
        if len(measured) != 1:
            unmeasured.append({
                "label": log.stem, "exit": ref(exit_path), "log": ref(log),
                "returncode": int(exit_path.read_text().strip()),
                "reason": "Outer command duration missing or ambiguous. Excluded from interval totals.",
            })
            continue
        seconds = float(measured[0])
        end = timestamp(log.stat().st_mtime)
        returncode = int(exit_path.read_text().strip())
        rows.append(segment(
            "packet_prepare", log.stem, (end-timedelta(seconds=seconds)).isoformat(),
            end.isoformat(), log, status="failed" if returncode else "passed",
            command_wall_seconds=seconds, exit=ref(exit_path),
            timestamp_basis="Outer GNU time duration anchored to final log mtime; estimates overlap to filesystem clock precision.",
            returncode=returncode, docker_snapshot_mount_failure=(
                log.stem in {"lane01-prepare01", "lane02-prepare02"} and returncode != 0
            ),
        ))
    return rows, unmeasured


def graph_details(registration, wrapper_failure):
    result = registration.get("result", {})
    if not result:
        return {}
    output = ROOT / result["out"]
    details = {}
    for name, key in (
        ("stage-budget.json", "staging"),
        ("publication-budget.json", "transfer"),
        ("stage-timings.json", "stage_timing"),
        ("publish.json", "publication_helper"),
    ):
        path = output / name
        expected = registration["evidence"].get(name)
        if not path.is_file() or not expected:
            continue
        receipt = ref(path)
        assert receipt["sha256"] == expected
        value = read(path)
        details[key] = {"receipt": receipt, "observed": value.get("observed"),
                        "seconds": value.get("wall_seconds", value.get("seconds"))}
    if wrapper_failure.is_file():
        details["postflight_exception"] = {"receipt": ref(wrapper_failure), **read(wrapper_failure)}
    return details


def graph_intervals(as_of):
    rows = []
    for job in sorted((CYCLE / "graph").glob("*/JOB.json")):
        run = job.parent
        completed, verified, failure = (run / (name + ".json") for name in ("COMPLETED", "VERIFIED", "FAILURE"))
        timer = run / "TIMER_STARTED.json"
        metadata = {"timer": ref(timer) if timer.is_file() else None}
        if completed.is_file():
            result = read(completed)
            registration = read(verified) if verified.is_file() else {}
            rows.append(segment(
                "live_graph", run.name, result["start_utc"], result["end_utc"], completed,
                status=("registered" if verified.is_file() else "command_passed") if result["returncode"] == 0 else "failed",
                command_wall_seconds=result["wall_seconds"], returncode=result["returncode"],
                verification=ref(verified) if verified.is_file() else None,
                registration_result=registration.get("result"),
                registered_generation=registration.get("active"),
                publication_details=graph_details(registration, failure),
                failure=ref(failure) if failure.is_file() else None, **metadata,
            ))
        else:
            rows.append(segment("live_graph", run.name, read(job)["started_utc"], as_of, job, status="in_progress", **metadata))
    return rows


def checks():
    result = []
    for commands in sorted(EVIDENCE.glob("linux-*/commands.json")):
        for row in read(commands):
            if "start_utc" not in row or "wall_seconds" not in row:
                continue
            result.append(duration_segment(
                "canonical_linux", commands.parent.name + "/" + row["label"], row["start_utc"],
                row["wall_seconds"], commands, status="passed" if row["returncode"] == 0 else "failed",
                returncode=row["returncode"],
            ))
    return result


def suite_counts():
    rows = []
    for log in sorted(EVIDENCE.glob("linux-*/tests.log")):
        output = log.read_text(errors="replace")
        summary = re.findall(r"(\d+)% tests passed(?:, (\d+) tests failed)? out of (\d+)", output)
        if not summary:
            rows.append({"job": log.parent.name, "status": "no_disposition_in_log", "receipt": ref(log)})
            continue
        _, failed, total = (int(x or 0) for x in summary[-1])
        completed = log.with_name("COMPLETED.json")
        if completed.is_file():
            formal = read(completed)
            assert formal["passed"] and formal["test_suites"] == total and failed == 0
        rows.append({
            "job": log.parent.name, "status": "failed" if failed else "passed",
            "total": total, "failed": failed, "passed": total-failed,
            "receipt": ref(log), "full_completion": ref(completed) if completed.is_file() else None,
        })
    return rows


def packet_disposition():
    sealed = set()
    failed = []
    batches = []
    for gate in sorted((CYCLE / "packeting").glob("*/BATCH_DISPATCH.json")):
        data = read(gate)
        if data.get("publication_state") != "complete":
            continue
        originals = set()
        for worker in data["workers"]:
            for packet in worker["packets"]:
                request = ROOT / packet / "request.json"
                if not request.is_file():
                    failed.append(relative(request))
                    continue
                originals.update(original_key(x) for x in read(request)["targets"])
        sealed.update(originals)
        batches.append({"receipt": ref(gate), "distinct_identities_in_batch": len(originals)})
    return {"dispatch_sealed_distinct_identities": len(sealed), "sealed_batches": batches,
            "sealed_requests_missing": sorted(set(failed))}


def original_key(original):
    return (original.get("elf_sha256", original.get("original_elf_sha256")),
            original.get("mangled", original.get("original_mangled")))


def handoff_data(acceptance):
    path = worker_handoff_path(acceptance)
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != acceptance["handoff_sha256"]:
        return None
    return read(path)


def check_cutoff(value, start, end):
    observed = timestamp(value)
    if not start <= observed <= end:
        raise ValueError(f"Timestamp {value} falls outside cycle bounds")
    return observed


def selected_rows(paths):
    primary, covered, identities = {}, {}, {}
    for path in paths:
        for lane in read(path)["lanes"]:
            for row in lane["candidates"]:
                ident = original_key(row["target"])
                task = row["task_id_override"]
                prior = primary.setdefault(task, {"lane": lane["lane"], "identity": ident})
                if prior != {"lane": lane["lane"], "identity": ident}:
                    raise ValueError(f"Conflicting primary implementation for {task}")
                owner = identities.setdefault(ident, task)
                if owner != task:
                    raise ValueError(f"Primary identity proposed under two tasks: {ident}")
                group = {ident} | {(r["elf"], r["mangled"]) for r in row.get("covered_originals", [])}
                for original in group:
                    if covered.setdefault(original, task) != task:
                        raise ValueError(f"Covered identity assigned to multiple tasks: {original}")
    return primary, identities, covered


def nominal_slots(primary, maps):
    """Accept only explicit same-lane replacement mappings from reviewed plans."""
    mapping = {}
    for path in maps:
        for record in read(path)["replacements"]:
            task, original = record["task"], record["replaces"]
            approval = record["disposition"]
            if approval not in {"root_approved_selection", "root_approved_replacement"}:
                continue
            if not re.fullmatch(r"cycle20_g\d{2}_r\d{2}", task) or not re.fullmatch(r"cycle20_g\d{2}_s\d{2}", original):
                raise ValueError(f"Invalid actual/nominal replacement mapping {task} -> {original}")
            if task[:12] != original[:12] or mapping.setdefault(task, original) != original:
                raise ValueError(f"Conflicting or cross-lane replacement {task} -> {original}")
    actual_to_slot = {}
    for task, row in primary.items():
        if re.fullmatch(r"cycle20_g\d{2}_r\d{2}", task):
            if task not in mapping:
                raise ValueError(f"Replacement proposal lacks explicit approved plan: {task}")
            slot = mapping[task]
        else:
            slot = task
        if int(slot.split("_")[1][1:]) != int(row["lane"]):
            raise ValueError(f"Proposed owner does not match primary lane: {task}")
        actual_to_slot[task] = slot
    return actual_to_slot


def retained_tasks(plans):
    tasks = {}
    for path in plans:
        for artifact in read(path)["tasks"]:
            task_file = ROOT / artifact
            task = read(task_file)
            exact = {original_key(row) for row in task["targets"]}
            previous = tasks.setdefault(task["task_id"], exact)
            if previous != exact:
                raise ValueError(f"Retained owner exact identities changed: {task['task_id']}")
    return tasks


def local_acceptance():
    windows, originals, unavailable = [], set(), []
    for path in sorted((CYCLE / "acceptance/receipts").glob("*.json")):
        record = read(path)
        if not {"returncode", "started_epoch", "seconds", "task_id"} <= record.keys():
            continue
        okay = record["returncode"] == 0
        windows.append(duration_segment(
            "local_acceptance", record["task_id"], record["started_epoch"], record["seconds"],
            path, status="passed" if okay else "failed", returncode=record["returncode"],
        ))
        if okay:
            handoff = handoff_data(record)
            if handoff is None:
                unavailable.append(ref(path))
            else:
                originals.update(original_key(row) for row in handoff["originals"])
    return windows, originals, unavailable


def applications():
    originals, receipts = set(), []
    for path in sorted((CYCLE / "integration").glob("*/apply/COMPLETED.json")):
        result = read(path)
        if not result.get("applied"):
            continue
        plan_path = path.parent.parent / "ACCEPTED_PLAN.json"
        plan_ref = ref(plan_path)
        if plan_ref["sha256"] != result["manifest_sha256"]:
            raise ValueError(f"Accepted plan hash changed: {plan_path}")
        tasks = read(plan_path)["tasks"]
        exact = {original_key(row) for task in tasks for row in task["originals"]}
        if len(tasks) != result["task_count"] or (None, None) in exact:
            raise ValueError(f"Applied manifest count differs: {path}")
        originals.update(exact)
        receipts.append({"result":ref(path), "plan":plan_ref,
                         "task_count":len(tasks), "exact_elf_identities":len(exact)})
    return originals, receipts


def sqlite_verified(evidence):
    rows, batches, request_ids = {}, [], set()
    for check in sorted(evidence.glob("*admission*/VERIFIED.json")):
        live, plan, notes = (check.with_name(name) for name in
                             ("LIVE.json", "COMMANDS_PLAN.json", "POSTADMISSION-NOTES.json"))
        if not (live.is_file() and plan.is_file()):
            continue
        result, verified, guard = read(live), read(check), read(plan)
        commit = result["sqlite_commit"]
        request_id = commit["request_id"]
        if request_id != verified["request_id"] or request_id in request_ids:
            raise ValueError(f"Duplicate or inconsistent SQLite request: {check}")
        request_ids.add(request_id)
        total = {kind:verified[kind] for kind in ("ready","pending")}
        if total != guard["after"]:
            raise ValueError(f"SQLite guard result differs: {check}")
        increment = {kind:total[kind]-guard["before"][kind] for kind in total}
        if sum(increment.values()) != verified["checked_new"] or any(n < 0 for n in increment.values()):
            raise ValueError(f"Unexpected classification transition: {check}")
        if notes.is_file():
            exact = {tuple(row["identity"]):row["status"] for row in read(notes)["rows"]}
            bound = Counter(exact.values())
            if any(bound[kind] != n for kind,n in increment.items()) or (rows.keys() & exact.keys()):
                raise ValueError(f"Unexpected exact admission disposition: {notes}")
            rows.update(exact)
        batches.append({"verified":ref(check), "live":ref(live), "guard":ref(plan),
                        "request_id":request_id, "new":increment,
                        "exact_notes":ref(notes) if notes.is_file() else None,
                        "incumbent_metadata_successors":len(commit.get("metadata_changed", []))})
    return rows, batches


def admissions(evidence):
    admitted, batches = {}, []
    for path in sorted(evidence.rglob("POSTADMISSION-VERIFIED.json")):
        verified = read(path)
        plan_ref = verified["artifacts"]["NOTES.json"]
        plan = ROOT / plan_ref["path"]
        if ref(plan) != plan_ref:
            raise ValueError(f"Postadmission plan proof changed: {plan}")
        rows = read(plan)["rows"]
        exact_status = Counter(row["status"] for row in rows)
        claimed_groups = {row["claim_id"] if "claim_id" in row else row["manifest"]["claim_id"] for row in rows}
        if (any(exact_status[k] != verified["verified_readiness_preserved"][k] for k in ("ready", "pending"))
                or len(rows) != verified["verified_catalog_note_appends"]
                or len(claimed_groups) != verified["verified_completed_claims"]):
            raise ValueError(f"Postadmission counts disagree: {path}")
        for row in rows:
            ident = tuple(row["identity"])
            if ident in admitted:
                raise ValueError(f"One original credited twice: {ident}")
            admitted[ident] = row
        batches.append({"verification": ref(path), "exact_status": exact_status,
                        "unique_completed_claims": len(claimed_groups)})
    return admitted, batches


def grouped_packet_windows(as_of):
    windows = []
    for run in sorted((CYCLE / "packeting").glob("*/attempt-*")):
        stamp = run.name.removeprefix("attempt-")
        if not stamp.isdecimal():
            continue
        completed, failed = run / "COMPLETED.json", run / "FAILED.json"
        receipt = completed if completed.is_file() else failed if failed.is_file() else None
        start = timestamp(int(stamp) / 1e9)
        launcher_start = run.parent.with_name(run.parent.name.removesuffix("-batch") + "-start.utc")
        if receipt and launcher_start.is_file():
            reported = timestamp(launcher_start.read_text().strip())
            if 0 <= (start-reported).total_seconds() <= 60:
                start = reported
        end = timestamp(receipt.stat().st_mtime if receipt else as_of)
        proof = receipt or run / "process.json"
        if proof.is_file() and end >= start:
            windows.append(segment(
                "grouped_packet_prepare", run.parent.name + "/" + run.name, start.isoformat(), end.isoformat(),
                proof, status=("completed" if receipt == completed else "failed" if receipt == failed else "in_progress"),
                timestamp_basis="Recorded launcher or attempt identifier start, anchored to terminal receipt mtime",
                internal_phases=read(receipt).get("timings", []) if receipt else [],
            ))
    return windows


def packet_launcher_attempts():
    """Use recorded clock/exit receipts for Actual05 recovery and Actual06 publication."""
    packet = CYCLE / "packeting"
    attempts = (
        ("Actual05 independent10 initial", "actual05-independent10-start.txt",
         "actual05-independent10-end.txt", "actual05-independent10-exit.txt",
         "actual05-independent10.log"),
        ("Actual05 independent10 retry", "actual05-independent10-retry-start.utc",
         "actual05-independent10-retry-end.utc", "actual05-independent10-retry-exit",
         "actual05-independent10-retry.log"),
        ("Actual05 independent10 recovery", "actual05-independent10-resume-start.utc",
         "actual05-independent10-resume-end.utc", "actual05-independent10-resume-exit",
         "actual05-independent10-resume.log"),
    )
    actual06_attempts = (
        ("Actual06 grouped preparation", "actual06-authorized42"),
        ("Actual06 maintained partition", "actual06-authorized42-partition"),
        ("Actual06 scoped publication 1", "actual06-authorized42-scoped01"),
        ("Actual06 scoped publication 2", "actual06-authorized42-scoped02"),
        ("Actual06 scoped publication 3", "actual06-authorized42-scoped03"),
    )
    attempts += tuple((label, root + "-start.utc", root + "-end.utc", root + "-exit", root + ".log")
                      for label, root in actual06_attempts)
    rows = []
    for name, start_name, end_name, exit_name, log_name in attempts:
        start, end, status, log = (packet / path for path in (start_name, end_name, exit_name, log_name))
        if not all(path.is_file() for path in (start, end, status, log)):
            continue
        first = start.read_text().strip().replace(",", ".")
        last = end.read_text().strip().replace(",", ".")
        code = int(status.read_text().strip())
        rows.append(segment(
            "packet_launcher_attempt", name, first, last, log, returncode=code,
            status="failed" if code else "completed",
            clock_receipts=[ref(start), ref(end), ref(status)],
            timestamp_basis="Actual recorded outer launcher start/exit clocks. May overlap internal grouped-packet receipt windows.",
        ))
    return rows


def worker_launches():
    launches = []
    for path in sorted((CYCLE / "workspaces").glob("*/LAUNCH.json")):
        data = read(path)
        if {"agent", "model", "mode", "observed_utc"} <= data.keys():
            launches.append({
                "agent":data["agent"], "model":data["model"], "mode":data["mode"],
                "observed_utc":timestamp(data["observed_utc"]).isoformat(),
                "receipt":ref(path),
            })
    return sorted(launches,key=lambda row: row["observed_utc"])


def worker_delivery_windows():
    rows, pending = [], []
    by_task = {}
    for path in sorted((CYCLE / "acceptance/receipts").glob("*.json")):
        receipt = read(path)
        if receipt.get("returncode") != 0 or "handoff" not in receipt:
            continue
        handoff = worker_handoff_path(receipt)
        if handoff_data(receipt) is not None:
            by_task.setdefault(receipt["task_id"], []).append((receipt["started_epoch"], handoff, path))
    for launch in sorted((CYCLE / "workspaces").glob("*/LAUNCH.json")):
        plan = launch.with_name("PLAN.json")
        metadata = read(launch)
        if not plan.is_file() or "observed_utc" not in metadata:
            continue
        started = timestamp(metadata["observed_utc"])
        task_ids = {Path(path).name for assignment in read(plan)["assignments"]
                    for path in assignment["packets"]}
        observations = {}
        for task in sorted(task_ids):
            for accept_start, handoff, accept_receipt in by_task.get(task, []):
                delivery = timestamp(handoff.stat().st_mtime)
                if started <= delivery <= timestamp(accept_start):
                    observations[task] = (delivery, accept_receipt)
                    break
        if set(observations) == task_ids and task_ids:
            end, accept_receipt = max(observations.values())
            rows.append(segment(
                "worker_delivery_envelope", launch.parent.name, started.isoformat(), end.isoformat(),
                launch,status="all_handoffs_observed", last_handoff_acceptance=ref(accept_receipt),
                timestamp_basis="Launch receipt to latest hash-bound handoff file mtime for all exact tasks",
                exact_tasks=sorted(task_ids),
            ))
        else:
            pending.append({"launch":ref(launch), "unmeasured_or_open_tasks":sorted(task_ids-observations.keys())})
    return rows,pending


def callable_groups(admitted):
    names = sorted({pair[1] for pair in admitted})
    if not names:
        return {"distinct_mangled_names": 0, "distinct_demangled_callables": 0, "abi_variant_identities": 0}
    demangled = subprocess.run(["c++filt"], text=True, capture_output=True,
                               check=True, input="\n".join(names)+"\n").stdout.splitlines()
    if len(demangled) != len(names):
        raise ValueError("Demangler failed to return one name per original")
    variant = re.compile(r"(?:C[123]|D[012])E|^_ZT[hv]")
    return {"distinct_mangled_names": len(names), "distinct_demangled_callables": len(set(demangled)),
            "abi_variant_identities": sum(bool(variant.search(pair[1])) for pair in admitted)}


def additional_windows(evidence):
    rows = {"graph_wrapper": [], "graph_postflight": [], "sqlite_admission": [], "dedup_review": [], "catalog_review": []}
    for path in sorted((CYCLE / "graph").glob("*/WRAPPER_TIMING.json")):
        data = read(path)
        run = path.parent
        state = ("verified" if (run / "VERIFIED.json").is_file() else
                 "already_current" if (run / "ALREADY_CURRENT.json").is_file() else "failed")
        rows["graph_wrapper"].append(segment(
            "graph_wrapper", run.name, data["start_utc"], data["end_utc"], path,
            status=state, command_wall_seconds=data["wall_seconds"],
        ))
    for path in sorted(evidence.rglob("*_COMMAND.json")):
        if path.name not in {"DRY_RUN_COMMAND.json", "LIVE_COMMAND.json"}:
            continue
        data = read(path)
        end = timestamp(path.stat().st_mtime)
        start = timestamp(data["start_utc"]) if "start_utc" in data else end - timedelta(seconds=data["seconds"])
        rows["sqlite_admission"].append(segment(
            "sqlite_admission", path.parent.name + "/" + path.stem, start.isoformat(), end.isoformat(),
            path, status="passed" if data["returncode"] == 0 else "failed",
            command_wall_seconds=data["seconds"], returncode=data["returncode"],
            timestamp_basis=("Maintained receipt start and filesystem finish" if "start_utc" in data else
                             "Maintained monotonic command duration anchored on receipt mtime"),
        ))
    for run in sorted((CYCLE / "graph").glob("actual*")):
        finished = run / "COMPLETED.json"
        verification = run / "VERIFIED.json"
        failed = run / "FAILURE.json"
        if not finished.is_file():
            continue
        start = read(finished).get("end_utc")
        if not start:
            continue
        if failed.is_file():
            error = read(failed)
            now = error.get("utc")
            if now and timestamp(now) >= timestamp(start):
                rows["graph_postflight"].append(segment(
                    "graph_postflight", run.name + " initial check", start, now, failed,
                    status="failed", check_failure=error.get("error")))
                start = now
        if verification.is_file():
            data = read(verification)
            end = data.get("verified_utc")
            if end and timestamp(end) >= timestamp(start):
                rows["graph_postflight"].append(segment(
                    "graph_postflight", run.name, start, end, verification,
                    status="verified", timestamp_basis="After command exit or observed initial postflight failure"))
    for start in sorted((CYCLE / "selection").rglob("CATALOG_RETRY_APPLY_START.utc")):
        base = start.parent
        end = base / "CATALOG_RETRY_APPLY_END.utc"
        receipt = base / "CATALOG_RETRY_APPLY01.json"
        clock = base / "CATALOG_RETRY_APPLY_TIME.log"
        if not all(path.is_file() for path in (end, receipt, clock)):
            continue
        result = read(receipt)
        elapsed = re.search(r"^real ([0-9.]+)$", clock.read_text(), re.MULTILINE)
        if not elapsed or result.get("dry_run") is not False or result.get("readiness_changed") is not False:
            raise ValueError(f"Invalid applied metadata-only catalog timing {receipt}")
        rows["catalog_review"].append(segment(
            "catalog_review", result["request_id"], start.read_text().strip(), end.read_text().strip(), receipt,
            status="passed", operation_count=result["operations"], command_wall_seconds=float(elapsed[1]),
            timestamp_basis="Recorded guarded metadata-only catalog operator with exact revisions, no readiness change.",
        ))
    measurements = []
    selection = CYCLE / "selection"
    for start in sorted(selection.rglob("REVIEW_START.utc")):
        review_dir = start.parent
        measurements.append((start, review_dir / "REVIEW_END.utc",
                             review_dir / "REVIEW_RECEIPT.json", review_dir / "REVIEW_TIME.log"))
    for start in sorted(selection.rglob("*.start.utc")):
        review_dir = start.parent
        prefix = start.name.removesuffix(".start.utc")
        measurements.append((start, review_dir / (prefix+".end.utc"),
                             review_dir / (prefix+".receipt.json"), review_dir / (prefix+".time.log")))
    for start, end, receipt, time_log in measurements:
        if not start.is_file():
            continue
        if not time_log.is_file():
            continue
        timing = time_log.read_text()
        measured = re.search(r"elapsed=([0-9.]+) status=([0-9]+)", timing)
        if not measured:
            measured = re.search(r"([0-9.]+) sec exit=([0-9]+)", timing)
        if measured:
            duration, outcome = float(measured.group(1)), int(measured.group(2))
        else:
            posix = re.search(r"^real ([0-9.]+)$", timing, re.MULTILINE)
            failure = re.search(r"Command exited with non-zero status ([0-9]+)", timing)
            if posix and failure:
                duration, outcome = float(posix.group(1)), int(failure.group(1))
            elif posix and end.is_file() and receipt.is_file():
                result = read(receipt)
                if not isinstance(result, dict) or result.get("status") not in ("verified", "rejected"):
                    raise ValueError(f"Missing successful guarded decision receipt {receipt}")
                duration, outcome = float(posix.group(1)), 0
            elif not end.is_file():
                continue  # GNU time creates its output stream before the command completes.
            else:
                raise ValueError(f"Invalid dedup review timing {time_log}")
        if end.is_file():
            finished = end.read_text().strip()
            basis = "Real command envelope including context-lock wait"
        elif outcome and receipt.is_file():
            finished = timestamp(time_log.stat().st_mtime).isoformat()
            basis = "Failed command with terminal time receipt mtime; wrapper exited before end timestamp"
        else:
            continue
        rows["dedup_review"].append(segment(
            "dedup_review", receipt.stem, start.read_text().strip(), finished,
            receipt, status="passed" if not outcome else "failed", outer_time=ref(time_log),
            command_wall_seconds=duration, returncode=outcome,
            timestamp_basis=basis,
        ))
    for command in sorted((CYCLE / "selection").glob("post-actual03-review*/**/*.command.json")):
        result = read(command)
        rows["dedup_review"].append(segment(
            "dedup_review", command.stem, result["start_utc"], result["end_utc"], command,
            status="passed" if result["returncode"] == 0 else "failed",
            returncode=result["returncode"], timestamp_basis="Exact maintained review command wall envelope",
        ))
    return rows


def canonical_command_accounting(evidence):
    applies = []
    for path in sorted((CYCLE / "integration").glob("*/apply/commands.json")):
        commands = read(path)
        applies.append({
            "scope": path.parent.parent.name,
            "receipt": ref(path),
            "commands": len(commands),
            "failed_commands": sum(row["returncode"] != 0 for row in commands),
            "summed_subprocess_seconds": sum(row["seconds"] for row in commands),
        })
    trackers = []
    postadmission = []
    for path in sorted(evidence.glob("*admission/TRACKER_TIMING.json")):
        data = read(path)
        trackers.append({"scope":path.parent.name, "receipt":ref(path),
                         "tracker_command_seconds":data["seconds"]})
    for verified in sorted(evidence.glob("*admission/POSTADMISSION-VERIFIED.json")):
        sqlite = verified.with_name("VERIFIED.json")
        tracker = verified.with_name("TRACKER_TIMING.json")
        mirror = verified.with_name("mirror-audit.json")
        if not sqlite.is_file():
            continue
        start = timestamp(sqlite.stat().st_mtime)
        end = timestamp(verified.stat().st_mtime)
        item = {"scope":verified.parent.name, "sqlite_verified":ref(sqlite),
                "postadmission_verified":ref(verified),
                "observed_receipt_gap_seconds":(end-start).total_seconds(),
                "time_basis":"VM101 receipt modification times, includes waits; not subprocess execution"}
        if tracker.is_file():
            item["tracker_timing"]=ref(tracker)
        if mirror.is_file():
            item["mirror_audit"]=ref(mirror)
        postadmission.append(item)
    return {"canonical_apply_subprocesses":applies, "tracker_runs":trackers,
            "postadmission_receipts":postadmission}


def quota_accounting(start, end, time_rows):
    path = CYCLE / "timing/QUOTA_OBSERVED01.json"
    if not path.is_file():
        return None
    receipt = read(path)
    observed = receipt["observations"]
    terminal = timestamp(observed["confirmed_coordinator_quota_terminal"]["utc"])
    resumed = timestamp(observed["coordinator_goal_became_active"]["utc"])
    left, right = max(start, terminal), min(end, resumed)
    is_observed = left < right
    window = [segment("quota_interruption", "coordinator observed",
                             left.isoformat(), right.isoformat(), path,
                             status="observed")] if is_observed else []
    overlap = {phase: intersection_seconds(window, rows)
               for phase, rows in time_rows.items()}
    process_phases = ("live_graph", "canonical_linux", "local_acceptance",
                      "packet_prepare", "grouped_packet_prepare", "sqlite_admission")
    elapsed = (right-left).total_seconds() if is_observed else 0
    return {
        "receipt":ref(path),
        "observed_coordinator_interruption_seconds_within_cycle":elapsed,
        "included_in_cycle_wall_seconds":True,
        "elapsed_seconds_less_observed_coordinator_interruption":(end-start).total_seconds()-elapsed,
        "observed_overlap_seconds_by_phase":overlap,
        "observed_union_overlap_of_measured_process_windows_seconds":
            intersection_seconds(window, [row for phase in process_phases
                                                 for row in time_rows.get(phase, [])]),
        "interpretation":"The worker delivery envelope can include idle time. These overlaps do not establish worker CPU usage or provider billing.",
    }


def summarize(args):
    request_path = CYCLE / "USER_START.json"
    request = read(request_path)
    start = timestamp(request["requested_utc"])
    end = timestamp(args.as_of)
    operational = check_cutoff(args.operational_end, start, end) if args.operational_end else None
    end_of_report = check_cutoff(args.commit_utc, operational, end) if args.commit_utc else None
    previous_path = args.previous
    previous = read(previous_path)["current"]
    if previous["report_commit"]["commit"] != request["baseline_commit"]:
        raise ValueError("Previous-cycle baseline differs")
    primary, selection, coverage = selected_rows(args.proposal)
    actual_to_slot = nominal_slots(primary, args.replacement_plan)
    if len(set(actual_to_slot.values())) > request["target_count"]:
        raise ValueError("Original selection exceeds requested denominator")
    retained = retained_tasks(args.historical_task_plan)
    if set(primary) & set(retained):
        raise ValueError("A retained task is also counted as a nominal primary slot")

    packets, packet_unmeasured = packet_intervals()
    accepts, accepted, unavailable = local_acceptance()
    deliveries, open_deliveries = worker_delivery_windows()
    graph = graph_intervals(operational.isoformat() if operational else args.as_of)
    linux = checks()
    applied, applied_receipts = applications()
    sqlite, sqlite_batches = sqlite_verified(args.evidence)
    admitted, batches = admissions(args.evidence)
    if any(sqlite.get(ident) != row["status"] for ident, row in admitted.items()):
        raise ValueError("Final claim completion differs from exact SQLite admission")
    if operational and (set(sqlite) != set(admitted) or any(row["status"] == "in_progress" for row in graph)):
        raise ValueError("An exact live admission or graph attempt lacks terminal verification")
    expected_by_task = {task: set() for task in primary}
    for original, task in coverage.items():
        expected_by_task[task].add(original)
    matching = {task: {original for original in originals
                       if original in admitted and admitted[original]["task"] == task}
                for task, originals in expected_by_task.items()}
    known_retained_admissions = {
        original for task, originals in retained.items() for original in originals
        if original in admitted and admitted[original]["task"] == task
    }
    completed_assignments = {task for task, originals in expected_by_task.items() if matching[task] == originals}
    completed_slots = {actual_to_slot[task] for task in completed_assignments}
    partial_slots = sorted({actual_to_slot[task] for task, coverage_ in matching.items()
                            if coverage_ and actual_to_slot[task] not in completed_slots})
    full_assignments_per_slot = Counter(actual_to_slot[task] for task in completed_assignments)
    nominal_counts = Counter(int(slot.split("_")[1][1:]) for slot in set(actual_to_slot.values()))
    time_rows = {"packet_prepare": packets, "grouped_packet_prepare": grouped_packet_windows(args.as_of), "local_acceptance": accepts,
                 "packet_launcher_attempt": packet_launcher_attempts(), "live_graph": graph, "canonical_linux": linux, "worker_delivery_envelope":deliveries,
                 **additional_windows(args.evidence)}
    return {
        "request": request, "request_receipt": ref(request_path),
        "cost_baseline": ref(CYCLE / "COST_REQUEST_BASELINE.json"),
        "as_of_utc": end.isoformat(), "elapsed_since_request_seconds": (end-start).total_seconds(),
        "operational_end_utc": operational.isoformat() if operational else None,
        "operational_seconds": (operational-start).total_seconds() if operational else None,
        "commit_utc": end_of_report.isoformat() if end_of_report else None,
        "report_commit_tail_seconds": (end_of_report-operational).total_seconds() if end_of_report else None,
        "report_commit": args.commit,
        "full_cycle_seconds_through_report_commit": (end_of_report-start).total_seconds() if end_of_report else None,
        "previous_cycle": {"receipt": ref(previous_path),
                           "operation_seconds": previous["operational_seconds"],
                           "full_cycle_seconds": previous["full_cycle_seconds"],
                           "target_accounting": previous["target_accounting"]},
        "selected_proposals": [ref(path) for path in args.proposal],
        "replacement_plans": [ref(path) for path in args.replacement_plan],
        "retained_task_plans": [ref(path) for path in args.historical_task_plan],
        "targets": {
            "requested_primary_worker_slots": request["target_count"],
            "proposed_primary_implementation_slots": len(set(actual_to_slot.values())),
            "proposed_exact_task_assignments_including_replacements": len(primary),
            "primary_implementation_slots_by_logical_worker": nominal_counts,
            "proposed_distinct_primary_elf_identities": len(selection),
            "proposed_distinct_covered_elf_identities": len(coverage),
            "locally_accepted_distinct_elf_identities": len(accepted),
            "canonical_applied_distinct_elf_identities": len(applied),
            "canonical_apply_receipts": applied_receipts,
            "sqlite_live_exact_elf_identities": len(sqlite),
            "sqlite_live_verified_counts": Counter(sqlite.values()),
            "sqlite_live_windows": sqlite_batches,
            "verified_admitted_distinct_elf_identities": len(admitted),
            "verified_admitted_distinct_implementation_tasks": len({row["task"] for row in admitted.values()}),
            "fully_admitted_primary_slots": len(completed_slots),
            "fully_admitted_replacements": sorted(task for task in completed_assignments if actual_to_slot[task] != task),
            "replacement_to_primary_slot": {t: s for t, s in sorted(actual_to_slot.items()) if t != s},
            "primary_slots_with_multiple_fully_admitted_actual_assignments": sorted(
                slot for slot, count in full_assignments_per_slot.items() if count > 1),
            "partially_admitted_primary_slots": partial_slots,
            "verified_admitted_inside_proposal": len(admitted.keys() & coverage.keys()),
            "verified_admitted_outside_proposal": sorted(admitted.keys() - coverage.keys()),
            "retained_implementation_tasks_planned": sorted(retained),
            "retained_elf_identities_verified_admitted": sorted(known_retained_admissions),
            "verified_admitted_outside_primary_or_retained_coverage": sorted(
                admitted.keys() - coverage.keys() - known_retained_admissions
            ),
            "verified_admitted_status": Counter(row["status"] for row in admitted.values()),
            "verified_admitted_callables": callable_groups(admitted),
            "verified_admitted_exact_identities": sorted(admitted),
            "acceptance_handoffs_unavailable": unavailable, "admission_batches": batches,
        },
        "packet_attempts_with_no_outer_timing": packet_unmeasured,
        "packet_disposition": packet_disposition(), "worker_launches": worker_launches(),
        "canonical_ctest_attempts": suite_counts(),
        "canonical_command_accounting": canonical_command_accounting(args.evidence),
        "unmeasured_or_open_worker_windows":open_deliveries,
        "phase_windows": time_rows,
        "quota_interruption": quota_accounting(start, operational or end, time_rows),
        "phase_interval_totals": {kind: interval_stats(rows) for kind, rows in time_rows.items()},
        "graph_local_acceptance_overlap_seconds": intersection_seconds(graph, accepts),
        "graph_dedup_review_overlap_seconds": intersection_seconds(graph, time_rows["dedup_review"]),
        "graph_linux_overlap_seconds": intersection_seconds(graph, linux),
        "completed_graph_command_seconds": sum(
            row["command_wall_seconds"] for row in graph if row.get("command_wall_seconds") is not None
        ),
    }


def failures(rows, phase):
    chosen=[r for r in rows if r["status"]=="failed"]
    return {"phase":phase,"count":len(chosen),
            "failed_window_union_seconds":interval_stats(chosen)["union_seconds"],
            "failed_attempts":[{"label":r["label"],"receipt":r["receipt"]} for r in chosen]}


def costs(view, graph_count, command, slots, elf, wall, quota_adjusted=None):
    phases=view["phase_interval_totals"]
    result={"primary_slots_fully_admitted":slots,"distinct_elf_admitted":elf,"user_wall_seconds":wall,
            "primary_slots_per_wall_hour":3600*slots/wall,"elf_per_wall_hour":3600*elf/wall,
            "verified_graph_commands":graph_count,"graph_command_sum_seconds":command,
            "graph_mean_seconds_per_verified_command":command/graph_count,
            "graph_command_seconds_per_admitted_primary_slot":command/slots,
            "graph_command_seconds_per_admitted_elf":command/elf,
            "canonical_linux_command_seconds_per_admitted_elf":phases["canonical_linux"]["summed_seconds"]/elf,
            "local_acceptance_command_seconds_per_admitted_elf":phases["local_acceptance"]["summed_seconds"]/elf,
            "phase_subprocess_window_totals":{kind:phases[kind] for kind in ("live_graph","canonical_linux","local_acceptance")}}
    if quota_adjusted:
        result.update({"observed_quota_excluded_wall_seconds":quota_adjusted,
          "primary_slots_per_hour_without_observed_quota":3600*slots/quota_adjusted,
          "elf_per_hour_without_observed_quota":3600*elf/quota_adjusted})
    return result

def compare(live_path, prev_path, graph_path):
    live, prev, graph=read(live_path),read(prev_path)["current"],read(graph_path)
    prior_targets = prev["target_accounting"]
    prior_elf = sum(prior_targets[state]["all_distinct_original_identities"]
                    for state in ("new_ready", "new_pending"))
    prior_slots = (prior_targets["requested_slots"] - prior_targets["final_unresolved_originals"]["selected_original_count"]
                   + prior_targets["replacement_admitted_count"])
    targets=live["targets"]
    slots,elf=targets["fully_admitted_primary_slots"],targets["verified_admitted_distinct_elf_identities"]
    phases=live["phase_windows"]
    live_graph=phases["live_graph"]
    related={k:phases[k] for k in ("canonical_linux","local_acceptance","grouped_packet_prepare","packet_launcher_attempt","dedup_review","sqlite_admission")}
    quota=live["quota_interruption"]
    active=quota["elapsed_seconds_less_observed_coordinator_interruption"] if quota else None
    current_wall = live["operational_seconds"] or live["elapsed_since_request_seconds"]
    assert graph["verified_generations"] == sum(row["status"] == "registered" for row in live_graph)
    assert abs(graph["command_wall_seconds_sum"]-live["completed_graph_command_seconds"])<.1
    result={
     "status": "operational_end_recorded" if live["operational_end_utc"] else "interim_no_final_cutoff","as_of_utc":live["as_of_utc"],
     "receipt_links":{"10x20":ref(live_path),"10x10":ref(prev_path),"graph_aggregate":ref(graph_path)},
     "10x20":{**costs(live,graph["verified_generations"],live["completed_graph_command_seconds"],slots,elf,current_wall,active),
       "approved_replacement_mappings":len(targets["replacement_to_primary_slot"]),
       "fully_admitted_replacements":len(targets["fully_admitted_replacements"]),
       "ready_pending_counts":targets["verified_admitted_status"],
       "quota_observation":quota,
       "graph_overlap_seconds_by_measured_phase":{k:intersection_seconds(live_graph,v) for k,v in related.items()},
       "graph_overlap_with_union_of_measured_phases_seconds":intersection_seconds(live_graph,[r for rows in related.values() for r in rows]),
       "failed_attempts":[failures(phases[k],k) for k in ("packet_launcher_attempt","canonical_linux","graph_postflight","sqlite_admission")],
       "ctest_attempts_reaching_tests":dict(Counter(r["status"] for r in live["canonical_ctest_attempts"])),
       "packet_attempts_without_outer_duration_count":len(live["packet_attempts_with_no_outer_timing"])},
     "10x10":{**costs(prev,prev["phase_interval_totals"]["live_graph"]["count"],prev["graph_command_wall_seconds_sum"],prior_slots,prior_elf,prev["operational_seconds"]),
       "wall_through_report_commit_seconds":prev["full_cycle_seconds"],
       "fully_admitted_replacements":prev["target_accounting"]["replacement_admitted_count"],
       "initial_docker_mount_failure_windows":prev["initial_docker_mount_failure_windows"],
       "graph_overlap_seconds_by_measured_phase":prev["observed_graph_overlap_seconds"],
       "ctest_attempts_reaching_tests":dict(Counter(r["status"] for r in prev["canonical_ctest_attempts"]))},
     "method":["User wall for current in-progress cycle runs request to as_of, including observed coordinator interruption. Prior cycle wall runs through verified operational end, with report/commit shown separately.",
       "Primary slots and ELF identities are separate denominators. ELF includes admitted retained work and role/ABI variants. Use phase summations for subprocess burden and interval union for wall share. Overlaps are not additive.",
       "Failure slices come from durable timings, and CTest attempt counts overlap the command failures. A missing duration is not zero cost.",
       "Quota bounds describe coordinator observation. The quota-excluded sensitivity quotient is neither active CPU time nor billing. Current and prior scopes differ; no measured speedup claim."],
     "operational_cutoff_utc":live["operational_end_utc"]}
    return result


def worker_handoff_path(receipt):
    repository = Path(receipt["repo"])
    if repository.is_absolute() and not repository.is_relative_to(ROOT):
        # Archived receipts can retain paths from another checkout host.
        for index, part in enumerate(repository.parts):
            if part in {"temp", "evidence"}:
                relocated = ROOT.joinpath(*repository.parts[index:])
                if relocated.is_dir():
                    repository = relocated
                    break
    return ROOT / repository / receipt["handoff"]


def add_coverage(args):
    coverage = read(args.coverage)
    for field in ("active_proposals", "prerequisite_bound_proposals"):
        for receipt in coverage[field]["receipts"]:
            source = ROOT / receipt["path"]
            if ref(source) != receipt:
                raise ValueError(f"Selection proposal bytes changed: {source}")
            args.proposal.append(source)
    return coverage


def main():
    global ROOT, CYCLE, EVIDENCE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="Repository root for receipt links")
    modes = parser.add_subparsers(dest="mode", required=True)
    report = modes.add_parser("report", help="Aggregate exact original identities and measured intervals")
    report.add_argument("--cycle", type=Path, required=True, help="Cycle receipt directory")
    report.add_argument("--evidence", type=Path, required=True, help="Canonical run and admission receipt directory")
    report.add_argument("--previous", type=Path, required=True, help="Previous completed cycle JSON")
    report.add_argument("--as-of", required=True, help="Observation timestamp with time zone")
    report.add_argument("--coverage", type=Path, required=True, help="Hash-bound selection coverage JSON")
    report.add_argument("--replacement-plan", type=Path, action="append", default=[])
    report.add_argument("--historical-task-plan", type=Path, action="append", default=[])
    report.add_argument("--operational-end")
    report.add_argument("--commit")
    report.add_argument("--commit-utc")
    report.add_argument("--out", type=Path, required=True)
    comparison = modes.add_parser("compare", help="Compare a current ledger and a previous completed cycle")
    comparison.add_argument("--current", type=Path, required=True)
    comparison.add_argument("--previous", type=Path, required=True)
    comparison.add_argument("--graph", type=Path, required=True, help="Current verified graph aggregate")
    comparison.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    ROOT = args.root.resolve()
    if args.mode == "report":
        CYCLE = (ROOT / args.cycle).resolve()
        EVIDENCE = (ROOT / args.evidence).resolve()
        args.evidence = EVIDENCE
        if bool(args.commit) != bool(args.commit_utc) or (args.commit_utc and not args.operational_end):
            parser.error("Commit hash and timestamp require an explicit operational cutoff")
        args.proposal = []
        coverage = add_coverage(args)
        data = summarize(args)
        targets = data["targets"]
        if targets["proposed_exact_task_assignments_including_replacements"] != coverage["proposal_primary_slot_count"]:
            raise ValueError("Report and selection assignment counts differ")
        if targets["proposed_distinct_covered_elf_identities"] != coverage["proposal_covered_elf_original_count"]:
            raise ValueError("Report and covered ELF identity counts differ")
    else:
        data = compare(args.current, args.previous, args.graph)
    with args.out.open("x") as output:
        json.dump(data, output, indent=2)
        output.write("\n")


if __name__ == "__main__":
    main()
