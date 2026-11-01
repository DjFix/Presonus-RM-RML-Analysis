# Subagent context gate — 2026-10-31

This records the initial stage-03 gate. Its manual-refresh limitation below was
subsequently resolved by [AUTOMATIC_REFRESH.md](AUTOMATIC_REFRESH.md), stage-04.

Memgraph now supplies bounded initial context for reconstruction/research
subagents. SQLite remains canonical for original identities, readiness and
current selected proof links. The operator is
`uc-library/tools/recovery/select_context.py`; usage is in CONTEXT_SELECTION.md.

The implemented path is register → prepare → validate → dispatch, or
batch-dispatch for independent workers. Dispatch produces exact spawn arguments;
Root invokes the collaboration API. AGENTS.md makes this path mandatory rather
than claiming a technical interception of that API. Workers request additional
context through explicit seed/query/reason expansions.

Packets preserve exact original ELF/mangled identities, namespace and file
ownership, source slices, tests/fixtures/proof pointers, unresolved boundaries,
generation and content hashes. Frozen source snapshots support already dispatched
tasks; changed code blocks new dispatch until the graph is refreshed/registered.
Mutable registry assignments alone do not invalidate source context. Selected
identity/proof changes still require a fresh packet.

## Validation

- Seven Python unit tests passed, including stale bytes/new sources, identical
  byte touches and invalid task/ownership policies.
- End-to-end results: `temp/test-work/context-gate-e2e/1793440823253158780/results.json`.
  Current packet validation, independent batch materialization and baseline
  expansion passed. Modified packets, wrong namespaces and conflicting write/read
  ownership were rejected. Expansion returned three direct callees.
- A real `fork_turns=none` subagent audited packet-02: six unique source files,
  five function bodies/24 lines, 17 context entities, no unresolved dispatch in
  this bounded case. It found the packet sufficient without expansion and
  independently checked 2,048 fixture rows without oracle inconsistencies.
  This was a read-only context audit, not new reconstruction admission.
- Packet-02 predates the final stricter namespace/path validation. Final
  end-to-end validation used packet-03 and packet-peer-01. Historical receipts
  retain their original producer identity.
- No production registry schema/readiness changes or reconstructed C++ edits.
  The Extract UC launch pause and all existing validation gates remain.

## Limits

Automatic incremental graph rebuilding is not implemented. Refresh uses the
existing controlled source/compiler graph pipeline; registration refuses captured
input hashes inconsistent with current files. The graph describes captured source
and build observations, not complete behavior of unreconstructed firmware.
This proves context selection and guard behavior, not measured token savings or
end-to-end reconstruction speedup.

Evidence: `evidence/recovery/2026-10-31/dependency-graph/stage-03/manifest.json`.
