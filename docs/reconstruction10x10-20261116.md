# Real reconstruction 10 × 10, 16 November 2026

The run processed 100 original ELF identities using ten reconstruction workers.
76 identities (54 demangled callable groups, counting ABI variants separately)
passed bounded reconstruction, local acceptance, canonical Linux validation and
SQLite admission. All 76 are **compiled, declaration pending**; none is newly
ready or hardware/ARM-ABI certified. The other 24 identities are parked with
identity-bound remarks and retry conditions. They are not counted as delivered.
All 100 received persistent notes; the 76 admitted claims are completed.

Baseline checkout: `6e11a755bf63fc8cad67e2372d05315842218a41`.
Graph implementation under measurement: `a426eb6a0c487dcab8d4e72ad66f764c225cb41b`.
Canonical host: VM101. Core implementation remains pinned upstream CCL.

## Elapsed time

The request began at **04:30:17.932 UTC**. All operational gates, including the
actual changed graph and claim completion, finished at **12:13:17.543 UTC**:
**7 h 42 min 59.611 s**. Reporting and committing follow this operational end;
their actual cutoff is retained separately in the local final receipt.

These consecutive windows sum to that elapsed time; they are not CPU timings:

| Window | Elapsed | Contents |
| --- | ---: | --- |
| Request to first worker | 1:18:43 | Selection, contracts, packets, failed preparation and repairs |
| First worker to last local acceptance | 3:53:20 | Reconstruction, native/provider observations, worker revisions and overlapping Root acceptance |
| Last local acceptance to final operational gate | 2:30:56 | Integration repairs, full checks, proof sealing, admission and graph update, with overlap |
| **Operational total** | **7:42:59.611** | Includes failures and waiting |

The final successful Linux pipeline took **7:14.890**, including **6:09.353**
for all **796/796 CTests**. Earlier failed build/check attempts are retained in
the full report. Guarded live SQLite admission took **55.722 s**. Existing 515
records received fresh compatibility proofs without new reconstruction credit
or classification changes. Tracker, installed-role/compile-once, active-source
and mirror audits passed. Formatting used clang-format 23.1.3.

## Actual graph update

The first publisher attempt failed before graph transfer: **32:04.149**,
including **6:30.928** compiler capture and **24:23.208** failed staging. Its
projected journal requirement was 1,101,382,727 bytes, above the old 1 GiB cap.
Keeping that superseded cap was an operating error, not an unavoidable workload
cost. The failed transaction rolled back; its evidence was preserved.

Persistent finite defaults and reviewed caps now agree: 3 GiB journal, 12 GiB
process writes, 3 GiB serialized requests and 30 million charged rows. Physical
RAM/disk guards and validation remain enabled. Twenty focused tests passed,
including the measured projection and over-limit rejection.

The successful retry reused all **1,333 compiler captures**, with **zero repeat
compiler invocations**. It took **1:02:39.038**. Of 1,333 current owners, 1,134
retained equivalent observations and 199 regenerated facts; ten old units were
removed. This was a changed-source publication, not a packet-only benchmark.

| Successful retry measurement | Value |
| --- | ---: |
| Stage calls (excluding outer commit/publication) | 17:31.636 |
| Inside stage: replace 199 owners | 10:26.961 |
| Recorded graph apply transactions, summed | 6:40.536 |
| First to last apply-commit timestamp | 32:10.894 |
| Last delta commit to wrapper completion | 11:11.047 |
| Complete retry, including all checks/registration | 1:02:39.038 |

These rows overlap and must not be summed. There were **923 apply commits and
923 matching verification records**, no duplicate or unmatched commits.
Verification events have no separate duration; gaps also include cursor reads,
serialization, scheduling, native reconciliation and registration. They cannot
honestly be labelled entirely as verification or database execution.

Both publisher attempts total **1:34:43.187**. From the first actual start to
successful completion, including the budget repair interval, elapsed time was
**1:42:29.882**. Linux tests, admission and tracker work overlapped this interval.
Claim completion waited for the required graph lock; that wait is included in
elapsed time and is not added again as independent work.

The compact delta contained 129,610 node operations, 47,909 old-edge operations,
699,971 new-edge operations and 40,454 orphan-node operations. These are journal
operations, not counts of unique reconstructed functions. The delta file was
232,960,000 bytes (222.17 MiB). Serialized request envelopes totalled
1,028,113,852 bytes (980.49 MiB), including checks; this is not measured Bolt
wire traffic. Staging process writes were 3,892,117,504 bytes (3.62 GiB), not
database growth. Thus this run still has substantial write and request volume.

The registered graph is `generation-1794831190814869031.json`, hash
`f33631d77829e1037bbee15bc86eb527b479279d1782b4d2669eff1cb279fa0c`.
The final read-only check confirmed the active state hash and absence of pending
or unregistered refresh markers.

## What the comparison establishes

The earlier controlled, identical-input, read-only computation measurement was
447.730 → 274.500 seconds (**38.7% less container wall time**), with equal output
hashes. It excluded graph mutation, commit and registration. It establishes an
improvement in those measured computations, not a 38.7% faster full cycle.

This real run has no matched old-implementation whole-cycle control. The prior
20-identity run took 3:23:30, but used different targets and repair work. Neither
absolute runtime nor throughput across those different workloads proves a
causal whole-cycle speedup. Current operational throughput is 9.85 admitted ELF
identities/hour, or 7.00 callable groups/hour, all declaration-pending.

The next useful optimization is the remaining owner replacement and publication
work: reuse one exact owner identity plan across preview and mutation under the
existing lock and guards; measure graph request/verification/lifecycle phases
separately before changing their scheduling. Missing indexes are not established
as the cause. Do not disable validation or launch another reconstruction batch
just to conceal this overhead.

## Local evidence and reproduction

Full evidence stays on VM101 outside Git, according to the artifact policy:

- `temp/recovery-work/reconstruction10x10-20261116/RESUME.json`
- `temp/recovery-work/reconstruction10x10-20261116/GRAPH_FINAL_METRICS.json`
- `temp/recovery-work/reconstruction10x10-20261116/GRAPH_REGISTERED_FINAL.json`
- `temp/recovery-work/reconstruction10x10-20261116/admission-final76-live.json`
- `temp/recovery-work/reconstruction10x10-20261116/postadmission-final76-run01/`
- `temp/recovery-work/reconstruction10x10-20261116/workflow/outcomes-current/`
- `evidence/recovery/2026-11-16/reconstruction10x10/linux-final04/`
- `uc-library/validation/reconstruction10x10-20261116-new76-schema03/`

`GRAPH_FINAL_METRICS.json` binds both actual refresh directories and the controlled
comparison. `COST_END.json` captures session-tree counter deltas at 12:19:36 UTC,
separating automatic approval review; cached input is a subset, and these are
not billing figures. Later reporting tokens are excluded from that cutoff.
Executable replay tests and bounded fixtures are versioned under
`uc-library/tests/recovery/`; full historical proofs, ELF inputs, worker packets
and one-run coordinator scripts remain local. A fresh clone alone does not
contain those validation prerequisites.
