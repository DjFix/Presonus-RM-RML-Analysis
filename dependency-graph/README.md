# Dependency graph experiment

ELF context for unreconstructed symbols, external-provider markers and the
nonempty-packet gate: [NATIVE_GRAPH.md](NATIVE_GRAPH.md).

## Active subagent context gate

Use [CONTEXT_SELECTION.md](CONTEXT_SELECTION.md) for the implemented Memgraph
selection operator, packet validation, disjoint batch dispatch and reasoned
context expansion. SQLite remains the canonical recovery registry.
See [IMPLEMENTATION_REPORT.md](IMPLEMENTATION_REPORT.md) for validation and limits.
Automatic incremental refresh before preparation is implemented:
[AUTOMATIC_REFRESH.md](AUTOMATIC_REFRESH.md).

## Current full-corpus result

Read [FULL_REPORT.md](FULL_REPORT.md) and [FULL_SCHEMA.md](FULL_SCHEMA.md).
SQLite, Neo4j and Memgraph now contain **551,185 nodes / 6,651,932 edges** from
**625 current Linux compile units** (574 app/test + 51 CCL) and all51,137 catalog
anchors. This is all captured source/build observations, not a proven complete
runtime graph of unreconstructed firmware. Unknown dispatch remains explicit.

The old15-record packet below was only header/TU impact. Full-case analysis found
five functions (two targets + three CCL), six types, six data entities, one caller,
one test and fixture. Both compilers agree on target calls; all three backends
agree on exact query results. See `runs/full-01/agent-context.md`: five existing
function bodies occupy24 lines, with the required state/test/proof context.

Active query catalog: `full_queries.py`. Complete main source/compiler evidence:
`runs/full-01/`; additional CCL evidence: `runs/core-source-01/`. Both graph
services have already received both deltas. Baseline remains historical.

Source extraction and compiler lowering are handled by `full_graph.py`,
`full_source_graph.py`, `gcc_source_graph.py`; merge/load/check by
`merge_full_graph.py`, `load_full_graph.py`, `check_full_graph.py`.
The historical Core compiler-ID repair is recorded by `qualify_core_ids.py`;
the merger now qualifies those IDs directly. Do not rerun completed imports on
existing receipt paths. No production registry/process/schema changes were made.

## Executed result

The last-cycle test selects **15 per-ELF records / 12 methods**: two target
methods plus ten related methods, in five production CPPs and the changed header.
The incoming packet had 464 records; 131 were bound to the changed header.
All four new per-ELF records are retained. Exact original-ID sets agree in
SQLite, Neo4j and Memgraph. This measures initial reading scope, not full-cycle
wall-time savings or complete call/runtime dependency coverage.

See `SCHEMA.md` for actual semantic SQL/Cypher and `COMPARISON.md` for features.
`handoff.py` builds the compact agent packet; `case_last_cycle.py` is the
cross-backend regression case. Results are in `runs/baseline-01/`.

Docker services and a Python benchmark runner have been built and tested.
`containers.py` uses `sg docker`; Compose is not required. Extra drivers run in
the runner image. Earlier host-local Java/Neo4j/driver artifacts were moved to
`.trashes/` with a verified manifest; `runtime.py` is an obsolete early helper.
Current images: `neo4j:2026.10.1`, `memgraph/memgraph-mage:3.13.0`.
Ports are loopback only: Neo4j Bolt 17687 / Browser 17474, Memgraph Bolt 27687.

```sh
uc-library/.venv/bin/python dependency-graph/containers.py case --backend neo4j
uc-library/.venv/bin/python dependency-graph/containers.py case --backend memgraph
```

These cases already ran on baseline-01; existing outputs are never overwritten.
Baseline benchmarks must run before case: case adds the documented semantic
labels and DEFINES overlay. Containers/volumes are retained. Stop services with
`containers.py stop --backend NAME`. The extraction below is the expensive
expanded baseline (941 seconds), not a recommended per-cycle refresh. The nm
ownership index took 3.49 seconds. Memory/restart/load series are deferred;
the priority is context quality, readable queries and a few timing samples.

## Initial protocol (historical plan; executed results above)

Isolated shadow experiment; no admission authority, schema migration, production
process changes or automatic test selection. Inputs are the operational SQLite
registry through its shared read-only adapter, GCC depfiles, compile commands and
CMake link recipes. No build or firmware operation is executed.

Run from the repository root (always choose a new output directory):

```sh
uc-library/.venv/bin/python -m unittest discover -s dependency-graph -v
uc-library/.venv/bin/python dependency-graph/experiment.py --out dependency-graph/runs/baseline-01
uc-library/.venv/bin/python dependency-graph/validate.py --run dependency-graph/runs/baseline-01
uc-library/.venv/bin/python dependency-graph/query.py --db dependency-graph/runs/baseline-01/graph.sqlite --path uc-library/include/surface_panel/ControlHelpers.hpp --domain build
```

Use the actual header path recorded in `scenarios.json`; an unobserved path
fails explicitly. `--registry-db ABSOLUTE_PATH` selects an independent registry.
The adapter takes a consistent transaction and the experiment saves a SQLite
backup of that generation. Input depfiles/commands/link recipes and extractor
are SHA-256 bound and rechecked before graph publication. This does not establish
that the existing depfiles are fresh for today's source or complete for other
build configurations. No source-level freshness or ABI claim is made.

Edges point from dependent to dependency. Reverse traversal reports impact.
`compiler_input`/`compiles`/`link_input` form the observed build graph;
`proof_binding`/`validation_binding` form a separate provenance graph. Neither
domain is silently traversed through the other. Original symbol identities retain
ELF SHA-256 and exact mangled names. Registry source digest values are preserved
on binding edges, not interpreted as proof of semantic dependency.

Outputs: isolated registry snapshot, indexed `graph.sqlite`, deterministic CSV
node/edge export, input hash table, scenario results and extraction report with
missing depfiles. Unknown call/type/virtual-dispatch relationships remain unknown.
Link recipes capture explicit object/archive operands, not dynamic loading,
response-file expansion or linker resolution of individual symbols. Imported
registry scripts are reused; their transitive environment is not fully sealed.

`validate.py` checks graph foreign keys/integrity, snapshot digest/integrity,
per-original-identity symbol count and the historical five-production-object
ControlHelpers observation. A mismatch fails rather than rewriting the expected
count. It does not assert a complete semantic dependency graph.

## Comparison protocol

1. Inspect ControlHelpers header, registrar CPP and partition-file scenarios.
   Review build/proof fanout separately; compare production objects against the
   previous five-TU observation, accounting for new versus existing objects.
2. Manually label required checks for header, implementation, new object,
   partition, producer/fixture and shared CCL header changes. Missing semantic
   evidence must expand the conservative scope, never authorize omission.
3. Run `query.py --repeat 20` for each observed path/domain; preserve JSON stdout.
   Measure extraction, traversal, explanation generation and end-to-end operator
   time separately. Repeated runs do not represent disk-cold performance.
4. Load the same `nodes.csv` and `edges.csv` into an isolated Neo4j instance.
   Retain IDs and edge kinds/evidence verbatim. Deduplicate by all four edge
   columns. Use one `DEPENDS_ON` relationship with a `kind` property and a unique
   node ID constraint. Do not import these experimental tables into production.
5. Compare exact reachable-ID sets using node-global visited traversal semantics,
   with filters applied at every edge. Avoid benchmarking enumeration of all
   possible paths against SQLite's deduplicated reachability. Time explanations
   separately. Record Neo4j version, edition, configuration, indexes, import time,
   memory and database size alongside SQLite results. No Neo4j benchmark has yet
   been executed; CSV export is preparation, not performance evidence.
6. Shadow several real cycles while retaining every current validation gate.
   Choose a backend only after correctness review and measured operational cost.

No persistent cache trust, changed readiness rule or automatic replay reduction
is introduced. Current full Linux validation remains the control process.

The first representation intentionally expands per-symbol proof bindings. Its
size and extraction cost must be reported rather than attributed to SQLite
traversal. A later source-set graph could preserve the registry's normalized
sharing; compare reachable identity sets before adopting that representation.

Unique ELF work and payload deduplication: [DEDUPLICATION.md](DEDUPLICATION.md).
