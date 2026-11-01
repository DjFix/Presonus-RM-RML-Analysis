# Resumable source publication

`batch_publication.py` applies nodes, edge removals, edge additions and orphan
cleanup in this order. Each transaction contains at most 1000 journal rows by
default (maximum 5000) and its server checkpoint update. Ordinary Memgraph
query timeout stays unchanged. No transaction spans the whole delta.

The immutable delta SHA identifies a `PublicationCheckpoint` node outside
`Artifact`. It binds batch size, phase and last SQLite rowid. A crash after
commit is resumed from the server cursor, even if the local receipt was not
written. An error rolls back both effects and cursor. Cursor updates verify the
expected previous phase/row; a concurrent advancement aborts the batch. The
coordinator still holds the shared context lock for the complete publication.
Never modify a sealed delta or silently change its producers/batch size.

`ContextGeneration.state` remains `refreshing` until completion and validation.
Packet preparation/dispatch cannot expose the mixed intermediate graph. A
completed cursor alone is not a registered generation or readiness admission.
Per-commit rows, wall durations and timestamps are in `batch-commits.jsonl`.

## Explicit v1 -> v2 migration

`migrate_source_identity.py stage --out ABSOLUTE_NEW_WORK_DIRECTORY` runs in the
graph runner. It copies the isolated v2 index, adds current build facts, checks
all retained input hashes, reconstructs the exact old owned union from the
working index and old sealed delta, and computes the physical delta. Source
observations are reused; no compiler replay occurs. It captures the relevant
server edge multiset and requires every audited prior owned edge to exist.
Unowned relationships and the native generation are preserved. A sealed stage
contains STAGED.json, plan.json, captured-report.json and SQLite artifacts.

`migrate_source_identity.py activate --out SAME_DIRECTORY` checks the seal,
inputs, producers and server baseline, then preserves a consistent SQLite
backup and original DB/WAL/SHM bytes under `state/legacy-v1-<run>/`. It installs
the new pending index and records SUPERSESSION.json referencing the exact old
delta. The old delta remains intact. The migration then uses the same batch
publisher as ordinary refresh/resume.

After all batches, migration verification compares the exact final relationship
multiset against the independently computed expected set, checks all desired
node identities, native counters/marker and unowned relationship kinds. Only
then can ordinary registration mark the graph ready. Fresh input hashes and
existing packet/unique-work/readiness gates remain required.

Use `refresh_graph.py --resume` after installation if publication was interrupted;
it reuses the staged delta and server cursor. Before installation, rerun the
same explicit activation after inspecting its INSTALLING/SUPERSESSION receipts.
Do not restage or reconstruct the source observations merely because an
observation timed out. A crash inside installation requires inspecting the
preserved archive/incoming file before continuing; do not manually mark ready.

## Validation

`check_batch_publication.py OUT bolt://graph-batch-test:7687` requires a dedicated
empty test server (the URI must contain `batch-test`). It injects interruption
after committed batches, resumes without replaying data batches, verifies a
second resume is a no-op, and checks a missing endpoint rolls back its cursor.
The fixture deliberately keeps the generation refreshing. Test container and
volume are retained separately from the production graph.

If unsealed staging is interrupted after the v2 index/build facts were committed,
`resume-stage --out SAME_DIRECTORY` explicitly reuses that cache and archives
its partial delta with hashes. It uses the audited all-affected prior union from
the old sealed delta. Pass SQLITE_TMPDIR and TMPDIR to an existing project work
directory **before Python starts**, so SQLite sorting cannot spill into Docker's
root filesystem. Do not launch a second staging writer; it must wait on the same
context lock until the inspected first process has actually exited.
