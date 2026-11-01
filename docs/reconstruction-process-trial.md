# Approved process trial — 2026-10-27

The user approved audit recommendations **2, 3, 4, 6 and 9**. Apply them over
the next three ordinary completed batches. Recommendations 1, 5, 7, 8 and 10
are not approved by this decision. No generic admission runner, candidate-schema
migration, dependency-proof reuse or readiness relaxation is introduced.

## Routine batch

1. Select two or three sealed candidates with disjoint file/namespace ownership
   when available. Check product destinations and shared header changes before
   applying. A dependency pair such as ProtocolComm/UARTComm must be applied and
   validated in dependency order; it is not an independent pair. Do not delay a
   ready candidate indefinitely for an unfinished peer. Keep per-candidate
   diagnostics, original identities and recoverable checkpoints.
2. Continue the existing guarded application, explicit formatting, full Linux
   integration, active-source behavioral proofs, readiness dry-run/admission,
   tracker and installed-role/header audit. Root retains global build and ledger
   ownership. Candidate proof never substitutes for active-source proof.
3. Consolidate explicit stable-boundary paths with project_sync phase manifests.
   Use at most one transfer per direction/area for the selected boundary where
   practical; retain fixed roots, exclusions, checksum checks, current changed
   destination mtimes, no delete/prune and no symlink following. Do not transfer
   unfinished worker files to reduce invocation counts.
4. Generate a new Markdown/JSON checkpoint using `tools/generate_checkpoint.py`
   with an optional previous generated JSON `--baseline`. It checks duplicate
   and overlapping ledger identities and the Linux test-log hash. It is a compact
   metadata summary, **not** the full hash/source/readiness checkpoint audit.
   Continue that audit. Keep unresolved behavior domains in the full symbol
   tracker and proofs. Update prose status documents once at completed batch.
5. Preserve full command/log/evidence files. Show exact shell commands before
   execution as required. Per the user’s reporting adjustment, omit routine
   conversational cycle reports, checkpoint summaries and unsolicited progress
   counts; provide status when requested. Keep required brief work updates and
   actionable blockers concise. Retain generated checkpoints, symbol trackers,
   full evidence and every validation gate; do not repeat completed inspections
   solely to prepare a chat report. Do not dump symbol tables or raw logs into chat.

## Measurement

`uc-library/tools/recovery/integrate_file_misc.py` now appends `step_started` and
`step_finished` records to phase `events.jsonl`. UTC `started_at`, `finished_at`
and monotonic `elapsed_seconds` are also added to existing `commands.json`
records. All previous command, exit-code and log fields remain. The helper
prints step/status/elapsed/log; complete commands and output stay on disk.

Record worker candidate-ready, root-review-start, role-audit-finished and
batch-admitted events in each batch's project evidence `queue-events.jsonl`,
using actual observation timestamps and candidate identities. Unknown historical
times stay unknown; never backfill invented durations. Root records its own
events; workers report proof/control handoff times with their existing messages.
Sync reports supply transfer timings and available byte/file counters.

At each completed trial batch, compare net ready identities and distinct compiled
identities with the generated baseline (including explicit removals), queue wait,
post-role-audit completion tail, rework and failures. Alias/per-ELF counts must not
be presented as independent algorithm throughput. A post-audit tail under five
minutes is a trial target, not a demonstrated speedup. Keep full CTest: measured
test time was too small to justify dropping it.

## Initial baseline and checks

Baseline: `evidence/recovery/2026-10-28/vm-migration/legacy-uc-recovery/checkpoints/2026-10-27-approved-process-baseline.{md,json}`.
Focused metadata/mocked-runner checks: `temp/process-audit/approved-process-tests.json`.
These checks do not execute C++ and do not claim new function readiness.
All reconstruction builds and behavioral validation continue on VM101 Linux.
