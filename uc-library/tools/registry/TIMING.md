# Measured registry workflow timings

Pre-ORM frozen run: `validation/registry-sqlite/runs/20261030-workflow-final02/benchmark.json`.
This generation has 1,052 ready and 1,048 pending records, including 16 known
stale live-ledger bindings later corrected by legacy admission. Every source
byte executed during this run was copied and hash-bound before/after. The run
completed with unchanged source hashes and lossless baseline exports. The
initial cancelled run and the earlier gate-parity diagnostic run are retained
as historical measurements, not substituted for these results.

| Operation | Observed seconds |
| --- | ---: |
| Full import, first/repeated | 7.861 / 7.805 |
| Open plus indexed original key/status/proof/source/count query | 0.000267–0.000467 |
| Single assignment preflight / commit | 0.000641 / 0.016499 |
| 15 assignment batch preflight / commit | 0.008917 / 0.032458 |
| Idempotent replay / rejected rollback | 0.000571 / 0.000786 |
| Existing-ready evidence preflight / commit | 1.616 / 1.777 |
| Whole registry fresh evidence replay, first/repeated | 45.934 / 46.331 |
| Lossless baseline value validation | 14.816 |
| Ready / pending streaming export | 7.348 / 6.257 |

Existing-ready revalidation is not a newly recovered-function admission. Each
single evidence operation freshly hashed 1,442 files / 1.736 GB in 1.321 s;
current original/source/Core/format/integration/proof checks took about 1.602 s,
with about 0.165 s remaining for mutation/final guards/commit. Whole-registry
replay freshly hashed 14,869 files / 3.633 GB in 2.962–2.975 s and checked all
2,100 records: 2,084 passed and the exact 16 known stale-ledger dependencies
failed. A failed/stale entry was not admitted or removed. Baseline database:
20,688,896 bytes; benchmark working copy: 21,454,848 bytes.

The separately measured complete catalog has 51,137 anchors and 98,123 raw
source rows. Its task preflight / apply / idempotent replay took
0.000631 / 0.014410 / 0.000519 s; in-progress / done updates took
0.012681 / 0.003309 s. Raw evidence is
`validation/registry-sqlite/runs/20261030-sidecar-01/catalog-functional-validation03.json`.
These catalog task writes leave readiness classification unchanged.

These are observed first-use and repeated measurements with no privileged OS
cache flush. The existing legacy admission ran concurrently, sharing CPU and
filesystem cache. Its separately observed 34 min 05.57 s run performed its own
legacy admission workload; this benchmark is not a controlled apples-to-apples
speedup experiment. Import and SQL query time do not replace firmware recovery,
builds, behavior tests, review, or fresh external evidence verification. Exact
commands, environment, individual samples, hashes and cache details remain in
the raw reports. The final ORM-backed generation will be recorded separately.

## Final ORM-backed corrected generation

Frozen runtime report:
`validation/registry-sqlite/runs/20261030-orm-final01/benchmark.json`.
Inputs came from the trusted admission `after-hashes.json` pair: 1,052 ready,
1,048 pending, with the prior 16 stale ledger dependencies corrected. Both
whole-registry evidence replays passed all 2,100 records with zero failures.
SQLAlchemy 2.0.55 / Alembic 1.20.1 performed actual guarded ORM writes. The legacy
tracker, which repeatedly reads cached files, shared CPU during this run.

| Operation | Observed seconds |
| --- | ---: |
| Full import, first/repeated | 7.685 / 8.157 |
| Open plus indexed original key/status/proof/source/count query | 0.000328–0.000525 |
| Explicit adoption/upgrade with verified backup and fingerprints | 1.004 |
| Single ORM assignment preflight / commit | 0.003287 / 0.028070 |
| 15 ORM assignment batch preflight / commit | 0.009180 / 0.047097 |
| Idempotent replay / rejected rollback | 0.001730 / 0.001944 |
| Existing-ready fresh evidence preflight / commit | 1.638 / 1.736 |
| Whole registry fresh evidence replay, first/repeated | 26.009 / 24.913 |
| Lossless baseline value validation | 14.860 |
| Ready / pending streaming export | 7.465 / 6.750 |

Each whole-registry replay freshly hashed 14,898 files / 4,011,255,015 bytes in
3.330 / 3.321 s, checked 105 normalized source domains once, and reused those
operation-local domain checks 1,995 times. No persistent proof cache is trusted;
current logical paths and stat fingerprints are rechecked before admission.
Each existing-ready revalidation freshly checked 1,442 files / 1.736 GB;
commit's hashing cost was 1.325 s, all evidence checks about 1.606 s, and the
remaining mutation/final guards/commit portion about 0.119 s. This benchmark
revalidates an already-ready key; it does not claim to measure newly recovered
function admission. New-key admission is covered by evidence-gate unit tests.

The normalized baseline occupies 20,680,704 bytes; its benchmark working copy
occupies 21,528,576 bytes. Both exports are lossless parsed-value matches to
byte-preserved snapshots. Read-only preflight and rejected rollback left DB
bytes unchanged. Source files were copied and hash-bound before/after the run,
and remained unchanged during it. This timing section and later report-only
documentation were appended after benchmark completion; the exact earlier docs
remain in `executed-source/`. Runtime code was not changed after measurement.

Differences from pre-ORM timings include corrected input bindings, more unique
evidence bytes, operation-local source-domain deduplication, ORM session work,
and changing shared CPU/cache load. These are individual observations, not a
controlled claim that one factor caused an exact speedup. The 34-minute legacy
admission and long-running tracker are different workflows; SQL import time
never substitutes for those validation domains or for builds and behavior tests.

The benchmark times synchronous in-process API operations, including reopening
SQLite connections, complete evidence checks, final guards and commits. It
excludes Python interpreter startup and importing ORM modules. Individual CLI
invocations therefore have additional startup cost; the table does not claim
millisecond wall time for a fresh Python process. Raw command and environment
records identify the process that produced these API samples.

## Final post-lock guard and fresh-process CLI samples

The runtime race guard was then hardened and measured in a separately frozen
`20261030-orm-final02` run. Both fresh full-registry replays passed all 2,100
records with zero failures in 24.531 / 24.970 s. Imports took 7.855 / 8.096 s;
explicit backed-up migration took 1.013 s. API single preflight / commit took
0.003615 / 0.046457 s; 15-record batch preflight / commit took
0.009642 / 0.048437 s. This is the final runtime version, including the
schema-current check inside the locked transaction. Its source hashes remained
unchanged during measurement. Later documentation edits do not pretend to be
executed benchmark code.

Separate fresh Python process measurements are in
`validation/registry-sqlite/runs/20261030-cli-final01/report.json`, including exact
argument vectors and stdout/stderr. They used an independent test copy, never
operational assignments: query 0.493–0.516 s, counts 0.483 s, single work preflight
/ commit 0.530 / 0.546 s, 15-record batch 0.519 / 0.548 s, idempotent replay
0.502 s, rejected rollback 0.568 s, and existing-ready evidence preflight / commit
2.208 / 2.268 s. These wall times include interpreter and ORM startup, operation,
output capture and process exit.

## Savings for the same 16 provenance corrections

The closest measured comparison uses the exact Mapping8 + Updater8 pending
corrections: start from an independent copy of the OLD immutable SQLite import,
use each old proof hash as the guard, and apply the exact final canonical pending
entry for each original ELF/mangled key. The old baseline and final baseline
remain byte-unchanged. Every one of the resulting 1,052 ready and 1,048 pending
records matches the final canonical baseline by value; a separate fresh audit
passes all 2,100 records. Evidence, frozen external runner, manifests and
arithmetic are in `validation/registry-sqlite/runs/20261030-correction16-final01/`.

Legacy receipts under
`evidence/recovery/2026-10-30/combined-panel-hal321/admission02-ledger-provenance/`
measure preflight **2,032.605336 s** and actual admission **2,045.570320 s**:
**4,078.175656 s (67.970 min)** per observed cycle.

The same 16 SQLite corrections, measured as complete CLI processes, took
**2.778030 s** preflight + **2.890064 s** commit. Each operation freshly hashed
1,538 files / 2.566 GB (1.971 / 1.949 s hashing), checked two source domains and
reused those checks 14 times within that operation. The additional full 2,100
record fresh audit took **24.585004 s**. Thus the deliberately conservative
bookkeeping cycle including that full audit is:

`2.778030 + 2.890064 + 24.585004 = 30.253098 s`.

Observed arithmetic savings:

- `4,078.175656 − 30.253098 = 4,047.922558 s`, about **67.47 minutes per batch**.
- Assuming ten otherwise identical cycles: **11.24 hours saved** in bookkeeping.
- The elapsed-time arithmetic reduction is **99.26%**; this is not a controlled
  causal speedup or an overall firmware-reconstruction speed claim.

The workloads have an explicit frequency difference: legacy preflight and
admission each scan the whole ledgers; SQLite checks the changed 16 plus global
integration evidence twice and performs one separate full-registry audit. This
is the intended scoped-bookkeeping optimization. All fresh proof/source gates
remain present, but this is not identical per-phase execution. Separate repeated
setup measurements were 0.174 s for the independent copy and 1.018 s for the
explicit backed-up migration. The benchmark-only complete value comparison took
23.040 s; it is reported separately rather than hidden in recurring admission.
Shared CPU/cache load and future batch composition can change timings. These
savings exclude firmware extraction, native execution, builds, behavioral tests,
review and hardware work; no overall reconstruction speedup is claimed.
