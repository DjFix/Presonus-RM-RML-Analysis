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

## Conversational reporting adjustment

- The user requests status separately. Omit routine cycle/checkpoint reports and
  unsolicited progress counts. Keep required work updates and actionable blockers
  brief. Preserve all validation gates, evidence logs, generated checkpoints and
  symbol tracker updates; avoid repeated inspections solely for chat reporting.
