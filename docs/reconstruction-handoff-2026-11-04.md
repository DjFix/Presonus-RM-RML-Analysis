# Reconstruction handoff — 2026-11-04

Canonical checkout: `/home/rs/projects/opencs/ai-line-analysis` on VM101.
Read repository `AGENTS.md`, especially the final production-priority section.
This handoff supersedes earlier continuation summaries about closing old 19/20
primary targets or completing three profiling trials before production.
The old goal attachment `92307753-732c-4a90-9f66-58dfa9f60e1b/goal-objective.md`
is historical, not the active objective: the user replaced the objective in chat.

## Active operating goal

Maintain sustained accepted reconstruction per elapsed time. Select rolling200
from current operational SQLite status/catalog/notes/claims, query Memgraph for
real dependencies, choose related scopes, prepare/dispatch, reconstruct. Prefer
more restored inputs and less missing work without excluding zero-input work.
Accept all independent passed results; park blockers with owner/reason/retry
condition and proceed next200. Never wait for200/200 or the old19-target tail.
Preserve every validation gate and original ELF identity. Reuse existing C++ and
pinned CCL, no Core binary reconstruction. Store and consult symbol-bound remarks
and evidence history, append resolutions. Optional ranking only if current/cheap;
no repair/rebuild/profiling prerequisite. Cheap automatic accounting only.
Overlap compatible preparation/publication/checks. Root integrates shared files,
canonical tests/audits, registry admission and trackers. Delegate implementation
to up to10 concurrent `gpt-6.1-sol` workers using sealed context packets,
`fork_turns="none"`. Parallelize bounded contract/declaration/state/provider review.
Continue production without repeated permission until scope exhausted or user stop.

## Runtime and tools

- Codex app-server was explicitly restarted by user request. New PID872047;
  confirmation `temp/recovery-work/codex-restart01/FORCED_RESULT.json`.
- Runtime now announced11 slots includingRoot:10 simultaneous workers supported.
  Do not fall back to old3-worker plan. Config `/home/rs/.codex/config.toml`:
  `[agents] max_concurrent_threads_per_session=10`, model `gpt-6.1-sol`.
- Default shell sandbox failed bwrap loopback. Escalated exec works; use specific
  justifications. Scratch belongs inside project `temp/`, never system `/tmp`.
- Validation Python/CMake/CTest/clang-format: `uc-library/.venv/bin/`.
- Active Linux build `temp/core-upstream/root-integration-01`.
- Host Python lacks neo4j. Existing `dependency-graph-runner:01` Docker image
  contains client; use `sg docker`, network `dependency-graph-experiment`, root
  mount read-only plus explicit output writable. Do not install a new stack.
- Do not restart Codex again. Do not run hardware, erase/flash, Mac sync or purge.

## Prior delivery is CLOSED — do not replay without changed inputs

Evidence root `evidence/recovery/2026-11-04/dependency-graph/stabilized-cycle01/`:
- `DELIVERY_CLOSED01.json`, `admission01/COMPLETED.json`.
-15logical functions/19ELF identities admitted compiled-declaration-pending;
 0newready. Canonical totals1063ready/1856pending.
- `linux06/COMPLETED.json`: all453CTest, install/role/compile-once gates passed.
- `mirror-source-audit02.json`: all2919current records passed.
- `claim-completion01/RECEIPTS.json`: all15work claims completed;19ranges checked.
- Graph refresh `temp/recovery-work/dependency-graph/refresh/1793824808026200298`
  succeeded;3018.56sec. Registered generation digest
  `49be5536ed3d2c7968d573d604048ed1f9091cf4e979d0755a58ac3351cc4b2b`.
- `COST_CUTOFF01.json` exists. No further performance comparison is a launch gate.
- Optional infrastructure optimization is stopped. Maintained early integration
  guards already validated with14regressions and fullLinux06; don't reopen them.

## Current selection and RUNNING preparation

Evidence `evidence/recovery/2026-11-04/dependency-graph/rolling200-01/`:
- `SQL_CANDIDATES01.json`: direct currentSQLite query, original identities,
  accepted statuses, active claims, notes; no ranking input.
- `MEMGRAPH_DEPENDENCIES01.json`: direct native projection queries; generation
  verified before/after;2446available nodes/19779observed edges.
- `PROPOSED200_PLAN01.json` and `.md`: exact200ELF identities/200unique-work,
 145distinct demangled signatures,10groups. IncludesABI/cross-binary variants;
 not200independent functions and not a claim of reconstruction completion.
- `NATIVE_REVIEW200_01.json`: every original byte range checked against sourceELF.
- `EXECUTION_OBSERVATIONS01.json`: exact mandatory `execution_review.collect`
 observations for all200, including register branches omitted from direct graph.
- `RECONSTRUCTION_NOTES01.json`:14indexedBLX across8methods plus GeqUI existing
 inline finding. This is NOT the complete indirect list; use execution observations.
- `OWNERSHIP_DRAFT01.json`:34distinct proposed existing write paths, root-only
 shared integration. Draft, not passed selected-read conflict validation.
- `WORKER_ASSIGNMENT02.json`: model and confirmed10-worker runtime.

Actual ongoing command (DO NOT start another copy):
```
uc-library/.venv/bin/python uc-library/tools/recovery/select_context.py batch-prepare --tasks temp/recovery-work/rolling200-01/REVIEW_TASKS01.json --out temp/recovery-work/rolling200-01/review-batch01 --jobs auto
```
Coordinator PID874466; exec session64837 belongs to the old chat and may not be
usable from a new one. Inspect PID/children and durable receipts instead.
Log `temp/recovery-work/rolling200-01/review-batch01.log`.
Environment handles `review-batch01/environment-handles-1793828591460255473.json`.
Latest process observation is recorded in
`evidence/recovery/2026-11-04/dependency-graph/rolling200-01/PREPARE_OBSERVATION01.json`.
At that observation coordinator PID874466 was alive with active select/finalize
children; packet selection/slicing was advancing. No sealed dispatch was observed.
This is a timestamped snapshot, not a substitute for checking the live process.
Recheck actual state now.
Do not restart/release claims merely because a tool handle is unavailable or an
observation times out. A failed prepare retains claims and resumable state.
No new workers were spawned in this chat. No new production C++ has been edited.

This batch is explicitly RESEARCH mode for bounded production contract review,
not an implementation dispatch or an infrastructure trial. Ten workers each get
16..24native packets and own only disjoint `uc-library/candidates/rolling200_review_wNN/`
review files. Root must validate returned exact execution/declaration/state/
lifecycle/provider contracts, then prepare reconstruction packets for eligible
results. Do not allow implementation using these research-only permissions.
Do not require all200review targets to succeed before advancing compatible work.

## Next actions

1. Verify existing PID/receipts and finish this SAME batchprepare. Diagnose terminal
   failure before resuming. Don't redo SQL selection, native checks or publication.
2. Inspect sealed BATCH_DISPATCH/DISPATCH arguments. Spawn10specified owners with
   model `gpt-6.1-sol`, fork none, generated context message; keep exact ownership.
   Old framework/worker model defaults must not override explicit user selection.
3. Reviews return REVIEW/EXECUTION_REVIEW/OWNERSHIP/BLOCKERS/REPORT. Validate with
   current `reconstruction_contract.py` and `execution_review.py`; use actual
   evidence, not invented virtual slot names or blanket local-flow classification.
4. Prepare compatible implementation groups and delegate toSol, then fullworker
   acceptance/integration/admission gates. Park unresolved results and keep stream.

Known ownership constraints: G03Controller.hpp changes precede G01/G02readers.
G02ownsDsp.hpp/FilterControllers.hpp. G04frontier01_w03.hpp also containsPotControl,
FileMuteGroup,FocusHelperButton; selectedreaders need frozeninputs/reprepare.
`GeqUIComponent::paramChanged` alreadyinline forwards toobservedParamChanged:
review/reuse, not automatic rewrite from absent archive symbol.
Native source lookup may show callbacks at `ldr pc,[vtable,#slot]`;14indexedBLX
alone is insufficient. Mandatory execution observations include all candidates.
Core uses pinned officialCCL; pending dependency status isn't caller-proof.

## Coordinator transfer

Only one Root should coordinate claims, source edits and admission at a time.
This file itself does NOT pause the old goal or transfer live ownership. The user
must stop/pause old coordinator when activating the new chat. Preserve the running
prepare; pausing chat is not permission to cancel its external process.
Current status pointer:
`evidence/recovery/2026-11-04/process/performance-stabilization01/STATE.json`.
