# Stable source identities, version 2

Source identity is separate from original ELF identity. No changes to ELF SHA,
firmware version, original mangled names, ranges, provider bindings or readiness.

`code_identity.py` defines the versioned compile-context descriptor: source path,
working directory, ordered compiler arguments (including output target), and
analysis arguments. Known path operands are resolved relative to the compile
working directory and made repository-relative where possible. Compiler flags,
macro values, argument order, target output and multiple configurations remain
significant. Captured `gcc_validation` paths and compile-list ordinal are not
identity inputs. This does not claim arbitrary command-line semantic equivalence.

A TU is `tu:<context hash>`; ownership is `<group>:<context hash>`. The context
exists before AST extraction. An unresolved AST call hashes its source function
and site, including the stable TU. GCC anonymous entities and unresolved calls
use the stable context instead of the compile-command ordinal. GCC symbol-table
numbers remain local discriminators; this does not promise stability across
arbitrary compiler versions or a changed symbol table.

Logical GCC relationship evidence carries the source and compile-context ID.
Capture paths and raw dump hashes no longer determine relationship identity.
`observations` is append-only: each payload binds exact AST/GCC paths and hashes,
input hashes and owner. `current_observations` selects the current observation
per contributor. Its GCC JSON binds the raw dump and its hash. Observations with
different capture paths or hashes remain separate even when the logical edges
are identical. Shared edge contributors remain in `edge_facts`; replacement
must not retract a logical tuple while any contributor remains.

`normalize_ast` provides an explicit legacy TU/indirect-node mapping, recomputing
opaque indirect IDs rather than replacing substrings inside hashes. It rejects
ambiguous identities and node collisions. Original observations stay intact.
The Clang cursor cache checks equality within hash buckets; a cursor hash alone
is not a declaration identity.

## Isolated rehearsal

Run from the project root, with a new output directory each time:

```sh
uc-library/.venv/bin/python dependency-graph/check_identity_migration.py \
  --out temp/recovery-work/dependency-graph/identity-v2-NEW \
  --run temp/recovery-work/dependency-graph/refresh/1793460399608072116 \
  --pairs evidence/recovery/2026-10-31/dependency-graph/delta-scope-audit-01/observation-comparison.json
```

This builds independent previous/current v2 indexes from retained observations.
Both sides reparse retained GCC dumps with the same current parser, separating
parser-coverage changes from changes of code dependencies. Sidecars preserve
legacy hashes, paths and every TU/indirect alias. This is a derived diagnostic
migration, not a claim that historical proofs ran a newer producer. The output
contains observations, ownership, logical-edge differences and integrity checks.
It does not compile, contact Memgraph, activate an index or rewrite old deltas.

For a v1 operational index/pending publication, preparation/resume
fails closed before modifying them. Direct publisher entry also rejects a v1
plan. Do not add a version marker to the old DB manually. Activation requires
reviewed physical ID/provenance migration and a separate supersession record
bound to the old sealed delta and verified server baseline. One-time physical
relabeling is distinct from the logical code delta measured here.

Bounded publication with server-side checkpoints and a `refreshing` gate until
all checks pass is described in [BATCH_PUBLICATION.md](BATCH_PUBLICATION.md).
Neither a successful isolated rehearsal nor a logical zero delta makes the
currently refreshing server graph ready for dispatch.
