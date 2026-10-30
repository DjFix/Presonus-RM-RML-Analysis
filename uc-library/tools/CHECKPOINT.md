# Generated checkpoint consumer

`generate_checkpoint.py` reads ready and pending entries from one read-only
SQLite transaction selected by `validation/registry-sqlite/ACTIVE.json`.
`--db PATH` explicitly selects another registry (relative paths are library-relative).
It never writes the registry or falls back to the historical JSON ledgers.

Existing CLI arguments, new-output preservation, identity deltas, summary counts,
original-key uniqueness/disjointness, passing Linux integration and test-log
path/hash checks remain. Paired JSON/Markdown includes `registry` snapshot logical
generation, schema revision and capture provenance instead of claiming that live
JSON ledger SHA values supplied the records. `inputs` still binds integration.
This metadata summary does not replace complete readiness validation.

Regression checks:

```sh
uc-library/.venv/bin/python -m unittest discover -s uc-library/tools -p test_generate_checkpoint.py -v
```

The actual old JSON/new SQLite CLI comparison is preserved in
`evidence/recovery/2026-10-30/registry-checkpoint-cutover/parity-report.json`.
All semantic output fields matched; only timestamp and storage provenance differ.
The single sequential samples include startup and output writes, with uncontrolled
cache/shared machine load; they are not a general throughput guarantee.
