# Reviewed source-port planning contract v1

Complexity ranking remains unchanged. A native body is analysis context, not a
complete reconstruction assignment. New `reconstruct` preparation requires a
`reconstruction_contract: {path, sha256}` reference to a Root-reviewed JSON file.
Audit/research and historical read-only inspection do not acquire reconstruction
permission from this mechanism. Existing sealed packets/proofs are not rewritten.

The review contains `version: 1`, `reviewer`, exact `targets` (ELF SHA-256,
mangled name, address and size), exact `owned_files`, a bounded intended `domain`,
and four `requirements`: `declarations`, `state`, `lifecycle`, `providers`.
Each requirement has a `status`, specific `reason` and hash-bound `evidence`.
Evidence includes repository-relative `path`, `sha256`, `kind` and precise
`scope`; paths outside the checkout and stale bytes fail.

Statuses:

- `established`: the relevant actual source-port declaration/implementation or
  provider source exists and was reviewed. Native observations alone cannot
  establish a C++ declaration, lifecycle or production provider.
- `bounded_work`: an uncertainty is explicitly assigned to this worker, with
  `work.objective`, `work.oracle_plan`, and `work.owned_files`. It must fit inside
  task ownership. This permits discovering details; it does not require full
  original class layout or return declarations before any reconstruction.
- `not_required`: justified for the particular method/domain, with evidence.
- `missing`: prerequisite work must be prepared first; not permission to add
  fake bases, no-op lifecycle, guessed original layouts or unbound providers.

Original ABI/layout and unencoded return types can remain unresolved in a
clearly stated source-port domain. A new partial class still needs coherent
production lifetime/state behavior for the scope it claims. Source availability
and matching mangling are never behavior or ABI proof.

`dependencies` record `kind`: `pinned_provider`, `existing_implementation`,
`included_work`, or `unresolved`, plus scoped evidence. Providers/implementations
need `binding_domain`. Included work needs its exact `work_item_id` and owned
files. The batch operator checks these IDs against actual dedup planning and
again against acquired bindings, on both fresh and resumed preparation; the work
must belong to the same worker. File/read/write/generation/claim gates remain.
Single-task preparation cannot claim external included work via a string list.

Existing compiled results route to `review_existing_result`, not reconstruction.
The review supplies a hash-bound actual object/archive and current implementation
source bindings. The checker runs Linux `nm --defined-only`, requiring each exact
original name. C1/C2 aliases are retained independently; matching compiled names
neither verify each original range nor grant readiness. ABI variants must not be
counted as new manually reconstructed bodies merely because a ledger lacks them.

`select_context.py prepare` and real `batch-prepare` enforce this planning check
before obtaining new claims or refreshing sources. Bound review/evidence files
are included in immutable batch inputs; the checker is included in tool hashes.
The gate validates a reviewed contract's bindings and structure. Root remains the
semantic reviewer; a typed reference to unrelated source is not a valid review.
All formatting, compilation, native/provider replay, handoff, full Linux CTest,
role/install/compile-once, fresh proof, guarded SQLite and tracker gates remain.

Do not fill a fixed quota with unreviewed work. Classify unreviewed candidates,
review connected scopes, and select only tasks that pass this stage. The current
legacy ranking queue name `reconstruction_eligible` denotes native-context
eligibility; it does not bypass this additional source-port planning gate.

## No pre-existing-declaration prerequisite

Missing declarations are normally reconstruction outputs. A native-only scoped
plan can pass with declarations/state/lifecycle/providers assigned bounded work;
the owned C++ files need not exist yet. Do not interpret earlier worker prose
saying “no declaration” as a proven impossibility. A real outside dependency or
insufficient evidence must be identified separately. Original full layout/ABI
proof is not a prerequisite for an explicitly bounded portable source port.

Recovery order is based on already recovered required inputs, not on whether a
C++ header happens to exist. See `recovery_frontier.py` and RANKING.md. Zero-input
and zero-recovery regions remain eligible for scoped planning. A review document
is an assignment of work and evidence, not a demand for prewritten declarations.
