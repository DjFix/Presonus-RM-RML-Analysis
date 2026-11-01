# Firmware extraction and C++ reconstruction policy

These rules apply to recovery of the PreSonus mixer/surface applications and
their UC, DICE, audio, panel, hardware and supporting functions.

## Preserve symbol identity and C++ scopes

- Retain each original ELF mangled name verbatim, alongside its demangled name,
  address, size, section, firmware version and input ELF SHA-256. Never replace
  an original name with a generated friendly name in the recovery manifest.
- Reconstructed original interfaces and implementations must retain the
  original, case-sensitive C++ namespace and class scopes: for example
  `Presonus::UC::DicePacketQueue`, `Presonus::DICE::SysexPacket` and `Core`.
  Put buildable definitions inside their corresponding namespace/class scopes.
  A qualified name printed by a decompiler is not a recovered class definition.
- Place buildable implementations directly under `src/` (for example
  `src/Presonus/UC/`); do not add a `src/recovered/` directory component.
  Public include directories must also omit `_recovered` suffixes.
- Preserve the recovered parameter types, const/reference/pointer qualifiers,
  overloads, member/static distinctions and C linkage where evidence establishes
  them. Do not infer return types, class fields, inheritance, ownership or static
  membership from a mangled name alone; record unresolved details explicitly.
- Track constructor/destructor variants, aliases and compiler thunks by their
  original symbols. Shared entry addresses may share code/pseudocode, but every
  symbol's byte range must be checked separately. Do not invent ordinary C++
  method names for compiler-generated ABI variants.
- Check the compiled symbols of reconstructed implementations against the
  original mangled names with a suitable symbol tool. Account explicitly for
  object-format decoration, such as Mach-O's extra leading underscore.
- Portable convenience APIs may use a separate namespace, such as
  `presonus::uc`, but must be identified as independent wrappers. They do not
  replace the recovered original namespaces or establish original ABI fidelity.
- Matching names is not proof of binary compatibility. Distinguish a portable
  source port from an ARM32 ABI-compatible implementation; claim layouts,
  calling conventions and binary interoperability only with matching evidence.
- Use filesystem include paths with consistent actual casing on macOS and Linux.
  Do not create case-only sibling directories on a case-insensitive filesystem;
  filesystem path casing does not change the required original C++ namespace.

## Core upstream source policy

- Read [Core framework lineage and API comparison](docs/core-framework-lineage.md)
  before Core recovery or integration. The captured earliest public release is
  CCL 5.0.0, commit `e8cbdea4a4a20e15111f5a690798a259c0374b31`; verify it from
  fetched Git history. The historical report also compares CCL 5.2.0; the
  completed 5.0.0 mapping is in the recovery library's
  `validation/core-upstream/source-map/`. Reuse that hash-bound evidence rather
  than repeating the historical comparison.
- Do not reconstruct Core implementation source from firmware binaries. Use
  the pinned official CCL source under `third_party/` and bind recovered
  application code to its actual types and implementations. Preserve upstream
  namespaces, source, commit identity and license notices.
- Replace unresolved Core dependency hooks with real CCL-backed adapters where
  an appropriate API exists (sockets, locks, buffers, containers, clocks and
  parameters). Do not define fake Core classes or legacy Core implementations.
  Test doubles may capture boundaries but are not production Core providers.
- Match the selected release's real declarations and implementations against
  original ELF symbol identities and compiled mangling. Skip manual recovery
  for source-provided matching APIs; reconstruct remaining app-specific work.
  Preserve original symbol/version/hash records and explicit API differences.
- Where upstream Core differs, prefer source-based behavior and record any
  app-specific adaptation as an intentional source port. Do not label matching
  mangling or available upstream source as original binary-behavior, layout,
  ARM ABI or hardware verification. Unencoded original return types remain
  unresolved unless independently established.
- Keep Core binary decompilation excluded. Actual CCL source integration and
  application bindings are authorized and required. Track source-provided methods separately from validated portable
  reconstructions and unresolved app-specific dependencies.

## Share client/server reconstruction where supported

- Before introducing separate client/server source folders, compare exact
  mangled-symbol intersections and existing non-Core decompiler patterns for
  the selected binaries. Record denominators, normalization rules and concrete
  differences; similarity alone is not semantic or ABI verification.
- Recover a shared implementation once. Preserve per-binary original identities
  and evidence, and retain distinct original namespaces through thin original
  interfaces plus an explicitly independent common helper when appropriate.
- Prefer a common source library with separate CMake client/server targets when
  measured overlap supports it. Keep proven role-specific behavior explicit;
  do not create stub applications or rename original symbols merely to obtain
  two build targets. Core continues to come from CCL source.
- The active build uses `cmake/ProductionSourceGroups.cmake`: add each new
  production CPP to exactly one common/CS18/RM OBJECT partition. Keep shared or
  mixed units common; classify exclusive units from original symbol ownership
  and native dependency evidence. Do not add CPP bodies directly to archive
  facade targets or duplicate them for both roles. Keep explicit public header
  lists consistent and replay the per-role archive/compile-once audit.

## Automatic C++ formatting

- Always run an automatic syntax formatter on reconstructed `.cpp`, `.hpp` and
  `.h` files before their final build, validation replay or readiness seal.
  Use the project's configured C++ formatter. If none is configured, use
  `clang-format --style=file --fallback-style=LLVM -i` on explicit source paths.
- Verify the same paths with `clang-format --style=file --fallback-style=LLVM
  --dry-run --Werror`. Record the formatter version in the validation evidence.
  If the formatter is absent, install it in the project-local tool environment;
  do not silently skip formatting.
- Format only the reconstructed files in scope; preserve unrelated/vendor code
  and raw, unvalidated decompiler output. A formatter does not turn pseudocode
  into valid C++ and does not prove semantic or ABI equivalence.
- Format before recording source hashes. If formatting changes an already
  sealed source, replay the affected compile/symbol/behavior checks and reseal
  its current hashes before marking the function ready again.

## Keep an evidence-backed symbol tracker

- Linux on VM101 is the canonical validation target. Run reconstruction builds,
  formatter checks, symbol checks, behavioral replays and integration tests on
  Linux; skip further macOS builds/tests unless the user explicitly requests them.
  Ongoing editing and hash audits run on VM101; historical Mac data stays in backups.
- Preserve existing macOS evidence as historical results. Do not wait for or
  require a macOS replay before admitting Linux-validated work. The canonical
  `validation/integration.json` must contain the current Linux proof; retain
  `integration-linux.json` as its compatibility copy and archive prior proofs.

- Maintain a Markdown symbol tracker covering the entire requested workload,
  with per-binary function/data tables and links to recovery evidence. The
  canonical tracker is `uc-library/SYMBOLS.md` on VM101.
- Update the tracker after each extraction/reconstruction phase. Use separate
  statuses for catalogued symbols, extracted bytes, verified bytes, exported
  pseudocode, compiled C++, mangling/namespace checks, behavioral validation and
  hardware validation. Record failures, pending work and bounded test domains.
- Verify extracted bytes against the SHA-256-identified source ELF using the
  symbol's actual section mapping and range. ELF symbol-table row numbers are
  not file offsets. Record zero-initialized `SHT_NOBITS` data separately.
- A decompiler export is unvalidated analysis evidence. Keep it separate from
  buildable sources, label it clearly, and do not mark a function ready merely
  because pseudocode exists or a stub compiles.
- Mark a reconstructed function ready only for the scope supported by its
  namespace/signature checks, reviewed implementation and behavioral evidence.
  Byte matches, roundtrip tests, loopback tests and ARM differential tests prove
  different things; do not substitute one for a broader completion claim.
- Preserve the full requested scope. Extract DICE first, then proceed through
  the remaining mixer/surface and supporting functions. Reuse completed work
  only after checking source identity and maintain explicit coverage of aliases.
- Keep background-job handles, logs and resumable state. Inspect a live job
  before retrying; an observation timeout alone does not justify restarting it.
- Preserve newly produced logs, fixtures, source hashes and validation proofs in
  a structured local `evidence/recovery/` tree on the analysis VM; reverse synchronization to Mac is no longer required.
  Capture new output going forward; do not spend time recovering historical logs
  instead of processing remaining symbols.
- During delegated work, assign separate class/namespace and file ownership.
  The coordinating agent integrates shared build files and the global readiness
  ledger so independent workers do not overwrite one another's results.
- Keep ready and declaration-pending ledgers disjoint, keyed by original ELF
  SHA-256 and mangled name. Pointer-valued/string behavior alone does not prove
  the original static pointer return declaration or character const qualification.
- The converted `merge_readiness.py`, `generate_symbol_tracking.py` and
  `generate_checkpoint.py` use the operational SQLite registry identified by
  `uc-library/validation/registry-sqlite/ACTIVE.json`. Use the shared registry
  adapter and an explicit database override for isolated tests. Do not fall back
  to, overwrite or refresh the preserved legacy ready/pending JSON implicitly.
  Explicit JSON imports create a new independent baseline and working generation;
  preserve meaningful task/history data by original identity and retain old DBs.
  Keep fresh proof/source/Core/format/integration checks, optimistic transaction
  guards, backups and append-only classification journals. Stale existing records
  must fail admission rather than disappear silently. Archive historical producer
  inputs with exact hashes and explicit provenance when their working paths change;
  never relabel a historical proof as having executed a newly changed producer.
  Other legacy JSON consumers require explicit migration before using them after
  SQLite admission changes. Operator and schema-upgrade instructions are in
  `uc-library/tools/registry/README.md`.
- Use the readiness merger's guarded `--demote` manifest for ready-to-pending
  transitions: previous proof hash, explicit reason and fresh pending validation.
  A validated explicit promotion must remove the old pending entry. Preserve both
  previous ledgers and classification journals; do not disguise demotion as stale
  source removal. Verify read-only preflight before actual admission.
- Constructor/destructor readiness must reflect actual variant and lifecycle
  observations. Record native C1/C2 aliasing explicitly while checking every
  original range separately. Validate D1/D0 target identities and actual
  deallocation/cleanup behavior; a manually appended delete event is not evidence
  that the native deleting destructor deallocated an object.
- Before handing off active-source fragments, run `tools/merge_readiness.py
  --dry-run` with their ready/pending arguments on the analysis checkout.
  Preserve its output and expected totals. Include canonical proof flags,
  nonempty per-function validation domains, current formatting bindings and
  explicit repository-relative CCL dependencies. A green fixture replay alone
  does not prove that a fragment meets the readiness schema.

## Project trash and deletion approval

- Use `.trashes/` at the repository root as the project trash. During project
  housekeeping, move files selected for deletion there first, retaining their
  original paths relative to the repository root: `path/to/file` becomes
  `.trashes/path/to/file`. Do not discard existing work products directly.
- Record each move with its original path, trash path, size, SHA-256, timestamp
  and reason in a managed move manifest. Verify the moved bytes; preserve links
  to prior evidence and do not rewrite historical provenance cosmetically.
- Never overwrite an existing trash entry. If the original relative path is
  already occupied, use a dated batch directory inside `.trashes/`, retaining
  the complete original relative path beneath that directory.
- Permanently delete trash contents only after the user's explicit permission
  for that deletion. Moving something to trash is not permission to purge it.
- Keep trash contents outside Git. This policy does not authorize moving
  unrelated user files, firmware inputs or still-required evidence into trash.

## Working locations and firmware boundaries

- The canonical project is `/home/rs/projects/opencs/ai-line-analysis`
  on VM101, with `uc-library/` at its root. Work directly on VM101; do not run
  legacy Mac-to-VM or VM-to-Mac synchronization.
- Recovery operators are in `uc-library/tools/recovery/`. Runtime control
  and scratch use `temp/recovery-work/`; generated CTest work uses
  `temp/test-work/`. The complete former temporary tree is preserved at
  `evidence/recovery/2026-10-28/vm-migration/legacy-uc-recovery/`.
  Exact moves are recorded in the adjacent `relocation.json`.
- Use `uc-library/.venv/bin/python` and its CMake, CTest and clang-format
  for validation. Agent utilities are in `/home/rs/.local/bin`.
  The active Linux build is `temp/core-upstream/root-integration-01`.
- Historical chat paths and proofs retain their original provenance.
  Translate working paths using the relocation record; do not cosmetically
  rewrite historical proof files. Decode FPGA board photographs are in
  `images/board-attachments/` with a SHA-256 manifest.
- Extract UC launch is awaiting a directly approved user message to migrated
  thread `01a17fc6-3e44-7dd1-beb3-319f5d4d97a0`. Preserve the research pause
  until that launch message arrives. Then work directly on Linux with subagents,
  using this checkout and the existing proof/readiness workflow.
  Scoped exception: the user explicitly authorized one real reconstruction trial
  in the current graph-development chat on 2026-10-31, after ELF context and empty
  packet rejection are implemented. This authorization supersedes the destination
  chat restriction for that one trial only. That trial is now closed with two new
  C++ implementations and three compiled-pending ELF identities; evidence is in
  `evidence/recovery/2026-10-31/dependency-graph/live-trial-02/`. Do not start another
  reconstruction batch without a new user instruction.
- Use `docs/vm101-chats.md` for migrated destination thread IDs and explicit
  VM101 host links. Historical source IDs retain their original provenance.

- Keep temporary scripts, scratch files, archives and work products inside the
  project's `temp/`, never in system temporary directories. Maintained tools may
  live with the recovery library. The same rule applies on the analysis VM.
- Wait for an existing checkout to finish before modifying its tracked content;
  do not interrupt or replace a clone without authorization. A verified matching
  VM checkout may be used for analysis while the local clone is unfinished.
- Preserve existing guides, firmware inputs, completed exports and unrelated
  user changes. Record which checkout, ELF version and hash each result uses.
- Distinguish host application functions, embedded DICE/processor firmware and
  FPGA data. Extract blobs with their names, offsets, sizes and hashes; do not
  present them as recovered C++ functions without further architecture/layout
  analysis and validation.
- Analyze firmware programming/erase functions offline. Do not execute device
  update, erase or flashing operations as part of extraction or verification.
  Hardware interoperability testing is deferred until the devices are available
  and the user authorizes that testing.

## Approved efficiency trial

- The user approved process-audit recommendations 2, 3, 4, 6 and 9 on
  2026-10-27. Follow `docs/reconstruction-process-trial.md` for the next
  three completed batches: generated compact checkpoints, small disjoint
  candidate batches, consolidated scoped sync, phase/queue timing and compact
  conversational output with full logs retained.
- Preserve all existing formatting, full Linux tests, active-source proof,
  mangling, readiness, installed-role and mirror-audit requirements. Keep exact
  shell commands visible. These recommendations do not authorize the separate
  admission-runner/schema redesign or proof-reuse changes from the audit.

## Graph-selected context before reconstruction subagents

- The user authorized Memgraph context selection on 2026-10-31. Before delegating
  a reconstruction/research subtask, Root prepares a task with exact original
  ELF SHA-256 and mangled identities, namespace ownership and disjoint owned files.
  Run `uc-library/.venv/bin/python uc-library/tools/recovery/select_context.py
  prepare --task TASK.json --out temp/recovery-work/UNIQUE_PACKET`, then `dispatch
  --packet PACKET`. Use the generated `DISPATCH.json` as the arguments to
  `collaboration.spawn_agent`, normally with `fork_turns="none"`. Do not replace
  the packet with the whole coordinator chat or broad proof bundles.
- For parallel workers prepare all packets before edits, then use
  `batch-dispatch --packets PACKET... --out temp/recovery-work/UNIQUE_BATCH` before
  spawning the first worker. It rejects write/read dependency conflicts and mixed
  generations. Dispatch the sealed batch, not independently reselected contexts
  after another worker has begun editing. Root retains shared CMake/build files,
  global trackers, registry and final admission ownership.
- Workers read AGENTS.md, TASK.md, SOURCE_SLICES.md and CONTEXT.md. Use the bound
  ELF_CONTEXT.md supplies hash/range-verified native target bodies and typed
  one-hop relationships for unreconstructed methods. Each target must have a real
  source or native body; research mode and uncertainty_work never permit an empty
  packet. ELF SHA-256, firmware version, role and original range remain separate
  identities. Cross-version name correspondences are never execution edges.
  SQL symbol_resolution.strategy=external_source means use the pinned provider,
  not firmware recovery. Binding status verifies only its recorded scope; it is
  not readiness or proof of original return/layout/behavior/ARM ABI.
  baseline source snapshots if workspace files changed. Missing context is an
  explicit request to Root with a query, seed and reason; Root uses `expand`.
  `expand --baseline` is for an already dispatched task's frozen generation,
  never a claim that its graph describes newly edited source. No silent truncation
  or interpreting missing mappings as independence. Unmapped original symbols
  require an explicitly scoped research task, not an empty reconstruction packet.
- Memgraph is a derived code index; SQLite remains canonical for original
  identities, readiness and current proof links. Ordinary registry assignments
  do not invalidate code context. Selected target/evidence changes require a new
  packet. `prepare` automatically refreshes changed source/build observations and
  registers the new graph under a shared lock before selecting context. It reuses
  unaffected compiler observations; headers invalidate all captured dependent TUs,
  configuration changes and added/deleted source/header paths conservatively
  replay all current compile commands (including optional-include/glob cases).
  Prepare the next batch after the preceding workers finish editing. A failed
  refresh blocks preparation; a durable publication journal is retried on the next
  preparation. There is no ignore-staleness override. Registration must not
  bless source hashes that differ from the graph's captured inputs.
- This gate changes initial reading context only. Preserve all existing Linux,
  formatting, active-source, mangling, behavior, role and readiness gates. It
  does not release the Extract UC launch pause or authorize hardware work.
  Operator details: `dependency-graph/CONTEXT_SELECTION.md`.

## Worker delivery and automatic acceptance

- Reconstruction workers own the complete local cycle: original ELF range
  verification, C++ implementation, independent native/provider observations,
  replay fixtures, executable replay, formatting, compilation, mangling checks
  and local proof. Follow `docs/worker-handoff.md`, version 1. Deliver a
  hash-bound `HANDOFF.json`; prose alone is not a reconstruction handoff.
  Research-only tasks must explicitly report no reconstruction handoff.
- Workers use original ELF instructions as the native oracle, not expected
  values computed from their new C++ or decompiled pseudocode. Core continues
  to use the pinned official provider; no Core binary reconstruction. Record
  memory assumptions, stubs, coverage, unresolved declarations and exclusions.
  Prepare replay integration metadata without editing shared CMake or ledgers.
- Root reviews the bounded handoff and exact argv, then runs
  `uc-library/.venv/bin/python uc-library/tools/recovery/accept_worker.py
  --handoff PATH/HANDOFF.json --out temp/recovery-work/UNIQUE_ACCEPTANCE`.
  It checks hashes, runs format/compile/symbol/replay checks and records timings
  and logs. This executes worker code; it is not a sandbox or semantic reviewer.
  Local acceptance is not readiness admission. Root retains shared integration,
  canonical Linux/full CTest, installed-role/compile-once audits, fresh proof,
  guarded SQLite dry-run/admission, tracker and mirror audit. Preserve every
  existing gate; do not invent fixtures or rewrite a worker's native proof at
  Root merely to make admission pass. Return local failures to the owner.
- The user authorized a follow-up real reconstruction trial after completion
  of the Compare SQLite and Neo4j thread
  `01a18eec-1cfe-7962-8411-1bfd168bba4f`. This is conditional authorization,
  not an immediate batch launch. Record explicit completion evidence before
  starting; no new permission is needed once that condition is satisfied.
  Freeze infrastructure before measurement. Record Root and each worker's
  session ID, cumulative token baseline/end (cached input is a subset), wall
  timestamps and tool durations separately. Distinguish packet preparation,
  worker reconstruction, local acceptance, global integration and reporting;
  record overlaps, context requests, failed preparation and redundant checks.
  Infrastructure changes during the trial are separately charged, never hidden
  as ordinary reconstruction or omitted from whole-cycle totals.

## Unique ELF work before graph packets

- The derived unique-work index is selected by `dependency-graph/DEDUP_ACTIVE.json`.
  `select_context.py prepare` plans and claims one unique work item before source
  refresh/selection and includes all covered original identities in the packet.
  Name equality, exact bytes and shared portable implementation are distinct.
  Unresolved equivalence requires a research comparison; external providers use
  binding/adapter work. Existing canonical C++ goes to explicit
  `review_existing_result` audit/research, never repeated firmware reconstruction.
- Keep claims and their history. A failed prepare retains its claim. Inspect the
  live process/agent and resumable state before explicit release; timeout alone
  does not authorize stealing. Batch dispatch checks unique work identities in
  addition to file/dependency conflicts. Changed generations or decisions require
  re-preparation. No group automatically inherits readiness from a representative.
- Operator/schema details: `dependency-graph/DEDUPLICATION.md`. This gate does not
  authorize a new reconstruction batch or change the canonical readiness schema.

## Conversational reporting adjustment

- The user requests status separately. Omit routine cycle/checkpoint reports and
  unsolicited progress counts. Keep required work updates and actionable blockers
  brief. Preserve all validation gates, evidence logs, generated checkpoints and
  symbol tracker updates; avoid repeated inspections solely for chat reporting.
