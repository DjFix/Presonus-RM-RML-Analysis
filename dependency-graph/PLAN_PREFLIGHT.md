# Cheap plan preflight

`plan_preflight.py` checks known physical write/write and explicitly declared
write/read overlap **before** claims, containers or AST slicing. It only reads
its supplied manifest, task JSON and optional proposal maps. It does not import
context, graph, registry or reconstruction operators. It is not connected to
batch prepare; Root must review integration separately.

```sh
uc-library/.venv/bin/python -B dependency-graph/plan_preflight.py \
  --tasks temp/recovery-work/MY_BATCH/TASKS.json \
  --out temp/recovery-work/MY_BATCH/plan-preflight01.json
```

`--root` defaults to this checkout. Every input/output path is repository-relative,
POSIX, normalized and case-correct. Absolute, empty, `.`/`..` components and
backslash paths fail closed. In-repository symlink aliases resolve physically;
hardlinks share identity. Links that escape the root are rejected before reading
their target. New owned files need not exist. Existing file paths must name regular
files. Inputs are hashed and checked for changes during observation. There is no
claim of protection from arbitrary concurrent editors after the check.

Input is the existing batch manifest shape: `tasks` contains task JSON paths;
optional `groups` contains `task_name` and `packets`. Packet basename identifies
`task_id`, matching existing grouped planning semantics; coverage must be exact.
Same-owner grouped writes/reads may overlap. Across owners `owned_files` are
physical writes and `declared_source_dependencies` are declared reads. Namespace
and original-class ownership are not a substitute for file coverage.

An optional task `source_proposal_map` is a `{path, sha256}` reference to the
existing `{worker, destinations}` format. `destinations` maps intended canonical
paths to actual proposal write paths; values must be owned by that same group.
Malformed hashes, paths, aliases and ownership fail. Canonical destinations are
reported separately for Root integration review; they are **not** concurrent
worker writes. Canonical source reads are never silently translated to proposal
paths. A missing map does not establish isolation or dependency independence.

Exit0 means **no known supplied conflicts**, exit1 means known conflicts (including
optional historical hints), exit2 means malformed/unusable inputs. Every receipt
sets `dispatch_authorized=false`, `independence_proven=false`. Missing implicit
reads remain unknown even when declared reads are present. This is not a gate
for original declarations, lifecycle, providers, native bodies or readiness.
The final current batch prepare/dispatch content/freshness/conflict gate stays.

## Frozen historical regression only

```sh
uc-library/.venv/bin/python -B dependency-graph/plan_preflight.py \
  --tasks temp/recovery-work/reconstruction-200-02/LARGE_TASKS01.json \
  --historical-contexts temp/recovery-work/MY_AUDIT/historical-contexts.json \
  --out temp/recovery-work/MY_AUDIT/historical-result.json
```

The hints manifest is `{"contexts":[{"task_id":"...","path":".../context.json",
"sha256":"..."}]}`. Each saved context must match task identity and its supplied
hash. Only `selected_file_sha256` keys are read hints; recorded generation is
reported. Context JSON is not retained in memory after extracting its read list.
Hints may cover a subset of tasks, and never imply coverage for missing tasks.

This option explicitly reports `stale_or_unknown` for a current plan. It does not
check current source hashes/generation, task contract freshness or historical
filesystem equivalence, and cannot authorize active dispatch. It is for reproducing
known historical conflicts conservatively; no silent inheritance of old context.

The real failed200 plan lacks the peer implicit reads that caused its late
42.27-minute rejection. Declared-only preflight does **not** cure that failure.
Hash-bound prior contexts reproduce the same two reported path overlaps cheaply;
physically isolated proposal writes remove those overlaps. This is a useful frozen
regression, not demonstrated current dependency completeness.

For a future active read-hint exporter, use the already current derived index:
require matching graph generation, exact selected target/contract/proposal-map
identity and current input hashes, then query the existing ownership/source
relationships without a fresh AST slice. Emit provenance, query scope and unknown
implicit/virtual/provider boundaries. If any binding is absent/stale, report
unknown and continue through ordinary mandatory prepare; do not mark independent.
That exporter/freshness integration is **not implemented here** and needs Root
review. Do not merely pass old contexts as current read evidence.

Tests:

```sh
uc-library/.venv/bin/python -B -m unittest discover \
  -s dependency-graph -p test_plan_preflight.py -v
```
