# Symbol statistics from the operational registry

Run from the repository root:

```sh
uc-library/.venv/bin/python uc-library/tools/recovery/symbol_statistics.py report
```

Refresh the generated statistics section of the canonical tracker with:

```sh
uc-library/.venv/bin/python uc-library/tools/recovery/symbol_statistics.py report --update-symbols
```

This preserves the detailed extraction/behavior evidence sections. The full
`generate_symbol_tracking.py` generator delegates its summary to the same SQL
implementation; it no longer renders its old range-based reconstruction table.
Run this update after registry changes before committing a checkpoint. SQLite
is always the live state; the Markdown tables are a generated snapshot.

Optional `--registry-db /absolute/path.sqlite` selects an isolated registry;
`--json-out temp/recovery-work/symbol-statistics/new-report.json` saves a new
report without overwriting an older result. Both Markdown tables are printed.

The command resolves ACTIVE.json through the shared registry adapter and uses
the existing ORM read transaction. It reads only narrow catalog/status/provider
columns, closes the snapshot, then aggregates them with SQL in memory. No graph,
compiler, proof hashing, JSON provider fallback, migration or database write
occurs during reporting.

## Counting rules

- The first table counts distinct `(ELF SHA256, original mangled name)` among
  catalog `STT_FUNC` rows. Duplicate catalog occurrences do not add credit.
  Zero-size functions are included, matching the conversational table. Data,
  file symbols and other ELF symbol kinds are excluded.
- The second table groups by exact original mangled name and partitions names
  into names exclusive to each binary and names shared by multiple binaries.
  Each name belongs to exactly one row; every column sums to the union row.
  This is name deduplication, not reviewed implementation equivalence. Constructor
  variants, thunks and aliases with different names remain separate.
- In the union a name is reconstructed only when **all** its ELF identities have
  ready/pending records. All-ready means ready; a complete group containing a
  pending record is declaration-pending. Partially admitted names remain in the
  remaining column and are additionally counted in `partial`.
- Core follows both `core-source-provided` and `core-deferred` catalog policies.
  This means source-provider routing, not completed binding/ABI validation.
  libpng/zlib use exact imported ELF/name/address bindings, including internal
  functions. Unknown libraries are not guessed and remain in the remainder.
- Library/admitted overlaps and incompatible same-name library ownership fail
  explicitly instead of subtracting twice or inventing a unique-function count.
  Counts do not assert fresh proof, native equivalence or hardware validation.

## ORM import and migration

`tools/registry/schema.py` revision `0003_provider_definitions` adds two ORM
tables: `provider_imports` (hash-bound full original document/provenance) and
`provider_definitions` (normalized exact identities, size, section and library).
Both are append-only. No existing catalog/readiness rows are rewritten.

Before an explicit upgrade, retain a consistent SQLite backup. The migration
runner creates one by default. `--reuse-backup` accepts an already requested
backup only after verifying it equals the locked working database; it never
overwrites the backup or silently accepts a stale one.

```sh
uc-library/.venv/bin/python uc-library/tools/registry/schema.py \
  --db /absolute/working.sqlite --backup /absolute/backup.sqlite \
  --reuse-backup --apply
uc-library/.venv/bin/python uc-library/tools/recovery/symbol_statistics.py import-providers \
  --manifest /absolute/archived-provider.json --sha256 EXPECTED_SHA256
```

The importer validates all original ranges against the catalog and uses
`orm.Unit`/SQLAlchemy models for one atomic transaction. Reimporting identical
evidence is idempotent; conflicting ownership requires explicit reconciliation.
Consumers use `tools/registry/providers.py`, pinning the import SHA256. They do
not reopen the JSON file. The original JSON may be archived outside the project;
its historical source path and exact contents stay in SQLite provenance.

Maintained consumers are `packet_planning/packet_cycle.py` and
`reconstructed_library_callers.py`. The planner's module family was moved with
it; its historical runtime data remains under the original `temp/` path.
`reconstructed_library_callers.py --out PATH` performs its explicit native-index
analysis; merely importing the module or requesting `--help` does not run it.

Migration/import/move receipts and the initial report are under
`temp/recovery-work/symbol-statistics/`. Original producer bytes are preserved in
project trash with exact paths/hashes in `SCRIPT-MOVES.json`, not relabelled as
having executed the new maintained code.
