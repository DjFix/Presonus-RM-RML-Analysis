# Firmware symbol extraction and verification tracker

The extraction order is **DICE first, then the other mixer/surface functions**.
Tables are regenerated from completed byte exports and recorded per-address
decompiler results across UC, DICE and full-binary recovery scopes.
Unprocessed entries remain marked pending; exported pseudocode is not ready C++.

## Status meanings

- **Catalogued:** name, address, size and section appear in the original symbol table.
- **Bytes verified:** exported function bytes match the SHA-256-identified source ELF and their recorded hash. This does not verify behavior or recover source code.
- **Pseudocode exported:** decompiler produced text. It is unvalidated and excluded from the C++ build.
- **Upstream API match:** the pinned source's compiler-mangled encoded interface matches the original ELF entry. Actual source/body hashes are checked; unencoded original return types, layouts, binary behavior and native build success are not implied. Declaration-only matches are counted separately in coverage JSON.
- **Portable behavior partial:** a narrower wire behavior has a reconstructed C++ implementation and captured-frame tests. This does not verify the entire original function, its ABI or error paths.
- **Portable reconstruction ready:** current formatted C++ sources compiled, original mangled names matched, and ARM differential checks passed within the linked proof's stated domain. Original layouts, unresolved declaration spelling, untested inputs and hardware remain subject to the proof's limitations.
- **Compiled; declaration pending:** C++ compilation and symbol checks passed, but unresolved original interface declarations prevent portable readiness. Summary entries count distinct `(ELF SHA-256, mangled name)` identities; `compiled_declaration_pending_ranges` counts all matching original table rows. Every original range remains a separate table row and requires its own evidence.
- **Original function fully verified:** requires an explicit semantic/differential validation record. There are currently **zero** such functions.
- **Hardware verified:** deferred by the user because CS18AI/RM hardware is unavailable. Nothing is hardware-verified.

Function tables include defined functions and imported function symbols; the counts below refer only to defined, nonempty function entries. Addresses identify the original ARM ELF, not portable-library entry points.
Pseudocode coverage counts defined nonempty symbol entries, including aliases sharing an exported entry point. Unique entry counts and zero-size alias exports are recorded separately in coverage JSON; every symbol's byte range remains independently checked.
Data tables cover `STT_OBJECT` symbols, including embedded firmware and vtables. Structural mapping/file/section symbols remain in `recovered/*/all-symbols.json` and are excluded from the extraction workload.

## Current work scope

New **manual Core-owned binary reconstruction and extraction are deferred** and remain incomplete. Upstream Core source integration and prototype/mangling matching are active, using the earliest verified official public version. Source availability will be tracked separately from binary-behavior validation. Existing evidence is preserved. Presonus UC/DICE and mixer/surface work continues; a Core parameter type does not defer a Presonus-owned method. See [work-scope.json](tracking/work-scope.json).

## Coverage

| Binary | Defined functions | Bytes verified | Pseudocode exported | Upstream API matches (bodies) | Portable reconstructions ready | Compiled; declaration pending | Original functions fully verified | Tables |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| CS18AI surface 13840 | 7,843 | 7,843 | 6,818 | 1,566 (1,467 bodies) | 518 | 991 | 0 | [functions](tracking/client-functions.md), [data](tracking/client-data.md) |
| RM/RML mixer 13731 | 7,126 | 7,126 | 6,058 | 945 (890 bodies) | 545 | 1164 | 0 | [functions](tracking/server-functions.md), [data](tracking/server-data.md) |

## Partial portable C++ evidence

The six labeled original function signatures in each binary have **partial behavior references**, not full semantic verification:

| Original function area | Narrower reconstructed behavior | Evidence |
|---|---|---|
| `EventClass::write` | Event tag and route-field wire layout | `src/protocol.cpp`; captured event roundtrips |
| `Connection::writeEvent`, `Connection::readEvents` | TCP envelope, size bounds, incremental framing | `src/protocol.cpp`; 380 distinct captured TCP frames and malformed/split/coalesced cases |
| `MulticastConnection::writeEvent` | UDP envelope and reply-port field | `src/protocol.cpp`; 14,258 distinct captured UDP frames |
| `ParamValueEventClass::write`, `read` | Parameter-value path/index/value payload | `src/protocol.cpp`; 213 distinct captured PV payloads |

Tests also cover a portable TCP client/server loopback exchange. They do not validate mixer state, subscriptions, authentication, DICE hardware I/O, firmware programming, audio routing or original function equivalence.

Integrated CTest evidence must match current source and log hashes before partial wire-behavior labels are shown. Existing UC byte-export audit: [audit.json](recovered/audit.json). Current source identity, scope manifests, aliases and per-symbol statuses: [coverage.json](tracking/coverage.json).

Current integrated build evidence and source hashes are in [integration.json](validation/integration.json), with the matching [Linux build seal](validation/integration-linux.json). Embedded DICE callbacks have a separate [symbol tracker](validation/dice-image/EMBEDDED-SYMBOLS.md) and [image report](validation/dice-image/REPORT.md); registration labels and independent wrappers do not count as recovered host ELF symbols. [Source-lineage research](validation/source-lineage/README.md) records candidate declarations and version/licensing limitations without promoting them to original headers.

## Subsystem queue

Grouping below is based on symbol names and is a navigation aid, not a proven module/dependency boundary. DICE includes explicit `Presonus::DICE`, `Dice*`, TCAT and Shelby names. Embedded processor firmware and FPGA blobs are data, not automatically disassembled host functions.

| Binary role | Subsystem | Defined functions | Bytes verified | Pseudocode exported |
|---|---|---:|---:|---:|

Actual pinned CCL source is built and publicly linked on Linux. Its relocated installed package passed a consumer check; all 248 SDK headers matched the clean upstream source. This does not promote Core ELF symbols to recovered readiness. See [source-provider proof](validation/core-upstream/root-provider-validation.json).

| client | AVB | 66 | 66 | 66 |
| client | C++ / compiler runtime | 105 | 105 | 105 |
| client | Core | 2,326 | 2,326 | 1,301 |
| client | DICE / TCAT / Shelby | 90 | 90 | 90 |
| client | DSP | 129 | 129 | 129 |
| client | Mixer | 174 | 174 | 174 |
| client | Other C / application | 956 | 956 | 956 |
| client | Other Presonus | 850 | 850 | 850 |
| client | Panel | 560 | 560 | 560 |
| client | Surface | 1,056 | 1,056 | 1,056 |
| client | UC | 1,511 | 1,511 | 1,511 |
| client | UUX | 14 | 14 | 14 |
| client | XMen | 6 | 6 | 6 |
| server | AVB | 80 | 80 | 80 |
| server | C++ / compiler runtime | 102 | 102 | 102 |
| server | Core | 1,407 | 1,407 | 339 |
| server | DICE / TCAT / Shelby | 26 | 26 | 26 |
| server | DSP | 308 | 308 | 308 |
| server | Mixer | 1,052 | 1,052 | 1,052 |
| server | NOAA | 167 | 167 | 167 |
| server | Other C / application | 572 | 572 | 572 |
| server | Other Presonus | 598 | 598 | 598 |
| server | Panel | 1,220 | 1,220 | 1,220 |
| server | UC | 1,574 | 1,574 | 1,574 |
| server | UUX | 14 | 14 | 14 |
| server | XMen | 6 | 6 | 6 |

## Updating the tracker

Regenerate with `tools/generate_symbol_tracking.py --inputs <directory-containing-surface-13840.elf-and-mixer-13731.elf>` after each extraction phase. This checks source identities and each existing byte export again. Keep semantic/hardware verification false until concrete validation evidence is added; do not promote pseudocode exports to verified source.

The generator merges `recovered`, `recovered-dice` and `recovered-all`, verifies source identity and available byte exports, and uses recorded decompilation results. Function aliases sharing an entry address share a pseudocode export; every symbol's own byte range is checked separately. `validation/registry-sqlite/ACTIVE.json` selects the authoritative SQLite registry, which grants portable readiness only when its proof file and current source hashes match, compiled mangled names were checked, and ARM differential tests passed. Retired JSON ledgers are historical snapshots. Readiness applies only to the recorded buffer/semantic domain; it does not establish original ARM object-layout or hardware compatibility. No original implementation is promoted to fully verified merely because a portable reconstruction is ready.

Stopped or unsupported reconstruction attempts are recorded in [the recovery gap log](validation/RECOVERY-GAPS.md), with exact original identities and remaining work. A tool stop does not prove a function unrecoverable.

Client/server component targets `presonus::cs18_components` and `presonus::rm_components` share production OBJECT units; `presonus::uc` remains the compatibility archive. See [source partitions](cmake/ProductionSourceGroups.cmake) and [production audit](candidates/common-build/validation/production-audit-01/validation.json). These component archives do not establish completed application startup.
