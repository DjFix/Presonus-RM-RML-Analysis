# SQLite readers required by the single reconstruction cycle

These active operators read the shared SQLite ACTIVE snapshot, with optional
`--registry-db`. They do not read, restore or silently recreate retired ready /
pending JSON ledgers. Synthetic JSON in isolated unit fixtures is not a fallback.

| Operator | Preserved checks / output |
| --- | --- |
| `tools/audit_install.py` | Integrated public headers, optional real provider SDK, installed archive original mangles; DB snapshot provenance replaces ledger-file provenance. |
| `tools/recovery/audit_role_build_basic_activity.py` | **Actual cycle role audit**: all 42 original assertion ASTs are unchanged, including its 35 enumerated no-RTTI exceptions, actual provider/private include/math policy, compile-once partitions and relocated role consumer checks. |
| `tools/recovery/audit_fader_queue_router_checkpoint.py` | **Actual cycle full checkpoint audit**: current Linux integration/logs, all source/proof hashes, explicit Core dependencies, bounded ready proof coverage, disjoint identities, tracker counts and expected suites. |
| `tools/recovery/audit_recovery_checkpoint.py` | Same generic full checkpoint gates; explicit repository/output options. |
| `tools/recovery/generate_hal_symbol_tracking.py` | Original priority selection, function/data distinction, exact original identities, source-current labels and bounded/hardware fields; operation-local guarded cache. |
| `tools/recovery/count_current_unique.py` | Pinned unique-workload policy hash, 13 wrappers and exactly 10,173 defined nonempty host names; all-role completion and declaration-pending buckets. `--output` never overwrites an old result. |

`audit_role_build.py` and old batch-specific apply/admit/count derivatives were
not silently promoted to the actual cycle role policy. In particular, the
generic role audit has different RTTI/provider assumptions: use the actual
`audit_role_build_basic_activity.py` derivative. Historical batch scripts still
requiring retired JSON must not be run as active operators without a separately
reviewed migration. Old reports, fixtures, snapshots and trash contents remain
preserved; no permanent deletion is performed by these ports.

Example current operations, from the repository root:

```sh
uc-library/.venv/bin/python uc-library/tools/recovery/count_current_unique.py --output evidence/recovery/2026-10-30/ONE_CYCLE/unique-current.json
uc-library/.venv/bin/python uc-library/tools/recovery/generate_hal_symbol_tracking.py --output-dir evidence/recovery/2026-10-30/ONE_CYCLE/hal --markdown uc-library/HAL_SYMBOLS.md
uc-library/.venv/bin/python uc-library/tools/recovery/audit_fader_queue_router_checkpoint.py --ready EXPECTED_READY --pending EXPECTED_PENDING --mangles EXPECTED_NAMES --suites EXPECTED_SUITES --phase ONE_CYCLE --output evidence/recovery/2026-10-30/ONE_CYCLE/checkpoint-audit.json
```

Do not run the final source audit until Root has published current integration,
all real changed-header/native family proofs and the reviewed SQLite admission.
The full checkpoint audit retains source/proof checks and final dirty-file
checks; its report binds the DB generation rather than inventing retired JSON
SHA fields. Current build/format inputs remain current global checks.

## Historical build/format context preparation

`prepare_cycle_admin_context.py` is a **preparation-only** operator. The explicit
allowlist is exactly `CMakeLists.txt`, `cmake/ProductionSourceGroups.cmake` and
`validation/formatting.json`. Exact bytes were independently archived before
Root changed those artifacts. Their role is historical administrative build /
format producer context; this does not archive any implementation code.

The real `include/presonus/surface_panel/ControlHelpers.hpp` dependency affects
127 identities (100 ready, 27 pending). All 127 are excluded from pure metadata
admission and need actual new header/family behavior replays. Prepared all-context
rows are review material only: Root must never overwrite a freshly replayed
family row with their old real source bindings. Ready original native proofs
remain unchanged; pending rows get new exact membership with previous validation
references retained. Domains, declarations, flags, statuses, real CPP/H/HPP,
Core and behavior source bindings remain unchanged by the preparer.

Root alone performs fresh current formatting, CMake/partition/build/installed-role
checks, full Linux integration, original/proof/source gates and a backed-up
journaled SQLite transaction. Exact producer-context relocation cannot substitute
for changed implementation behavior validation. Preparation writes only new
candidate artifacts, never ACTIVE DBs, global sources, old JSON or trash files.

## Role-reader alias regression and pending packet normalization

The actual role tool's source-hash dictionary is named `snapshot`. Its SQLite
reader is imported as `registry_snapshot`, avoiding a Python local-name shadow.
`test_role_snapshot_alias.py` reads the actual maintained role source, executes
its exact dictionary / reader / per-role-mangle AST stage, and reconstructs the
former two-name preimage in memory to verify that it raises `TypeError`. No
ignored candidate fixture is required by this regression; all 42 role-policy
assertions and 35 no-RTTI exceptions remain unchanged.

Pending inputs must be classified explicitly before the combined admission:

```sh
uc-library/.venv/bin/python uc-library/tools/registry/normalize_pending_fragments.py --library uc-library --canonical CANONICAL_PENDING_FRAGMENT --raw FRESH_RAW_PENDING_FRAGMENT --output uc-library/candidates/NEW_PACKET/pending-raw.json
```

Repeat `--canonical` / `--raw` for multiple disjoint inputs. Canonical rows carry
an outer membership pointer in `validation`; normalization selects the original
`behavior_validation` as raw `validation`, or removes raw validation when native
behavior evidence was absent. Thus the unchanged merger cannot accidentally
replace native behavior evidence with an old membership proof. Fresh raw rows
retain their actual native validation pointer. Ambiguous raw/canonical mixtures,
duplicate original keys, stale native or old membership hashes, mismatched old
membership sources, and dirty evidence files fail closed.

The new outer fragment is exact pending membership; the separate receipt binds
all input hashes, native proof presence/absence and expected final canonical row
hashes. Sources, domains, declarations, statuses and flags do not change. Shared
proof files use a fresh operation-local cache with final logical-path/stat
checks. This tool never writes a DB or adds native behavior credit. Final packet
assembly waits for all 127 real fresh family rows plus the four new pending
records; it does not promote the 127 old header bindings into fresh evidence.
