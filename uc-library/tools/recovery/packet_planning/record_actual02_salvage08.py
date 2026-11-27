"""Bind exact failed and successor process timings without inspecting claims."""
from datetime import datetime, timezone
from pathlib import Path
import sys

from packet_cycle import read, reference, save


packeting = Path(__file__).resolve().parents[4] / "temp/recovery-work/control10x20-after-4fed70d11/packeting"
first = packeting / "panel-successor-batch01"
second = packeting / "panel-successor-batch02"
failure, = first.glob("attempt-*/FAILED.json")
completion, = second.glob("attempt-*/COMPLETED.json")
snapshot = second / "SNAPSHOT.json"
dispatch = second / "BATCH_DISPATCH.json"
retained = packeting / "actual02-salvage08-claim-applied.json"


def attempt(receipt, command, started):
    start = datetime.fromisoformat(started.read_text().strip())
    end = datetime.fromtimestamp(receipt.stat().st_mtime, tz=timezone.utc)
    return {
        "started_utc": start.isoformat(),
        "terminal_receipt_written_utc": end.isoformat(),
        "observed_wall_seconds": (end - start).total_seconds(),
        "timing": read(receipt),
        "terminal_receipt": reference(receipt, "review_record", "Maintained attempt output"),
        "command": reference(command, "review_record", "Exact attempt commands and arguments"),
    }


save(Path(sys.argv[1]), {
    "first_attempt": attempt(failure, packeting / "actual02-independent11-command.sh",
                             packeting / "actual02-independent11-start.utc"),
    "same_owner_recovery": attempt(completion, packeting / "actual02-independent-salvage08-command.sh",
                                    packeting / "actual02-salvage08-start.utc"),
    "prior_claim_carry": reference(retained, "review_record", "Guarded exact eight same-owner carry"),
    "snapshot": reference(snapshot, "review_record", "Exact maintained mounted immutable inputs"),
    "dispatch": reference(dispatch, "review_record", "Exact maintained grouped dispatch"),
    "physical_snapshot_bytes": read(snapshot)["physical_copy_bytes"],
    "retained_snapshot_references": len(read(snapshot)["references"]),
})
