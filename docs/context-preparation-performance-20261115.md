# Context preparation: shared verification and 10×10 measurement

The 2026-11-15 change batches selection and finalization, shares verified immutable
inputs within each invocation, retains packet-specific checks, and finishes
independent packet work despite packet-local failures. It does not change
reconstruction/readiness admission or start reconstruction workers.

## Historical baseline

The preceding 20-symbol reconstruction trial spent 2:19:53 before its first
worker. Its disjoint windows were 1:06:17 for selection/graph refresh/retries and
coordination, 35:23 for first packet preparation, 4:57 for task repair, and 33:16
for resumed preparation/grouping/validation/dispatch. This is an observed complete
workflow, not a clean selector benchmark. The first window includes 39:28 of
measured extraction/publication operations and 26:49 not individually attributed.

One Gambit D1 packet took 240.108 seconds for preparation, 188.958 seconds for
finalization, and 0.226 seconds for slicing. Graph query time was 0.931 and 0.712
seconds respectively. Code inspection found five full generation guards during
preparation and four during finalization of each packet. The coordinator invoked
`batch-run` with a singleton each time and discarded the common verification
state for these two actions.

Historical receipts remain under
`temp/recovery-work/trial10x2-20261115/prepared01/` and
`temp/recovery-work/trial10x2-20261115/root-review/timing-final/OBSERVED.json`.

## Algorithm and preserved checks

- Submit pending packets together for selection and finalization; keep the
  existing final common validation/publication barrier.
- Check full generation/tool state at invocation entry and exit. Every packet
  retains selected-source and packet-file hashes, native identity/body/range,
  instruction bindings, current claims, work status and decision validation.
- Reuse hashes only for native immutable inputs within one invocation, checking
  filesystem identity on every hit and hashing again at the final barrier.
  Mutable registry and claim stores are excluded.
- Validate request structure before expensive selector checks and check all
  selected read/write ownership before slicing. Packet-local failures do not
  cancel independent work. Incomplete/failed common barriers remain fatal.
- Resume completed selections/slices/finalizations after validating their frozen
  inputs and claims. Keep interrupted partial selection evidence for inspection.

For 100 successful packets, the selector's full generation guard count changes
structurally from 902 (100×9 plus final validation's two) to six (two per batch
selection, finalization and validation). Host setup/publication guards remain;
these counts must not be described as the total number of all validation checks.

## Measurement scope

The user explicitly selected a read-only context preparation benchmark on 100
real symbols. It uses ten class scopes with ten distinct original symbols each,
selected from current canonical SQLite catalog/status/history. Compiled records,
notes requiring review, active claims, retained reservations and Core providers
are excluded. The chosen scopes are ordered by their smallest total symbol-byte
size; this is a small-symbol sample, not a random workload or 100 reviewed
implementation contracts.

The production preparation coordinator, actual Memgraph queries, exact native
bodies, source slicing, claims and common publication checks run unchanged except
for the optimizations above. No workers are spawned, no readiness is admitted and
no database copies are made. Claim history and evidence are retained locally; completed audit claims are released after verifying that no worker was launched. A prior graph
writer is awaited through a blocking lock; this dependency wait is accounted for
separately and does not introduce a manual polling delay before preparation.

The maintained runner is `dependency-graph/measure_context_preparation.py`.
Full receipts are local under `temp/recovery-work/prepare10x10-20261115/`.

The first candidate-selector implementation took 54.438 seconds. Replacing one
work-kind scan per catalog row with one bulk join took 0.242 seconds and selected
exactly the same 100 identities and history records. This comparison measures
candidate selection only, not packet preparation.

The targeted regression run passed 139 tests in 19.832 seconds. Tests cover
mutation/replacement detection, unchanged-input reuse, mutable-store exclusion,
selected-source hash checks, final generation barriers, partial-failure handling,
resume, current claims, conflicts, contracts and grouped dispatch.

## Fresh graph prerequisite

The previous reconstruction added source/header paths. The ordinary refresh
correctly refused automatic all-unit extraction. An explicitly requested compiler
rescan retained the compact incremental publisher; this was not a full database
rebuild. Its compiler extraction completed in 298.332 seconds (4:58.332).
The existing publisher was allowed to finish with unchanged producer bytes.

Direct newly registered compiler captures also need verified references, otherwise
a new packet snapshot would duplicate their AST/GCC payloads. The added direct
capture path binds the registered state and report, completed extraction command,
producer identities, compile command, source/input hashes and AST/GCC pair.
Runtime reference checks retain physical file identity and metadata/payload
checks. Metadata digests are explicitly fresh observations, not invented
historical execution seals.

The scoped hashing helper retains a statically verified hashing-only compiler
import path. Exact helper/initializer syntax and inert module checks are required;
any changed behavior falls back to the full dependency closure. Whole producer
module hashes are still recorded and verified.

The rescan processed 1,241 translation units and completed in 2,680.350 seconds
(44:40.350), including compiler extraction. Post-refresh reference/closure
regressions passed 33 tests in 0.818 seconds. This graph prerequisite is separate
from the measured warm 100-packet preparation.

## Completed 100-symbol measurement

All 100 packets passed prepare, finalize and validate. The complete dispatch
manifest contains ten groups of ten; **zero workers were launched**.
The successful resumed run lasted **807.068 s (13:27.068)**, including coordinator
setup, validated snapshot, context queries, slicing and publication. It ran from
2026-11-15 21:44:17.440 to 21:57:44.508 UTC on VM101.

| Operation | Wall time | Accounting |
| --- | ---: | --- |
| Setup and immutable snapshot | 183.419 s | Includes 135.447 s snapshot work and claim revalidation |
| Batch context selection | 270.267 s | 100 packets; 148.427 s graph queries |
| Source slicing and builder orchestration | 21.224 s | Builder envelope minus selection/finalization; parallel work, not sum of worker durations |
| Batch finalization | 167.577 s | 100 packets; 55.483 s graph queries |
| Final batch validation | 138.704 s | 100 packets; 27.859 s graph queries |
| Remaining coordinator/publication/cleanup | 25.877 s | Residual of measured total; includes final host checks |
| **Successful resumed preparation** | **807.068 s** | **13:27.068** |

The six selector generation barriers took 305.275 seconds combined. They are
included in selection/finalization/validation above, not extra time. Actual
selection made 85,801 graph queries: batching these context requests is a further
optimization opportunity. Query time across all three actions was 231.769 s.
Lock waits were below a millisecond; waiting on locks was not the bottleneck.

The first attempt stopped before snapshot payload writes at **78,553,068 bytes
(74.91 MiB)** against a leftover 64 MiB physical-copy default. That attempt cost
**264.520 s (4:24.520)**. Resume used the same 100 requests and claims with an
explicit 1 GiB budget. The coordinator gap between attempts was **87.057 s**.
From first attempt start to successful completion was **1,158.645 s (19:18.645)**.
The 44:40.350 graph prerequisite above makes the combined rescan-through-completion
window about **1:03:50** (21:57:44.508 minus 20:53:54.946 UTC). This excludes the
preceding ordinary-refresh refusal, development, tests and final reporting; it is
not the total elapsed time of this development task.

The snapshot copied **78,553,068 bytes**, retained 6,923 verified references and
bound 7,170 files. Large registered compiler captures and existing snapshots use
verified references; there was no database copy or repeat compiler extraction
in the preparation run. The snapshot references are dependencies, not backups.

After measurement, the default copy budget was permanently raised to 1 GiB in
all three entry points, with a shared constant and regression tests for defaults
and explicit overrides. The existing AGENTS.md budget correction now covers
preparation snapshots. This fixes the missed propagation of the user's earlier
all-limits instruction, rather than preserving a per-run exception.
The final combined regression suite passed **175 tests in 17.252 seconds**.
A test-harness module-registration error was fixed before this successful run.

The measured packets retain their original bindings. Subsequent tool/instruction
changes make them historical: they must not be dispatched or cosmetically
resealed. Their 100 owned claims were explicitly released after checking completed
measurement/process/agent state; release history is appended and no reconstruction
work or readiness was marked complete.

## Comparison and next opportunities

The prior observed time before workers was **2:19:53 for 20 reconstruction
symbols**, versus **13:27 for successful preparation of 100 audit symbols** here.
These are different workloads: prior time includes manual contract repair and
failures, while this benchmark selects small native bodies and launches no
workers. This is not a controlled 10× speedup claim and does not measure
reconstruction or admission throughput. The **2–5 minute preparation goal has
not been reached**.

Verified improvements are the same-candidate selector reduction from 54.438 s
to 0.242 s and the removal of per-packet full-generation verification repeats:
902 structural calls for 100 packets become six, observed in the new receipts.
Further reductions should batch graph context requests, reduce repeated host and
container file walks through explicitly validated immutable manifests, and reuse
claim decisions within an invocation while retaining current-state barriers.
The separate 44-minute graph refresh still warrants its own targeted work;
this change does not solve it or hide it inside a warm preparation number.

## Reproduction and evidence

The maintained runner defaults to 10 groups × 10 symbols and a finite 1 GiB
snapshot-copy budget. Run from the canonical VM101 checkout:

```sh
uc-library/.venv/bin/python dependency-graph/measure_context_preparation.py \
  --out temp/recovery-work/NEW_MEASUREMENT --select-audit \
  --reuse-snapshot temp/recovery-work/trial10x2-20261115/prepared01
```

Use a new output directory and current inputs. Do not resume the completed,
released historical benchmark. An actually interrupted run can use `--resume`
only after checking its live state and unchanged frozen inputs. The audit runner
never starts workers; its claims need explicit owner-reviewed release when done.

Receipts under `temp/recovery-work/prepare10x10-20261115/` include:

- `measurement02/MEASUREMENT.json`: failed first attempt.
- `measurement02/MEASUREMENT-retry-1794779864522844875.json`: successful full timing.
- `measurement02/prepared/BATCH_DISPATCH.json`: 100 packets, ten groups, complete.
- `measurement02/prepared/SNAPSHOT.json`: actual copy and reference accounting.
- `POST_MEASUREMENT_DEFAULTS.json`: original/final tool and instruction hashes.
- `AUDIT_CLAIMS_RELEASED.json`: owned claim release observations and history.
- `final-regressions.log`: final 175-test suite.

The scripts, regression tests and this compact report are versioned. Large
operational receipts remain local; no generated databases/log trees are added
to Git.
