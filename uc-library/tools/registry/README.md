# SQLite registry mirror

The operational SQLite registry stores ready and declaration-pending records,
original catalog data and independent work tracking. Original JSON files remain
untouched import provenance. The explicitly converted merger, symbol tracker and
checkpoint consumers use the database selected by ACTIVE; other consumers are
listed separately below. Capture/import preserves all previous generations.
No operator performs hardware operations. Python's standard
library is sufficient for capture/import/query/export; ORM work operators use the separately pinned dependencies below. Run from the checkout root:

```sh
uc-library/.venv/bin/python uc-library/tools/registry/registry.py capture-import --ready uc-library/validation/ready-functions.json --pending uc-library/validation/compiled-functions.json --run uc-library/validation/registry-sqlite/runs/UNIQUE_RUN
uc-library/.venv/bin/python uc-library/tools/registry/registry.py validate --db RUN/registry.sqlite --snapshots RUN/snapshots
uc-library/.venv/bin/python uc-library/tools/registry/registry.py query --db RUN/registry.sqlite --source src/Presonus/UC/EventItem.cpp
uc-library/.venv/bin/python uc-library/tools/registry/registry.py query --db RUN/registry.sqlite --elf ELF_SHA256 --mangled SYMBOL
uc-library/.venv/bin/python uc-library/tools/registry/registry.py query --db RUN/registry.sqlite --status pending --proof validation/EXAMPLE.json
uc-library/.venv/bin/python uc-library/tools/registry/registry.py export --db RUN/registry.sqlite --status ready --output NEW_EXPORT.json
uc-library/.venv/bin/python -m unittest discover -s uc-library/tools/registry -p 'test_*.py' -v
```

Capture hashes all canonical inputs before copying, hashes independent copies,
and hashes all inputs again. Any disagreement rejects the capture and retains
artifacts for inspection; no import follows. Snapshots are made read-only and
never optimized or deduplicated. The manifest records canonical absolute paths,
parent directories, input hashes, timestamp, schema version, tool hash and
checkout commit. Protect snapshots with normal backup controls: read-only mode
is an accident guard, not an immutable-storage security guarantee.

SQLite normalizes both `sources` and `repository_sources` dictionaries into
content-addressed ordered source sets and shared path/value versions. Other
record values and all top-level metadata are preserved as JSON. Original ELF
hash plus mangled name is unique across both statuses, so duplicates and
ready/pending intersections reject import. Separate indexed columns support
identity, status, proof and reverse source lookup. `--digest` qualifies a source
query by its exact digest string. Query emits compact identities rather than
expanding multi-megabyte manifests; export restores full records one at a time.
Read operations open SQLite with `mode=ro`; output files must not exist.

Export preserves JSON values, list order, and source-map ordering; whitespace
and record/top-level object key order may differ. Byte-identical originals
remain in snapshots. Import and full validation load one legacy document at a
time with the standard JSON parser; export streams one restored record at a
time. Database size and import timing are captured in `report.json`. Import
failures can leave a partial database with no success report; retain it as
failure evidence and use a fresh run/output path. A success report plus explicit
validation is required before treating the mirror as valid. A later admission
requires another capture; this mirror does not follow ongoing JSON writes.

Tests cover lossless roundtrip including unknown metadata and two source
versions, deduplicated source sets, reverse lookup, read-only enforcement,
foreign-key/integrity checks, duplicate-key disjointness rejection, capture
mutation rejection and snapshot tampering rejection.

## Explicit SQLite work operators

`workflow.py` creates a mutable independent copy of a completion-marked baseline.
Old snapshots and baseline databases remain untouched. The versioned
`schema_info(version, complete)` marker is committed only after import; readers
reject old unmarked/partial databases. The historical first mirror remains
preserved; the completion-marked baseline is `registry-v1.sqlite` in the same
run. `validate` verifies snapshot SHA-256 against the database's captured
provenance before comparing all values. For producer-generation capture, pass
`--expected-manifest PATH`: a trusted JSON map whose `ready-functions.json` and
`compiled-functions.json` values are expected SHA-256 strings. Before/after
hashes alone establish stable observations, not atomic producer generation.

```sh
uc-library/.venv/bin/python uc-library/tools/registry/workflow.py init --baseline BASELINE.sqlite --db NEW_WORK.sqlite
uc-library/.venv/bin/python uc-library/tools/registry/schema.py --db NEW_WORK.sqlite
uc-library/.venv/bin/python uc-library/tools/registry/schema.py --db NEW_WORK.sqlite --backup NEW_PRE_UPGRADE.sqlite --apply
uc-library/.venv/bin/python uc-library/tools/registry/workflow.py query --db NEW_WORK.sqlite --elf ELF_SHA --mangled SYMBOL
uc-library/.venv/bin/python uc-library/tools/registry/workflow.py query --db NEW_WORK.sqlite --status pending --role client
uc-library/.venv/bin/python uc-library/tools/registry/workflow.py query --db NEW_WORK.sqlite --scope Presonus::UC::Example --source src/Presonus/UC/Example.cpp
uc-library/.venv/bin/python uc-library/tools/registry/workflow.py counts --db NEW_WORK.sqlite
uc-library/.venv/bin/python uc-library/tools/registry/workflow.py audit --db NEW_WORK.sqlite --elf ELF_SHA --mangled SYMBOL
uc-library/.venv/bin/python uc-library/tools/registry/workflow.py apply --db NEW_WORK.sqlite --library uc-library --manifest REQUEST.json
uc-library/.venv/bin/python uc-library/tools/registry/workflow.py apply --db NEW_WORK.sqlite --library uc-library --manifest REQUEST.json --commit
uc-library/.venv/bin/python uc-library/tools/registry/workflow.py validate-all --db NEW_WORK.sqlite --library uc-library
```

Default `apply` performs read-only preflight. `--commit` explicitly opens one
`BEGIN IMMEDIATE` transaction. All operations validate before mutation; any
failure rolls back the batch. A request has a unique `request_id`, nonempty
`actor`, and nonempty `operations`. Each operation requires original ELF SHA,
exact mangled name, `expected_revision`, and a nonempty `reason`. A request ID
replay with the identical payload is idempotent; a different payload is rejected.
Duplicate keys in one batch are rejected. Revisions start at zero for imported
records. Example work assignment (classification remains unchanged):

```json
{"request_id":"example-1","actor":"operator-name","operations":[{"kind":"assign","original_elf_sha256":"ELF_SHA","mangled":"SYMBOL","expected_revision":0,"reason":"Disjoint class ownership","value":"worker-name"}]}
```

Operations are:

- `assign` / `block`: set a string `value`; empty clears it. These subset work
  annotations do not alter evidence stages or ready/pending classifications.
  Full catalog task queues are provided separately by `catalog.py`.
- `stage`: `stage`, `proof`, `proof_sha256`, and nonempty bounded `domain`.
  Supported stages are `catalogued`, `bytes_extracted`, `bytes_verified`,
  `pseudocode`, `compiled`, `namespace_mangling`, `behavior`, and `hardware`.
  The referenced JSON proof must identify the exact original key (top-level
  ELF plus mangled name/name list, or a matching functions entry) and explicitly
  set the stage flag true: respectively `catalogued`, `bytes_extracted`,
  `bytes_verified`, `pseudocode_exported`, `cpp_compiled`, a supported legacy
  mangling flag, a differential-pass flag, or `hardware_validation_passed`.
  Stages record evidence attestations; they do not execute extraction,
  decompilation, builds, tests, or native/hardware validation. A proof file's
  truth still depends on its reviewed producer and bounded observations.
- `classify`: `target` (`ready` or `pending`), full replacement `entry`, and
  exact `previous_validation_sha256`. Promotion removes the single row's pending
  classification atomically. Demotion requires a different freshly checked
  pending proof, a matching previous proof hash, and explicit reason. Full
  source sets and other entry fields are normalized/preserved.
- `admit`: explicit new original key, `expected_revision: -1`, target and full
  entry; no previous hash. It rejects existing keys and applies the same full
  evidence gates as classification. No placeholder/stub admission shortcut.

Classification freshly checks native original catalog identity/role/address,
source hashes, formatting map and passing status, current integration source
bindings and passing CTest status, repository-relative pinned Core dependencies,
proof digest, and the legacy portable-ready behavior/signature flags and bounded
validation domain. Pending classification requires explicit compiled/mangling
flags, a pending fragment containing matching original identity/source bindings,
and bound underlying compile/behavior proofs when present. Hardware verification is never added by classification; ready admission sets
`original_function_verified` and `hardware_verified` false as the legacy merger
does. Pending original-function observation flags are preserved separately from
ABI/hardware claims. Null historical roles remain unresolved; supplied nonnull
roles must match native catalog ownership. Current formatting map/source checks
are mandatory; ready admission refreshes the formatting-file binding as the legacy
merger does. Historical pending formatting references remain provenance. `validate-all`
replays these checks read-only for every record and reports each stale or
unsupported binding; it never silently removes stale records or marks them ready.

Stage updates at compiled/signature/behavior levels also check live source,
Core, formatting and integration bindings. Hardware stage additionally requires
`hardware_verified: true`, nonempty `device_identifier`, a bound
`hardware_authorization: {"path":"...","sha256":"..."}`, and nonempty
`hardware_observations` containing path/SHA-256 objects. Those artifacts are
freshly checked; this command does not authorize or perform hardware operations.
No actual hardware validation is claimed by this migration or its tests.

Proof and source hashes, normalized source-domain checks, and integration-file
checks are cached only within one guarded operation. Each
unique evidence file is freshly hashed, a before/after stat fingerprint is
checked, and every fingerprint is rechecked before commit. JSON parsing uses a
bounded eight-document cache. No persistent proof-reuse trust or hidden lock of
canonical JSON is introduced. This guards ordinary concurrent edits, not a
hostile process rewriting evidence while forging filesystem metadata. Hashing
and source review do not prove original ABI or hardware behavior.

`work_state`, `stages`, and immutable classification `records` identities remain
separate concepts. `journal` records actor/time/reason, before/after revision and
state, proof bindings and normalized source-set references; UPDATE/DELETE
triggers enforce append-only journal behavior through ordinary SQL. `requests`
holds idempotency results; `evidence_checks` stores each fresh path/hash/stat
binding once per request. This is an auditable local tool, not an access-control
boundary against someone able to alter the database schema.

Legacy export remains an explicit new file operation, never an overwrite or an
implicit legacy admission. Task/stage/audit metadata stays SQLite-only. The user-authorized cutover converts `merge_readiness.py`,
`generate_symbol_tracking.py` and `generate_checkpoint.py` to SQLite. Their
original validation domains and metadata remain explicit, with parity and
freshness checks and preserved independent task history. There is no silent
JSON fallback or implicit export back to the original ledgers.

## Timing replay

```sh
uc-library/.venv/bin/python uc-library/tools/registry/benchmark.py --baseline BASELINE.sqlite --snapshots SNAPSHOT_DIR --library uc-library --out NEW_BENCHMARK_RUN
```

The benchmark imports twice, measures open-plus-indexed original-key/status/
proof/source/count queries, performs read-only preflight and single/batch
assignments, idempotent replay, rejected atomic rollback, audit query, existing
ready revalidation, full baseline export/value comparison, and two full fresh
evidence validations. It reports database sizes, record counts, unique files
and bytes hashed, hash time, JSON cache behavior, and first-use versus repeated
observations. OS caches are not flushed, so measurements are not claimed as
physical disk-cold timings. Database lookup speed and import time do not replace
external proof/source verification time or establish faster reconstruction.

## ORM and explicit schema evolution

Work mutations use real SQLAlchemy ORM sessions for records, revisions, stage
observations, requests, evidence bindings and journals. Catalog task persistence
also uses sessions. Shared source manifests and large catalog imports retain
bulk SQL paths inside that same SQLAlchemy-owned transaction; no repeated source
manifest is expanded into a large ORM object graph. Session flushes and raw SQL
writes commit or roll back together. A post-mutation journal-failure test checks
that ORM writes, revisions, requests and newly inserted raw source sets all roll
back atomically.

Install the isolated pinned registry requirements in the project environment:

```sh
mkdir -p temp/registry-dependencies/cache temp/registry-dependencies/tmp
TMPDIR="$PWD/temp/registry-dependencies/tmp" uc-library/.venv/bin/python -m pip install --cache-dir temp/registry-dependencies/cache -r uc-library/tools/registry/requirements.txt
```

The lock pins SQLAlchemy 2.0.55, Alembic 1.20.1 and exact transitive versions.
The [SQLAlchemy session API](https://docs.sqlalchemy.org/en/20/orm/session_basics.html)
and [Alembic runtime API](https://alembic.sqlalchemy.org/en/latest/api/runtime.html)
provide the transaction and migration primitives. `orm.py` defines the physical
mappings; legacy `provenance`, `schema_info`, `workflow_info` and catalog info
remain Core tables because their original tables have no primary key. Adoption
never fabricates uniqueness that could discard duplicate provenance rows.

Storage import version `schema_info.version=1` is separate from the working
schema's Alembic revision. `0001_adopt` accepts the known independent working
schema without rebuilding any existing table; it adds only Alembic version and
append-only migration history. `0002_workflow_indexes` adds assignment, blocker
and stage lookup indexes. New revisions must be appended explicitly to the
reviewed chain in `schema.py`; there is no automatic model diff, implicit
query-time migration, destructive downgrade, or schema rewrite of baseline DBs.
Read-only operations can inspect supported older revisions. Mutations require
the current revision and tell the operator to run an explicit upgrade otherwise.
Unknown/newer versions and ambiguous completion/version rows are rejected.

`schema.py --db WORK.sqlite` is a read-only plan. Applying requires both
`--apply` and a new `--backup PATH`. The target must have a valid working-copy
identity referring to a distinct, non-hardlinked, hash-matching immutable import
baseline. A SQLite backup snapshot is independently integrity/completion checked.
A data-version guard rejects concurrent commits during backup/lock acquisition.
An explicit transaction binds Alembic operations to the locked connection.
Before commit, the runner checks all adopted table contents, existing trigger
and index definitions, foreign keys, integrity, the requested target revision,
and exact append-only migration-history growth. Injected migration failures
roll back both DDL and data; the pre-upgrade backup remains available. Existing
0001 to 0002 upgrades, replays, newer-version rejection and baseline-mutation
rejection are tested. Queries never create schemas or migrate databases.

## New canonical generations

A later canonical ledger generation requires a new guarded capture and new
working copy; preserve old snapshots, baseline, working DB and logs. Full
catalog imports must wait until the producer's tracker/coverage writes finish.
There is no implicit active-database pointer switch.

`refresh.py --source OLD_WORK.sqlite --destination NEW_WORK.sqlite` plans a
stable-original-key transfer of all *meaningful operational* workflow history;
`--apply` explicitly commits it. The destination must be freshly initialized
and explicitly migrated with empty work history. Classification records always
come from the new baseline. Original ELF/mangled keys map numeric IDs; missing
keys, populated destinations, historical source-set conflicts or concurrent
source changes reject the transfer. Prior requests, stage observations, work
revisions and journal text are preserved, with a `generation_identity` map for
historical numeric IDs embedded in audit JSON. Source sets referenced by old
journal entries are retained without replacing new record bindings. The source
must be quiescent in DELETE journal mode; snapshot a WAL source explicitly first.

Benchmark and synthetic functional-test task assignments belong only in their
test databases. Do not transfer those assignments into the operational DB.
Archive the test DBs and record their hashes and excluded-history rationale;
start operational tasks fresh when no meaningful prior task history exists.
Catalog task transfer is a separate stable-anchor operation documented with
its module. No transfer writes canonical JSON, imports old classifications over
a newer baseline, or claims that historical stages have been freshly replayed.

## Converted consumers and remaining legacy scope

`merge_readiness.py`, `generate_symbol_tracking.py` and
`generate_checkpoint.py` use the shared `adapter.py` snapshot reader. Both
statuses come from one SQLite read transaction; normalized source dictionaries
are restored once per operation rather than copied into every function row.
`--registry-db` can select an explicit working DB; otherwise ACTIVE selects it.
There is no JSON fallback. The merger retains full proof/source/Core/format/
integration/original-identity gates, then persists only changed rows through
`commit_snapshot`, guarded by the validated generation and final dirty-file
checks. Old JSON is never overwritten. Implicit stale-record removal fails
closed and requires explicit review; guarded demotions preserve their manifests
and previous proof hashes. Metadata-only updates are audited without fake
function transitions, and a no-op still checks evidence freshness.

Other legacy consumers, including the HAL tracker and bespoke audit/counter
operators, can still use JSON. They are outside this explicit three-tool cutover
and must not be silently treated as converted. Existing source/proof requirements
remain in force. Their later migration is a separate bounded task. No new
firmware reconstruction or hardware operation is part of this registry work.

## Final operational checkpoint

The managed pointer is `validation/registry-sqlite/ACTIVE.json`. It identifies
`validation/registry-sqlite/runs/20261030-consumer-cutover01/operational.sqlite`,
its publication hash, schema revisions, immutable baseline/input hashes, source
hashes and complete catalog provenance. The finalized import contains 1,052
ready + 1,048 pending records, 51,137 original catalog anchors and 98,123 raw
source rows. All 51,137 task rows remain `todo`; no benchmark ownership or synthetic history
was imported. The operational DB also preserves one meaningful reviewed
administrative-context continuation request with 437 journal rows (207 ready,
230 pending), without native C++, declaration, domain or status changes. Old test databases
and their histories remain archived separately.

The working DB is mutable: a successful explicit work operation changes its
hash. Treat ACTIVE's hash as a publication checkpoint, and explicitly refresh
the managed manifest after reviewed commits; do not infer that a stale observed
hash means the baseline or canonical JSON should be rewritten. Immutable
baseline, snapshots, test DBs and old pointer revisions remain preserved. The fresh proof audit is `fresh-current-validation.json` alongside the working DB.
The original JSON import remains lossless and immutable; the reviewed 437-record
continuation is separately journaled and backed up. Actual converted-consumer
benchmark receipts are under `evidence/recovery/2026-10-30/registry-consumer-cutover/`
and the tracker/checkpoint cutover evidence directories. The earlier ORM API
benchmark remains preserved at `validation/registry-sqlite/runs/20261030-orm-final02/`.


The raw catalog is an immutable capture-time import, not a mutable readiness
ledger. Its coverage input SHA is
`08d8c918e8c075b56139f06388a86912426256d703fc461f705fa7e9472047d2`;
the exact prior bytes remain at
`evidence/recovery/2026-10-30/tracker-sqlite-cutover/prior-json-baseline/tracking/coverage.json`.
Current tracker output can contain intentionally continued proof links, so
current readiness queries must use `records` keyed by original ELF SHA plus
mangled name, rather than infer current proof links from historical raw coverage
rows. Original catalog identities, ranges, aliases and data rows remain intact.
ACTIVE records this distinction and the archive location explicitly.
