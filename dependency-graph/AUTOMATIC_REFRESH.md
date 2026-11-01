# Automatic source graph refresh

`select_context.py prepare` now checks and refreshes the active Memgraph index
before selecting a subagent packet. No separate manual refresh is needed for the
next batch. Prepare after the previous workers finish editing. Unchanged source
skips compiler replays and publication.

## Replacement policy

- CPP changes replay affected compile contexts only. Header changes replay every
  TU whose captured includes contain that header. Both GCC preprocessing and
  actual compilation run before Clang AST extraction; included project bytes
  are checked before/after analysis and again before publication.
- Compile-command additions/removals are reconciled. CMake/compile configuration
  changes conservatively reconfigure existing build directories and replay all
  current compile commands. Added/deleted source/header files take this same
  conservative path: globs and `__has_include` cannot rely on prior include edges.
  Existing cache options are preserved. Uncompiled
  files are not invented as independent graph leaves.
- `refresh-index.sqlite` stores node/edge contributions by TU. Replacement removes
  vanished calls and definitions and recomputes shared metadata from remaining
  contributors. Link/test/fixture facts are recomputed from current configured
  recipes and CTest inventory, but unchanged tuples are not republished. A test
  without a resolved CTest command blocks publication. External include paths are retained as compiler
  environment references, not recovered external implementations.
- Publication applies the delta in one Memgraph transaction, with the generation
  marked unavailable until verified registration. The SQLite journal records a
  pending delta atomically with its fact replacement. A later preparation retries
  it. If sources have advanced meanwhile, the published snapshot stays unavailable
  and the operator reconciles current sources against that exact index baseline.

The shared lock serializes refresh with packet preparation and dispatch. It does
not lock editors: edits racing extraction/publication fail freshness checks and
require a subsequent preparation after editing stops. Sealed packets are never
silently rebound to new generations.

## Live validation

`check_refresh_graph.py` temporarily added two functions and their call to the
existing registrar test, then restored the original source bytes. Memgraph showed
exactly two probe functions and two call observations (AST and GCC), and zero
after removal. A shared registrar header invalidated exactly its two captured
dependent TUs. All temporary source/header edits were restored byte for byte.

| Change | Replayed / total TUs | Observed wall time |
| --- | ---: | ---: |
| No source change | 0 / 625 | 0.46 s |
| One CPP, add probe | 1 / 625 | 62.43 s |
| Remove probe and change shared header | 2 / 625 | 63.44 s |
| Restore shared header | 2 / 625 | 63.46 s |

These are individual local regression timings, including graph publication and
registration with external include paths retained, not high-load benchmarks.
Most refresh overhead is still rebuilding/checking cached build facts and input
bindings; it is not a subsecond incremental updater. One-time ownership indexing reused
preserved observations without compilation. Configuration-wide invalidation is
unit tested; a new complete 625-TU replay was not needed for these local edits.

`check_refresh_recovery.py` reinserts a completed journal to simulate interruption
after transaction commit, changes the source again, then invokes the ordinary
`prepare` CLI. It verifies idempotent replay, reconciliation and a finalized
packet containing the same five functions / 17 context entities. This is a
controlled journal simulation, not an actual VM power-loss test.

Python unit tests cover dependency selection, removed compile contexts,
configuration-wide invalidation, shared-fact retention, definition demotion and
SQLite rollback, in addition to existing packet guards.

## Scope and retained evidence

Only the active Memgraph projection and its derived ownership cache update.
SQLite remains canonical for recovery identities/readiness; no production schema
or proof admission changes. SQLite/Neo4j benchmark snapshots remain historical.
The static graph still does not claim complete runtime firmware dependencies.
Existing formatting, Linux, mangling, behavior and readiness gates and the UC
launch pause remain in effect.

See CONTEXT_SELECTION.md for commands. Refresh source/compiler logs, producer
snapshots and receipts remain under `temp/recovery-work/dependency-graph/refresh/`.
Sealed validation evidence is under
`evidence/recovery/2026-10-31/dependency-graph/stage-04/`.
