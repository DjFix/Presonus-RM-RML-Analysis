# Full symbol catalog and task queue

`catalog.py` is an additive SQLite operator. It never writes canonical JSON,
readiness records, source bindings, proofs, firmware or SDK files. Task `done`
means work tracking only: it cannot promote, demote or validate a function.
Core source-provided/deferred classification is an imported catalog annotation,
not permission to reconstruct Core binaries or a new readiness assertion.

Run from the project root using `uc-library/.venv/bin/python`. Always make a NEW
working copy; never point mutations at an immutable baseline or another worker's
DB. Explicit examples:

```sh
uc-library/.venv/bin/python uc-library/tools/registry/workflow.py init --baseline uc-library/validation/registry-sqlite/runs/20261030-sidecar-01/registry-v1.sqlite --db temp/my-catalog.sqlite
uc-library/.venv/bin/python uc-library/tools/registry/schema.py --db temp/my-catalog.sqlite
uc-library/.venv/bin/python uc-library/tools/registry/schema.py --db temp/my-catalog.sqlite --backup temp/my-catalog-pre-upgrade.sqlite --apply
uc-library/.venv/bin/python uc-library/tools/registry/catalog.py import --db temp/my-catalog.sqlite --library uc-library
uc-library/.venv/bin/python uc-library/tools/registry/catalog.py import --db temp/my-catalog.sqlite --library uc-library --apply
uc-library/.venv/bin/python uc-library/tools/registry/catalog.py query --db temp/my-catalog.sqlite --role client --name ControlRegistrar --kind STT_FUNC --raw
uc-library/.venv/bin/python uc-library/tools/registry/catalog.py query --db temp/my-catalog.sqlite --source recovered-all/client/symbols.json --limit 10
uc-library/.venv/bin/python uc-library/tools/registry/catalog.py query --db temp/my-catalog.sqlite --policy core-source-provided --limit 10
uc-library/.venv/bin/python uc-library/tools/registry/catalog.py query --db temp/my-catalog.sqlite --state assigned --owner worker1 --batch hal-next
```

Import reads full `all-symbols.json`, extracted `symbols.json`, role manifests
and `tracking/coverage.json`. Before/read/after hashes reject changing inputs;
SQLite import is one transaction and refuses an existing catalog. The dry run
executes the transaction then rolls it back. Manifest/source-policy metadata,
every raw symbol row and its source ordinal are retained. Input ordinals never
become file offsets. A stable SHA-256 anchor encodes ELF hash, verbatim mangled
name, address, size, section, kind and binding; repeated identical rows remain
separate provenance rows while conflicting local names/ranges remain distinct.
Both roles retain firmware labels and exact ELF identities.

Read-only queries preserve zero-size/undefined symbols, functions versus data,
explicit exported file offsets/range hashes and NOBITS storage metadata.
`aliases` lists same defined, nonempty section/address/size candidates, not
semantic/ABI equivalence. Zero-size/undefined entries are not called aliases.
`--source` selects an exact imported input subset; proof source dependency
impact remains the readiness registry/workflow operator's separate responsibility.
`--raw` exposes every original input row for inspection.

## Explicit task operations

Save request JSON inside project `temp/` (replace the example anchor with the
exact anchor returned by query):

```json
{
  "request_id": "hal-next-assign-001",
  "actor": "coordinator",
  "operations": [{
    "anchor": "<catalog anchor>",
    "expected_revision": 0,
    "state": "assigned",
    "owner": "worker1",
    "batch": "hal-next",
    "notes": "Offline app-only recovery; no device I/O",
    "reason": "Assign disjoint class ownership"
  }]
}
```

```sh
uc-library/.venv/bin/python uc-library/tools/registry/catalog.py operate --db temp/my-catalog.sqlite --request temp/task-request.json
uc-library/.venv/bin/python uc-library/tools/registry/catalog.py operate --db temp/my-catalog.sqlite --request temp/task-request.json --apply
```

States: `todo`, `assigned`, `in_progress`, `blocked`, `done`. Assigned/in-progress
requires owner; blocked requires explanatory notes. Every edit requires the
current optimistic revision and reason. Duplicate anchors, stale revisions or
invalid fields reject the WHOLE batch. Repeating an identical applied request
returns its stored result; reusing its ID with changed content fails. Dry runs
persist nothing. Concurrent operations use `BEGIN IMMEDIATE`; reviewers must
rerun preflight if a revision changed.

Undo is a new audited compensating request, never journal deletion. It restores
task fields only when no later edit changed that task's revision:

```sh
uc-library/.venv/bin/python uc-library/tools/registry/catalog.py rollback --db temp/my-catalog.sqlite --target-request hal-next-assign-001 --request-id hal-next-undo-001 --actor coordinator --reason "Assignment withdrawn"
uc-library/.venv/bin/python uc-library/tools/registry/catalog.py rollback --db temp/my-catalog.sqlite --target-request hal-next-assign-001 --request-id hal-next-undo-001 --actor coordinator --reason "Assignment withdrawn" --apply
```

SQLite triggers reject changes/deletion of task journals and request records.
The queue has no readiness mutation API. Evidence-backed stage/admission work
continues through the independently reviewed workflow/merger gates.

## Measurements and validation

Actual import captured 51,137 unique identity anchors / 98,123 raw provenance
rows across both roles in about 4.2 seconds; the complete independent working
DB was about 128 MB including its existing readiness mirror. Original-name and
source-subset queries took roughly 48/69 ms; dry-run/idempotent task requests
about 0.5 ms, committed metadata edits 3–9 ms on this VM. These are measured
operator costs, not reconstruction throughput claims.

Evidence: `validation/registry-sqlite/runs/20261030-sidecar-01/` contains
`catalog-import*.json`, `catalog-functional-validation.json` and final unit-test
logs. Actual task assigned→in_progress→done changed only catalog metadata;
readiness-record content hashes matched before/after. Six tests cover collision
identity/raw preservation, Core argument namespace separation, NOBITS/aliases,
source subsets, dry-run schema rollback, atomic rejection, idempotency, stale
revisions, append-only journals and compensating rollback.

```sh
uc-library/.venv/bin/python -m unittest discover -s uc-library/tools/registry -p test_catalog.py -v
```

## ORM and catalog schema migration

Catalog schema is declared in `catalog_models.py` using the shared SQLAlchemy
`orm.Base`. Task requests/journals are actual ORM objects, and optimistic task
updates use ORM statements. The shared `orm.Unit` owns one `BEGIN IMMEDIATE`
transaction and its Session; bulk catalog imports and read-only query fast paths
share the same transaction without independent commits. Legacy `catalog_info`
has no physical primary key and remains an unmapped SQLAlchemy Core Table;
adoption does not invent a key or collapse any existing rows.

Every catalog mutation requires the explicitly current Alembic schema revision.
Read-only queries accept supported legacy schemas, never create tables or
migrate. Run `schema.py --db ...` to inspect the plan, then explicitly pass a NEW
`--backup` and `--apply` on an independent workflow working copy. The original
referenced baseline must still exist with its recorded hash and cannot be the
target or a hardlink. Existing catalog databases are adopted in place only on
such copies; no reimport is required or permitted over an existing catalog.

Migration preserves every anchor, raw JSON value/source ordinal, range/data
annotation, task state/revision/owner/batch/notes, idempotent request result and
journal sequence. Existing append-only triggers remain database-enforced. A
failed revision rolls back its DDL and version/history changes; its independent
backup remains available. After migration, old task request IDs still replay
idempotently, and compensating rollback appends a new revision/history row.
Schema migration never changes readiness or claims that task completion is
function validation.

`runs/20261030-orm-catalog-01/validation.json` records full actual catalog
adoption (51,137 identities, 98,123 raw rows, all four preexisting task requests
and journal rows) with exact before/after table-content fingerprints and all
original triggers retained. Upgrade took about seven seconds; dry-run plus a
real ORM task commit took about 15 ms. The source DB hash and readiness contents
were unchanged; subsequent test operations appended two audited task entries.
The sixth unit test additionally injects migration failure, compares all old
table fingerprints, retries with a new backup, then verifies old idempotence and
ORM undo. Timing receipts are historical observations, not performance promises.
