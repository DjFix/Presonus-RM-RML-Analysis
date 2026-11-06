# Recovery source and local operating evidence

Updated 2026-11-06 while reconstruction remains paused.

## Why the large reports were committed

Root (the coordinating coding agent) wrote one-run Python programs for individual
integration runs. `seal_current_proofs130.py` belongs to integration130;
`seal_current_proofs271.py` was derived from that recipe for a later integration.
These are not old and new persistent coordinator services. No maintained recovery
entry point imports these numbered programs; Root invoked them explicitly.

The maintained tools still perform the real gates:

| Component | Purpose |
| --- | --- |
| `uc-library/tools/recovery/accept_worker.py` | Check a worker handoff and execute its bounded checks |
| `uc-library/tools/recovery/validate_linux_integration.py` | Run canonical Linux/build/test/install/role checks |
| `uc-library/tools/merge_readiness.py` and registry adapter | Validate current proofs and perform guarded SQLite admission |
| Numbered `audit*`, `seal_current_proofs*`, `admit*` programs under local temp/evidence | Assemble inputs, source rebindings and receipts for one particular integration |

Changing production source requires fresh source-bound evidence even when the
coordinator is unchanged. It does not require modifying old executed producers,
copying their outputs into source control, or rerunning old integrations.
Historical scripts/proofs must remain immutable locally because provenance can
refer to their exact hashes. A reusable future operator should be maintained in
tools with explicit inputs; implementing that redesign is outside this cleanup.

`FINAL_SOURCE_DRIFT01.json` holds 599 complete registry records and their source
changes. Repeated source/hash maps account for most of its 64 MiB. Root's sealing
program used it as a transaction input; workers do not need that entire report
as their reconstruction assignment. Workers need selected context, source,
original identities, replay inputs and relevant bounded evidence.

The Git mistake was in staging: `commit_plan130.py` collected imported trees and
validation outputs; `stage130.py` recursively added evidence and used
`git add -f`. The later staging workflow repeated that pattern. Existing ignore
rules were bypassed. A file being textual or below 100 MiB was an insufficient
selection rule.

## Current boundary

Keep source, maintained tools, executable tests, necessary replay fixtures and
concise documentation in Git. The human symbol tracker remains intentional.
Keep generated proofs/fragments, HANDOFF metadata, runtime logs, registry/source
snapshots, machine coverage, backup databases and one-run coordinator programs
local. Do not commit recursively growing hash manifests as a replacement for the
reports. Local preservation is distinct from a backup/distribution mechanism.

Existing replay inputs still located under evidence/candidates are enumerated in
`tools/git-artifact-policy.json`. New fixtures belong in `uc-library/tests/`.
Some historical CMake checks read local evidence/proofs directly; those files
remain on VM101, unchanged. A fresh clone still needs the explicit local evidence
and firmware environment to reproduce those checks. This cleanup does not remove
or weaken them or pretend the repository is a standalone evidence archive.

Install the hook in each new checkout:

```
git config --local core.hooksPath .githooks
python3 tools/check_git_artifacts.py --tracked
```

The guard reads staged paths/blobs and the staged exception policy, rejects
force-added local reports, and rejects new/modified blobs above 20 MiB. Use
`--tracked` to additionally audit all tracked paths. Existing firmware/database
inputs outside this cleanup are not silently removed by the size check.
Hooks are a workflow guard, not a security boundary; do not disable them or use
`--no-verify`. Review any proposed exception and its actual test consumer.

## Cleanup and history

The cleanup uses index-only removal. All removed paths retain their exact local
bytes. The full before/after manifest is local at
`temp/recovery-work/git-hygiene292/UNTRACK_MANIFEST.json`, with verification in
`VERIFIED.json`; these are themselves operating reports, not new Git content.

No commits are rewritten. Old blobs remain in existing history, so this change
alone does not shrink old clones or guarantee that pushing previously unpushed
old commits avoids large-file warnings. Reconstruction remains paused. The
AGENTS.md change must be reconciled with packet instruction hashes on explicit
resume; no packets are resealed during cleanup.
