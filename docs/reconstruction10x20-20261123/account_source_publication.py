"""Attribute checkpointed source rows once and keep native follow-up separate."""
import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

def reference(path):
    with path.open("rb") as handle:
        return {"path": str(path), "sha256": hashlib.file_digest(handle, "sha256").hexdigest()}

def stamp(ns):
    return datetime.fromtimestamp(ns // 10**9, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S") + f".{ns % 10**9:09}Z"

def parse_journals(paths, shared_prefix=None):
    events, clocks = {}, {}
    for path in paths:
        with path.open("rb") as stream:
            if shared_prefix is not None:
                expected = shared_prefix.read_bytes()
                if stream.read(len(expected)) != expected:
                    raise ValueError(f"Shared resume journal changed its archived source prefix: {path}")
            for line in stream:
                row = json.loads(line)
                identity = row.get("checkpoint", "")
                if not identity.startswith("source-delta:"):
                    continue
                if row.get("state") == "verified":
                    key = row["event_id"]
                    if events.setdefault(key, row) != row:
                        raise ValueError(f"Conflicting verified source event {key}")
                elif "time_ns" in row and "commit" in row:
                    clocks.setdefault(f"{identity}:{row['commit']}", row)
    return events, clocks

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-journal", type=Path, required=True)
    parser.add_argument("--source-budget", type=Path, required=True)
    parser.add_argument("--timeout-command", type=Path, required=True)
    parser.add_argument("--timeout-log", type=Path, required=True)
    parser.add_argument("--checkpoint-readback", type=Path, required=True)
    parser.add_argument("--resume-journal", type=Path, action="append", default=[],
                        help="A resume-only journal")
    parser.add_argument("--shared-resume-journal", type=Path, action="append", default=[],
                        help="Journal with the immutable original source journal as a byte-exact prefix")
    parser.add_argument("--resume-budget", type=Path)
    parser.add_argument("--resume-command", type=Path)
    parser.add_argument("--resume-readback", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    initial, clocks = parse_journals([args.source_journal])
    if not initial or set(initial) != set(clocks):
        raise ValueError("Missing source commit clock/event associations")
    resumes, resume_clocks = parse_journals(args.resume_journal)
    shared_events, shared_clocks = parse_journals(args.shared_resume_journal, shared_prefix=args.source_journal)
    for key, event in shared_events.items():
        if resumes.setdefault(key, event) != event:
            raise ValueError(f"Resume journals disagree for source event {key}")
    resume_clocks.update(shared_clocks)
    all_resume_journals = args.resume_journal + args.shared_resume_journal
    new_effects = resumes.keys() - initial.keys()
    if new_effects or resume_clocks.keys() - clocks.keys():
        raise ValueError("Resume contains new source events; review independently")
    for key, event in resumes.items():
        if event != initial[key]:
            raise ValueError(f"Resume source proof conflicts with original event {key}")
    if resume_clocks:
        raise ValueError("Resume journal includes timed source transactions; verify readback vs retransmission")
    budget = json.loads(args.source_budget.read_bytes())["observed"]
    command = json.loads(args.timeout_command.read_bytes())
    log = args.timeout_log.read_text()
    if command["returncode"] == 0 or "publication: delta committed; checking and registering" not in log or (
            "NativeCandidateCheckpoint" not in log or "transaction timeout" not in log):
        raise ValueError("Missing measured native transaction timeout after source commit")
    phases = defaultdict(lambda: {"rows": 0, "verified_batches": 0, "transaction_seconds_sum": 0.0})
    for key, event in initial.items():
        row = clocks[key]
        if (row["phase"], row["rows"]) != (event["phase"], event["rows"]):
            raise ValueError(f"Source event differs from its timing row: {key}")
        phase = phases[event["phase"]]
        phase["rows"] += event["rows"]
        phase["verified_batches"] += 1
        phase["transaction_seconds_sum"] += row["seconds"]
    checkpoint = json.loads(args.checkpoint_readback.read_bytes())
    source_state, = checkpoint["source"]
    if source_state["commits"] != len(initial) or source_state["verified"] != len(initial) or checkpoint["native"] != 0:
        raise ValueError("Independent checkpoint readback disagrees with source and native boundaries")
    total = sum(phase["rows"] for phase in phases.values())
    if total != budget["rows_charged"]:
        raise ValueError("Unique source events disagree with retained source publication budget")
    resume_paths = [args.resume_budget, args.resume_command, args.resume_readback]
    resume_summary = {"checked_completion_journals": len(all_resume_journals),
                      "verified_source_events_referenced": len(resumes),
                      "additional_transferred_source_rows": None}
    if any(resume_paths):
        if not all(resume_paths) or not all_resume_journals:
            raise ValueError("Require guarded resume command, budget, readback and source journal")
        resumed_budget = json.loads(args.resume_budget.read_bytes())["observed"]
        resumed_command = json.loads(args.resume_command.read_bytes())
        resumed = json.loads(args.resume_readback.read_bytes())
        source, = resumed["source"]
        if (resumed_command["returncode"] != 0 or resumed_budget["rows_charged"] != 0
                or source["state"] != "published" or source["commits"] != len(initial)
                or source["verified"] != len(initial) or resumed["native"]["state"] != "verified"
                or resumed["timeout"]["setting_value"] != checkpoint["timeout"]["setting_value"]):
            raise ValueError("Resume registry, timeout or unchanged source accounting disagrees")
        active, = resumed["active"]
        if active["state"] != "ready" or {event["checkpoint"] for event in initial.values()} != {active["checkpoint"]}:
            raise ValueError("Another graph checkpoint was registered")
        resume_summary.update({
            "additional_transferred_source_rows": 0,
            "command_wall_seconds": resumed_command["wall_seconds"],
            "serialized_transfer_bytes_including_native_and_registration_checks": resumed_budget["serialized_transfer_bytes"],
            "native_seal_sha256": resumed["native"]["seal_sha256"],
            "timeout_restored_seconds": int(resumed["timeout"]["setting_value"]),
        })
    else:
        resume_paths = []
    first, last = min(row["time_ns"] for row in clocks.values()), max(row["time_ns"] for row in clocks.values())
    last_clock = datetime.fromtimestamp(last // 10**9, timezone.utc).replace(microsecond=(last % 10**9)//1000)
    end_clock = datetime.fromisoformat(command["end_utc"])
    result = {
        "source_layer": {"rows_counted_once": total, "verified_batches": len(initial),
                         "serialized_transfer_bytes": budget["serialized_transfer_bytes"],
                         "first_verified_batch_utc": stamp(first), "last_verified_batch_utc": stamp(last),
                         "first_to_last_batch_elapsed_seconds": (last - first) / 1e9,
                         "phases": dict(phases)},
        "native_followup": {"initial_disposition": "transaction_timeout_after_source_commit",
                            "configured_transaction_timeout_seconds": int(checkpoint["timeout"]["setting_value"]),
                            "native_checkpoints_after_timeout": checkpoint["native"],
                            "last_source_batch_to_command_exit_seconds": (end_clock - last_clock).total_seconds(),
                            "interval_scope": "Upper bound from final confirmed source batch to command exit, including intervening checks; exact native transaction start is not recorded."},
        "resume": resume_summary,
        "receipts": [reference(path) for path in (args.source_journal, args.source_budget, args.timeout_command,
                                                 args.timeout_log, args.checkpoint_readback, *all_resume_journals, *resume_paths)],
        "counting": "Timing phases are nested inside command wall and are not added to that wall. Source events are counted once by checkpoint/event identity."
    }
    with args.out.open("x") as handle:
        json.dump(result, handle, indent=2)
        handle.write("\n")

if __name__ == "__main__":
    main()
