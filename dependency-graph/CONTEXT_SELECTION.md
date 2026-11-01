# Context gate for reconstruction subagents

This is the required initial-reading gate before `collaboration.spawn_agent`.
It does not create sidebar chats, call an agent API itself, admit reconstructed
functions, release the UC research pause or change production registry schema.
The coordinator consumes the generated tool arguments and invokes the subagent.

```sh
uc-library/.venv/bin/python uc-library/tools/recovery/select_context.py prepare --task dependency-graph/tasks/control-registrar-audit.json --out temp/recovery-work/context-gate/NEW_PACKET
uc-library/.venv/bin/python uc-library/tools/recovery/select_context.py validate --packet temp/recovery-work/context-gate/NEW_PACKET
uc-library/.venv/bin/python uc-library/tools/recovery/select_context.py dispatch --packet temp/recovery-work/context-gate/NEW_PACKET
```

Use `DISPATCH.json` as the `spawn_agent` arguments. `fork_turns=none` prevents
passing the entire coordinator history. TASK/CONTEXT/source slices, exact original
identities, ownership and unknowns are in the packet. The worker reads project
AGENTS.md as well. Root owns shared build files, global readiness and admission.

Task JSON fields: `task_id` (lowercase tool name), `mode` (`audit`, `reconstruct`,
`research`), `objective`, exact `namespace`, `owned_files` and `targets` containing
original ELF SHA-256 + verbatim mangled name. Catalog-only ambiguous names require
an explicit anchor or address+size. No return/class/layout information is inferred
from mangling. Reconstruction requires a disjoint owned-file list; audits are
read-only. `unmapped_policy=research` is allowed only for explicit research mode.
Unresolved source dispatch/missing bodies in reconstruction require an explicit
`uncertainty_work` assignment; nothing is silently cut to a count limit.

Unmapped source targets now use verified ELF context from NATIVE_ACTIVE.json;
they do not need an empty research escape. Read ELF_CONTEXT.md as part of every
packet. Each target needs a native/source/pinned-provider body before dispatch.
Explicit `declared_source_dependencies` can bind a necessary adapter source file
already hash-bound to the source generation. Native identities, typed links and
external-source policy are described in NATIVE_GRAPH.md.

Memgraph selects call/type/data context, references, tests and fixtures. Current
selected original records/proof links come through the shared SQLite adapter.
Assignments or unrelated registry traffic do not invalidate code context.
Dispatch rereads selected records; a changed selected record requires a new packet.
Existing broad proof bundles are links, not automatically expanded reading lists.

`prepare` automatically refreshes stale code observations, then performs source selection, AST slicing in the analysis container and
finalization. Dispatch refuses incomplete or modified packets, changed instructions
or operator code, stale source/build inputs and a missing/loading/wrong Memgraph
generation. A source-only catalog miss is unknown, not an independent leaf.

## Parallel batches

Prepare every packet before any worker starts editing, then:

```sh
uc-library/.venv/bin/python uc-library/tools/recovery/select_context.py batch-dispatch --packets temp/recovery-work/PACKET_A temp/recovery-work/PACKET_B --out temp/recovery-work/BATCH
```

This verifies one generation and rejects duplicate ownership or another worker
writing a file present in a packet's reading context. Only after this succeeds
spawn all workers from `BATCH_DISPATCH.json`. Failed preparation/dispatch paths
remain evidence and must not be treated as successful assignments.

## Additional context during work

The worker requests Root to run an expansion with a reason. After edits, explicitly
query the dispatched task's baseline, not a purported current-source graph:

```sh
uc-library/.venv/bin/python uc-library/tools/recovery/select_context.py expand --packet temp/recovery-work/PACKET --query callers --seed 'function:MANGLED_NAME' --reason 'Need caller state assumptions' --baseline --out temp/recovery-work/EXPANSION
```

Seeds must already belong to the parent packet or its original targets. Expansion
is read-only and tied to the parent manifest. Baseline expansion requires a sealed
dispatch and the same active Memgraph generation; source text comes from verified
content-addressed generation snapshots. It does not declare workspace edits fresh.
Available requests: callers, callees, references, overrides, source_files, proofs.

## Freshness and refresh

`dependency-graph/ACTIVE.json` identifies a registered graph generation. Registration
verifies captured input hashes and full typed node/edge counts, then records
filesystem fingerprints, source inventory and immutable source snapshots. Before
each new dispatch ordinary edits are detected using stats; a changed fingerprint
is accepted only if fresh bytes still match the captured SHA. Selected sources,
fixtures and proof files are freshly hashed. New/deleted source files invalidate
the generation. This is a cooperative filesystem guard, not a hostile-writer
security boundary. Import/case mutation operators mark Memgraph refreshing first.

The freshness check runs automatically at the start of `prepare`, under the same
exclusive lock as packet construction. An unchanged corpus skips compilation and
publication. A changed CPP replays its compile context; a header replays all TUs
whose captured includes contain it. New/deleted/changed compile commands are
reconciled. CMake configuration changes conservatively reconfigure existing build
directories, preserving their options, then replay all current TUs. Added/deleted
source/header files use the same fallback because of globs and `__has_include`.
A source file
outside compile_commands is not silently treated as compiled code.

GCC preprocessing discovers current includes before actual GCC compilation and
Clang extraction; source/include hashes are checked again before publication.
Per-TU fact ownership preserves shared observations while removing vanished
calls/definitions. Current link/test/fixture facts are recomputed together;
unchanged tuples are not republished. Unresolved configured tests block refresh.
Unchanged TU observations retain their original evidence paths and producer
identity; reuse is index reuse, never readiness-proof reuse.

Only the active Memgraph projection and `state/refresh-index.sqlite` are refreshed.
The SQLite/Neo4j experiment snapshots in `runs/` remain historical benchmarks.
The production SQLite registry is not modified. Historical proof/ownership
bindings retained in the corpus are not new current-build or readiness evidence;
selected proof links always come from the current registry adapter.

Refresh receipts, compiler logs and immutable observations are retained beneath
`temp/recovery-work/dependency-graph/refresh/`. Memgraph receives the delta in one
sequence of bounded transactions with atomic server checkpoints while its marker is `refreshing`. A durable SQLite pending journal
allows the next preparation to retry publication after interruption. Packet
selection remains blocked until registration verifies the new inputs and marks
the generation ready. Do not refresh concurrently with workers editing sources.

For maintenance, trigger the same freshness check explicitly:

```sh
uc-library/.venv/bin/python dependency-graph/refresh_graph.py
```

`--force` reconfigures and replays every current compile command. `--resume`
explicitly retries a pending publication; ordinary preparation also does this.
Direct registration is only for an already refreshed/reviewed corpus:

```sh
uc-library/.venv/bin/python uc-library/tools/recovery/select_context.py register --out temp/recovery-work/context-gate/NEW_REGISTRATION
```

Registration refuses changed source hashes; it cannot bless stale facts.
Dispatch validates its sealed packet and does not silently rebuild/rebind it.
Prepare fresh packets after refresh; an older generation's packet must not be
dispatched as current. Existing tasks retain their frozen source snapshots;
baseline graph expansion requires their generation to remain active.
No ignore-staleness switch or persistent readiness-proof reuse is introduced.

## Unique work gate

Preparation now requires the derived index selected by `DEDUP_ACTIVE.json`.
It transactionally claims one work item, expands to all covered original
occurrences, and binds the decision revision and claim in `context.json`.
Batch dispatch rejects duplicate work even with disjoint file ownership.
Read [DEDUPLICATION.md](DEDUPLICATION.md) for explicit import/publication,
provider routing, comparison tasks, result coverage and failed-prepare recovery.
Old packets without `work_binding` must be prepared again.

## Source identity migration gate

Source producers now use version 2 stable compile/TU/indirect identities and
separate observation provenance. The existing v1 pending delta must not be
resumed by these producers. Preparation is blocked until an explicit reviewed
migration has been activated; do not set a version flag on the legacy DB to
bypass the gate. See [SOURCE_IDENTITIES.md](SOURCE_IDENTITIES.md) for the isolated
rehearsal and the separate physical-publication requirements.
