# Refresh staging: measured computation and preserved checks

The historical graph refresh took 44:40.350. Its compiler extraction took
4:58.332; the publisher took 39:27.950. Approximately 25:48 elapsed before the
staged delta was written. That historical log has no per-operation timers, so
new measurements must not be presented as a retrospective exact breakdown.

The maintained `measure_refresh_stages.py` replays computations on the retained
1,241-unit capture. It reads operational SQLite in a read-only transaction,
never copies databases, starts no compiler and sends no graph requests. It
separates comparison of 1,138 retained observations, fact generation for 103
changed units, build dependency collection, input hashing and native sealing.
Native sealing must reproduce the saved seal exactly. Before/after runs must
have equal workload and output digests; changed historical inputs fail the run.
SQL mutation/commit and server publication are outside this read-only replay.

Production staging now writes `stage-timings.json` for successful and failed
attempts. Disjoint timed calls cover equivalence, facts, per-owner SQL updates,
build facts, build SQL updates, delta finalization, input hashes, retained-capture
verification and native seal construction. Wall and CPU seconds are recorded;
remaining time is reported separately rather than assigned speculatively.

The optimized staging normalizer avoids copying the full AST before rebuilding
it, reuses the command descriptor, and memoizes repeated serialized provenance.
Its bounded string cache is cleared whenever the indirect-call identity mapping
changes. Original inputs remain unmodified and mutable outputs remain independent.
The extraction normalizer remains the original implementation and serves as a
differential reference; all six extraction producer hashes are unchanged, so this
staging optimization itself does not force another compiler pass.

Build dependency collection resolves repeated path references once, then
re-resolves every distinct path before returning its facts. Symlink retargeting
fails that final barrier. Existing input hashes, kind conflicts, unit ownership,
publication guards and transaction rollback checks remain active.

Full local receipts are under `temp/recovery-work/stage-profile-20261116/`.
Generated receipts/profiles are not tracked in Git.

The Linux publisher container passed 183 distinct regression tests in 2.559 seconds,
including compact staging transactions, zero-delta refresh, shared-owner removal,
late source mutation rollback, pre-write budget rejection and native guard codec
and lifecycle tests. A stale native-seal test double was updated to the current
versioned codec shape; the actual guard codec remains exercised.

Timing runs use the same 4 GiB / 2 CPU container profile. cProfile results identify
call costs but include instrumentation overhead; the separate wall-clock runs
omit profiling. Reference build collection is loaded from the existing archived
producer, verified identical to commit `3f3c63b13`, without creating another
checkout. Comparison aborts on changed inputs, changed tools, changed workload or
unequal outputs. Runs are sequential; the next run starts on process completion
without a conversational waiting interval.

The initial diagnostic profile (cProfile enabled) recorded 2,176,651,406 calls.
Normalization accounted for 910.514 of 1,232.943 profiler seconds (~74%);
`deepcopy` had 177,805,212 calls and JSON decoding 10,403,042 calls. SQLite
`execute` calls accounted for 26.327 seconds in this read-only replay. These
figures identify repeated Python tree/serialization work; they do not measure
the original SQLite mutation phase or establish the entire historic 25-minute
breakdown. The reader uses SQLite's default cache, while live staging configures
a larger cache; absolute replay times are not a forecast of production duration.

Within an equivalence comparison, both AST/GCC captures still undergo file,
source, command, recovery-pair and dump verification. When their raw semantic
AST contents match, the second deterministic normalization reuses the first
validated result. The resolved command descriptor must also match, including
include-directory symlinks. Different raw contents take the full two-normalizer
path; malformed identical inputs still fail the first normalization. Cache state
is discarded on success and failure and never crosses owners or invocations.

Sparse SQL row planning uses the exact membership differences already established
by `_preview` under the caller's transaction. It validates input types for every
node/edge, but looks up interned node values, logical edges and provenance only
for changed incoming facts. Deleted memberships retain their row charges.
Unchanged memberships already prove their interned records exist. The subsequent
actual mutation-count equality check, budgets, rollback and shared ownership
checks remain unchanged.

`measure_owner_planning.py` compares the original and candidate planners against
one read-only operational SQLite snapshot. Its cases use the real `@build`
collection unchanged, then one explicit in-memory label edit and one provenance
replacement. These last two are benchmark scenarios, not reconstructions or a
claim to replay the historical mutation. Every case requires an identical full
storage-row/cost plan; no scenario is written to SQLite or Memgraph.

## Final unprofiled comparison

All five output digests matched on the same 1,241-unit captured workload. The
native candidate seal also matched the original saved seal exactly. No compiler,
operational database writes or server publication ran in this comparison.

| Computation | Original seconds | Final seconds |
| --- | ---: | ---: |
| Verify/compare 1,138 retained capture pairs | 339.009 | 184.681 |
| Generate facts for 103 changed units | 28.912 | 22.715 |
| Collect build dependencies | 35.575 | 24.960 |
| Check input hashes | 8.569 | 8.116 |
| Construct and verify native seal | 31.697 | 30.458 |
| Sum of measured computation phases | **443.763** | **270.930** |
| Whole benchmark command, including startup/output | **447.730** | **274.500** |

The complete read-only command improved from **7:27.730 to 4:34.500**: 173.230
seconds less, **38.7% lower elapsed time** (~1.63× throughput for this replay).
These numbers are not a replay of the complete historical 25:48 staging interval
or 44:40 graph refresh. In particular, mutation/commit costs and server-side
publication/checks are excluded; no whole-refresh speedup is claimed.

## SQL planning comparison

The real `@build` owner contains **5,914 nodes and 265,144 edges**. Both planners
used one read-only SQLite snapshot, with exact equality of row counts, table
counts and encoded payload costs required in every case.

| Scenario | Original SELECT count | Final SELECT count | Original seconds | Final seconds |
| --- | ---: | ---: | ---: | ---: |
| No changes | 542,994 | 1 | 11.578 | 0.261 |
| One node label changed in memory | 542,994 | 4 | 4.086 | 0.261 |
| One edge provenance replaced in memory | 542,994 | 6 | 4.043 | 0.266 |

The first and later cases have different cache warmth; this is one sequential
sample, not a statistical latency guarantee. Query-count reduction is the
algorithmic result. Both implementations produced respectively 0, 2 and 4
planned storage-row mutations, and no mutation was actually executed. Do not add
these hypothetical-case times to the main computation benchmark or extrapolate
them into the missing historical SQLite-write duration.

## Evidence and reproduction

The maintained entry points are `dependency-graph/measure_refresh_stages.py`
and `dependency-graph/measure_owner_planning.py`. Their `--help` describes the
read-only modes. Exact Docker argv and wall timestamps are retained in the
local `*-command.json` receipts. The resource profile is 4 GiB / 2 CPUs.

Reference computation flags:

```text
--capture temp/recovery-work/dependency-graph/refresh/1794776024514322063
--normalizer reference
--reference-source temp/recovery-work/dependency-graph/refresh/1794776024514322063/producers/refresh_publish.py
--out temp/recovery-work/NEW_BEFORE
```

Final computation flags use the same capture, a new output directory, and
`--compare temp/recovery-work/NEW_BEFORE/RESULT.json`; omit the reference flags.
The SQL comparison uses `--reference` pointing to the archived `compact_facts.py`
and a new `--out` directory. These commands run in the publisher environment,
which includes the Neo4j client dependency; the benchmark makes no network calls.

Key retained receipts under `temp/recovery-work/stage-profile-20261116/`:

- `before/profile.txt`, `after-profile/profile.txt`: diagnostic profiles, including instrumentation overhead.
- `before-wall/RESULT.json`, `final-wall/RESULT.json`: final unprofiled comparison and equal output digests.
- `after-wall/RESULT.json`: intermediate normalizer/path-only implementation, preserved separately.
- `sql-planning/RESULT.json`: real owner size, exact planner equality, statement counts and elapsed times.
- `PAIR_APPLIED.json`, `SQL_APPLIED.json`: exact measured candidate hashes installed after earlier runs ended.
- `EXTRACTION_CLOSURE.json`: unchanged extraction producers.
- `complete-regressions.log`: final 183-test result.

No new full database generation, checkout copy, rollback archive or reconstruction
batch was created. The next actual refresh will use the optimized code and emit
the new per-operation staging timings; its complete wall time remains unmeasured.
