# SQLite-only reconstruction trial

The 2026-11-25 instruction stops production graph updates for this and all subsequent cycles. The first cycle measures the new operating mode. Use the operational SQLite registry for identity, status, history and proof links, and its assignments for exclusive ownership. Select and issue work only from SQLite. During reconstruction resolve dependencies from the current source, compiler inputs, pinned providers and hash-verified original ELF ranges. Record the exact inputs for each handoff. Select up to ten independent owners and ten implementation targets per owner; admit completed work incrementally.

Preparation, worker activation, acceptance and final admission run without Memgraph queries, graph snapshots, refresh, publication or graph-generation checks. Never fall back to the graph path on an error in this trial. Preserve the existing CT and historical index. Document a missing dependency on the affected target and select a replacement. Check actual source read/write sets and sealed source hashes at issue and integration. Continue all native, source, formatting, compile, Linux role, SQLite admission and tracker checks.

Measure wall time from the first selection through SQLite readback. Record original and replacement targets, worker launches, new implementations, existing-source audits and declaration-pending entries separately. Identify any overlap with unfinished work that started before this trial. Prior graph-backed workers retain their original evidence and denominators.

## Running a cycle

Run the packet operator from the project root with the selected plan and a fresh output directory under `temp/recovery-work/`.

```sh
uc-library/.venv/bin/python uc-library/tools/recovery/sqlite_packet.py prepare --plan "$plan" --out "$packet_dir"
uc-library/.venv/bin/python uc-library/tools/recovery/sqlite_packet.py dispatch --packet "$packet_dir"
```

Launch the workers listed in `DISPATCH.json`. Verify the compiler's actual dependency files against the accepted sources using `sqlite_dependency_gate.py`. Retain the scoped native, portable and installed-role observations with each handoff. After the guarded readiness merge, use `sqlite_admission.py` to finalize the assigned catalog rows against the exact merge receipt.

### Same-owner reproof revisions

When a guarded reproof advances an assigned task revision, keep the original
packet and assignment journal and bind the later journal and live readback
during finalization. Verify that the later revision retains the same owner,
batch and exact original write scope. Append the admission evidence to the
latest notes and finalize against the verified current revision. If that
chain is incomplete, preserve the task assignment and resolve the missing
evidence before closing it.

A same-owner companion write requires its own approved exact scope and
guarded catalog revision. Bind the approval, original packet, revision
journal, current readback and exact companion source hashes. An ordinary
reproof receipt cannot confer write ownership. Finalize against the
verified current revision after the same admission gates.

### Configured compile modes

Compare the configured compile and link commands with the accepted
production and replay commands before a full Linux run. A flag can be
equivalent when the pinned provider defines the same value. Demonstrate
equivalence for each affected translation unit with byte-identical
preprocessor outputs from the actual configured command with and without
the worker definitions. Bind both commands, outputs and the raw
comparison. Resolve every other mode difference before running the suite.

### Historical replay inputs

Before starting a full canonical Linux run, inspect the configured CTest
inventory for immutable dependency manifests passed through `--bindings`.
Compare every application source or header changed in the integration plan
against those manifests and the exact current source-transition rows. Check
the original archived dependency bytes even when an existing transition
covers several other files. When the changed path is absent from the
transition or its hash differs, archive the prior manifest, issue an exact
successor for the affected tests and run those tests before the full suite.
Preserve the original runtime fixture and its producer.

Also inspect the active Python checkers named by configured CTest commands
for inline current-source hash tables and hash fields resolved indirectly
from proof templates. An empty argv-manifest scan is insufficient. Compare
the exact projected source hashes with the checker's current assertions.
Archive the previous checker and provider bytes when a versioned transition
is needed, bind the rebuilt production and replay dependency files, and
target the real registered test before running the full suite. A hash used
only to identify archived inputs stays historical.

When a recovered constructor or newly implemented virtual callback changes
behavior used by an existing body-only replay, inspect the actual dependent driver and its original native oracle
state. Explicitly seed the oracle's timer, observer/parameter state and
callback-feedback preconditions in that driver. If the native oracle directly
installs observer state, use that direct setup rather than a setter that now
executes a newly recovered callback; retain the native tag and IO assumptions;
 preserve the original fixture and expected observations. Do not
change production defaults or weaken the constructor test to preserve an
implicit historical test setup. Retain the old driver, bind the exact
transition, and run both the affected body replay and the new constructor
variants before the full suite. Hash-only preflight does not detect this state
coupling. Enumerate the actual compiler `.d` dependency closure, including
derived-class replay drivers, before choosing focused tests. Class-name or
test-name filters alone are prohibited as the dependency inventory. Inspect
all dependent setter setup calls when a base virtual callback changes and run
the corresponding registered tests before the full suite.

Before registering an accepted replay in the canonical Release build, inspect
its assertion usage and actual worker compiler flags. If assertions execute
operations or validate the promised domain, compile that replay target with
`-UNDEBUG` after inherited Release definitions. Verify the generated command
and replay output. A successful binary with disabled assertions cannot prove
those operations; preserve the failed output and rerun the affected replay.

### Installed public headers

A name-only install-list comparison is not the required header preflight.
Materialize the actual configured install tree and compile every changed public
header from that tree before the full suite. Include unchanged application base
headers reached transitively; a source checkout include path must not hide an
absent installed dependency. Preserve the failing standalone translation unit,
correct the explicit public list, and demonstrate the actual compile succeeds
before continuing.

Before starting the full canonical Linux suite, compare the configured CMake
install destinations and source paths with the expected application header
inventory. Compile each changed public header against a temporary tree
containing exactly the configured headers and the pinned external SDK.
A missing name, wrong origin, or unresolved include requires an exact
install-list correction and a clean preflight before running the suite.

When an integration adds a public header or changes its application include
dependencies, compile a small translation unit that includes the installed
header from a fresh canonical install. Supply the pinned external SDK include
paths and omit the checkout application include path. If the check finds an
omission, measure the transitive set against the whole installed header
inventory and repeat from a fresh install after updating the install list.
Keep the affected readiness rows and consumer ownership open until the
official install passes. A temporary supplemented prefix may diagnose the
fix and must be identified in the evidence.

### Wave 07 public install follow-up

The canonical Linux run passed all 1,519 suites and the two installed role
archive audits. The public include audit found four missing transitive
headers. The 44 DAWClient identities retain their assigned custody and
remain outside readiness until the official installer runs with the fix.
The exact W07 archive and staged-prefix checks are recorded in
`evidence/recovery/2026-11-24/rolling-c001/rolling-compatible-queue/W07-DAWCLIENT-44-OFFICIAL-INSTALL-HOLD.json`.
Its SHA-256 is
`e6a0586f1a29895eb8b2d727b04fbc8b01034b4756f1e43181fe522b49c5686c`.

Wave 08 installed the four measured headers and passed the official
clean-prefix compile and all 458 application header checks. The separate
DAWClient follow-up verifies the common object in both installed archives.
Its minimal role probes use each archive independently. The full RM replay
uses the CS18 archive for the separately recorded test fixture providers.
The official proof boundary is
`evidence/recovery/2026-11-24/rolling-c001/sqlite-cycle02-wave08-daw-proofs01/OFFICIAL-PURE-ROLE-AND-FIXTURE-BOUNDARY.json`.
Its SHA-256 is
`fd0ce1c127c9982977df25f94d7a70c66e0ad2ce9a27dd050734c962e9e799f2`.

## Existing-source review log

- 2026-11-25. Verified ten deleting-destructor (D0) ELF identities for
  `ChDelayFormatter`, `ChGainFormatter`, `ChHPFFormatter`,
  `EarlyRefFormatter` and `GeqFreqFormatter`, one identity per class in
  each of the CS18AI and RM/RML roles. The bounded review covers the exact
  original ranges, role-specific allocator and deallocation observations,
  and five delivered portable replays. This review carries zero
  reconstruction credit and leaves readiness unchanged. The complete VM101
  archive is `evidence/recovery/2026-11-24/rolling-c001/formatter-d0-existing-review/`.
  Its `MANIFEST.json` SHA-256 is
  `266fd850373d1ba5902ce70ab6a777a8cbbcff1200e88e824ac1d1312791515a`.

When restoring a previously staged source or header overlay, preserve its exact
accepted/baseline bytes but invalidate dependent build outputs explicitly. A
`copy2` restoration can retain an old timestamp while newer objects still embody
the reverted interface. Touch the restored paths and run the authentic canonical
dependency build; verify the affected compile commands and rebuilt objects before
sealing. Matching source hashes alone cannot establish object freshness. Preserve
any failed stale-object link and the restored hashes; do not mask unresolved
symbols or repeat unrelated successful checks.

After the scoped formatter and dry-run succeed, use the maintained
`uc-library/tools/format_cpp.py` check-only path to refresh the canonical
formatting manifest for the exact paths. Physical formatting alone does not
refresh proof hashes. Verify every changed C++ source/header has its current
hash in `validation/formatting.json` before starting proof refresh/sealing.
Preserve prior formatting metadata and never rewrite source after a final build
merely to repair proof metadata.

Before an installed-role proof, distinguish a handoff's compiled artifact list
from the reviewed runtime provider requirements for that exact target. A shared
worker build may compile sibling formatters or other class methods that the
replay never calls. Keep every artifact/source hash and archive member binding,
but require runtime link-map presence for the explicitly reviewed caller/base
provider closure. Derive that closure from declarations, actual calls and
native/source-provider evidence before execution; never learn an exclusion
policy automatically from the resulting map. Missing real providers remain a
failure. Preserve prior proofs when issuing a narrowly scoped policy successor.
