# UC recovery from PreSonus CS18AI and RM/RML firmware

Extraction progress: [symbol and verification tracker](SYMBOLS.md), with complete
function/data catalogues and separate byte, pseudocode and behavior statuses.

The current integrated milestone contains 577 per-ELF portable-ready entries
(309 distinct original mangled methods), with 296 declaration-pending entries
kept separate. The canonical Linux Release build passes 98 CTest suites; installed
archives contain all 309 ready mangles, with 71 application and 248 upstream CCL
public headers verified separately.
Further macOS builds/tests are skipped unless explicitly requested. Existing
macOS evidence is retained as historical validation; local work mirrors sources,
logs and hashes from VM101.
See `validation/integration.json` and `validation/integration-linux.json`.
The active UC adapters use actual CCL sockets, locks, buffers, hash maps and
singleton support; AVB collections use actual CCL linked lists. Original
application methods retain their `Presonus::UC` and `Presonus::AVB` scopes.
The 262 affected UC entries were freshly compiled and resealed; AVB replay
passed 961,994 retained original-ARM fixture cases. `Connection::readEvents`
and AVB pointer-return lookups remain declaration-pending. Source-built CCL
integration does not claim original Core ELF behavior or ARM object layouts.
The packet/response phase adds original DICE constructor/command methods and
distinct DICE/NOAA wait interfaces over one shared wait algorithm. The shared
UC dispatcher and CCL-backed panel ControlGroup are integrated; unresolved
void/pointer return declarations remain separate from numeric ready entries.

Client/server recovery uses a common codebase. The similarity audit found 2,709
shared Presonus names (62.12% client / 56.17% server); 2,183 have corroborating
byte or normalized-pattern matches. These are reuse candidates, not equivalence
proofs. See
`validation/client-server-similarity/20261027T032232.775911Z/REPORT.md` and its
build architecture proposal. Shared implementations are reconstructed once;
role-specific behavior stays explicit. Original `main` and concrete application
startup closures remain unreconstructed; manager control flow has a bounded
source port. Component build targets must not be advertised as
complete replacement applications. Stopped attempts and unsupported parts are
recorded in [the recovery gap log](validation/RECOVERY-GAPS.md).

The active CMake build now compiles each production CPP once into common,
CS18 or RM OBJECT partitions (currently60/18/6 units). It produces the existing
`presonus_uc` archive and real `presonus_cs18_components` /
`presonus_rm_components` archives. Installed targets are `presonus::uc`,
`presonus::cs18_components` and `presonus::rm_components`. All98 current test
suites passed; root/installed archives contain309/296/281
required facade/client/server mangles. Both relocated role consumers passed.
Current audit:
`validation/role-build-audit/runs/20261027T135241.287055Z/validation.json`.
The original migration proof remains at
`candidates/common-build/validation/production-audit-01/validation.json`.
The real CCL provider continues to build from pinned source; no copied permanent
SDK archive or role-specific source duplication was introduced.
Clang DSP builds require `-ffp-model=strict` to preserve signaling-NaN comparisons
under optimization. This does not establish original ARM ABI or hardware fidelity.

Shared `Presonus::UARTMessageHandler` now uses actual CCL TypedObject and
CString128 services. Its active 25,896-case replay verifies the twenty virtual
slots, callback argument order/aliases, signed encoder values, full diagnostic
branch and actual indirect D1/D0 destruction/deallocation. All eighteen original
dispatch opcodes and the unused handleVersion slot are retained. Four lifecycle
entries are ready; thirty-six ordinary declarations remain pending. Native D2
is support-only, not an invented original entry; static storage/guard layout,
opaque touchscreen representation and concurrency remain explicit limits.
Current checkpoint: `temp/uc-recovery/checkpoints/2026-10-27-control-file-services.md`
(repository-relative).

Shared `Presonus::Panel::Control` now supplies its original 28 methods per role,
using actual CCL ParamObserverBase/Parameter/vector services and the recovered
ParamEditHandler. Fourteen lifecycle entries are ready; forty-two ordinary
declarations remain pending. Fresh active replay passes 8,914 ordinary and
11,182 explicit null-seam cases, actual virtual D1/D0/deallocation and populated
edit-handler-before-timer composition. Original module initialization and dirty
list data remain outside the preinitialized-state domain.

Shared `Presonus::UC::{FileRequestHandler,FileReader,FileWriter,FileListReader,
FileListWriter}` supplies 27 methods per role from one common CPP. Thirty-four
lifecycle entries are ready and twenty ordinary declarations pending after
2,796 retained cases in each fresh Release/sanitizer mode. Stream ownership,
virtual deletion and application RTTI are checked. Actual CCL Attributes uses
portable composition in list helpers; its private field layout/inheritance is
not claimed as original ARM ABI. Existing file payload headers are unchanged.

Server-only `Presonus::NOAA::SysexPacket` payload construction and `TCardSPI`
packet/receiver methods now use actual CCL clock, buffer, vector and lock
services plus the original-namespace NOAA logger. One C1 entry is ready and
four ordinary declarations remain pending after 6,369 retained cases and fresh
canonical-object/native playback. The header migration freshly replayed all
five prior Dice lifecycle-ready and ten pending dependencies. SPI uses a
256-byte span and 32-bit count. Its independent borrowed state is distinct from
the original hardware constructor, Singleton/PinStateObserver inheritance and
device lifetime, which remain open. Bounds/storage-mutation handling and
inactive packet byte 255 initialization are explicit source adaptations.

Shared `Presonus::Panel::ParamEditHandler` now uses actual CCL vectors,
Parameter callbacks and the source clock gateway. Six C1/C2/D1 lifecycle entries
are ready; eight ordinary declarations remain pending. Fresh active replay
passes 2,300 ordinary-allocation cases and 3,464 cases under a separate explicit
GNU `-fcheck-new`/wrapped-null seam. Production allocation exceptions/unwind and
callback mutation of the helper containers remain excluded. Native D2 is a
support alias, not an invented original entry. The final formatter reordered
includes for the active filename; fresh proof binds those exact active bytes.

Shared `Presonus::ResourceLibrary` registration, lookup and ownership now use
actual CCL Vector/CStringBuffer types. Active Release and sanitizer replays each
pass 352 retained cases, including direct constructor/destructor variants,
native alias observations, capacity growth, lookup and actual deallocation.
Eight lifecycle entries are ready; eight ordinary declarations remain pending.
FirmwareBundle metadata/zlib storage remains a partial source port. Its three
stream methods now pass 238 retained ARM/native cases per Release/sanitizer mode;
six per-ELF ordinary declarations remain pending. Modern zlib 1.3 with a
112-byte native z_stream replaces the original 1.2.11/56-byte interface, retaining
windowBits 31. This does not verify original zlib bodies or ARM layout. The
destructor preserves direct global deletion and does not invent stream cleanup.
Resource registration checkpoint: `temp/uc-recovery/checkpoints/2026-10-27-resource-library.md`
(repository-relative).

Shared `Presonus::DelayTimer` now uses the actual CCL monotonic clock gateway.
Its 17,512-case active replay supports eight lifecycle-ready entries and sixteen
declaration-pending methods. Eighteen NaN sign/payload differences are retained
explicitly and compared only by quiet-NaN classification; production does not
normalize them. The zero-size signed-division helper stays a documented external
compiler contract, not a recovered body. Constructor conversion limits are
explicit.

CS18 `Dice3Uart` now uses actual CCL Singleton and UARTComm bases for post,
idleRead, onIdle and release. All four declarations remain pending. Its 1,405
retained fixtures and six separate source-port bounds cases pass; all six prior
header-dependent pending entries were freshly replayed and preserved. Original
default constructors and destructors now have five bounded portable-ready
C1/C2/D0/D1/D2 entries, supported by 3,006 lifecycle cases and real CCL provider
smoke tests. Native aliases are recorded independently of original byte ranges.
The two original ARM -4 adjusting thunks remain unready; native -8 thunks are
distinct symbols. Default-owned state and borrowed seeded support are explicit;
the derived close gate differs from the inherited UART descriptor. Provider
smoke tests stay unwrapped; replay diagnostics are preserved separately.
Dice/timer checkpoint: `temp/uc-recovery/checkpoints/2026-10-27-dice-timer.md`
(repository-relative).

Shared `Presonus::Panel::SimulateComm` now provides the original duplex panel
transport using real inherited CCL locks. Its active 11,120-case replay includes
full-message framing, native constructor/destructor aliases and actual virtual
destruction/deallocation. Ten lifecycle entries are ready; ten ordinary
declarations remain pending. Static storage declarations, concurrent access and
overflow/throwing domains retain explicit limits.

The CS18-only `Presonus::Surface::SurfaceApplication::readSerialFromDisk` source
uses actual CCL FileStream and the recovered SimpleReader; 755 retained cases
pass each active Release/sanitizer mode. Its ordinary declaration, partial class
storage/hierarchy and modern libc scanner remain explicit source-port limits;
the method is pending and does not establish complete application startup.
The later identity batch adds original `getAlternateMac` and `getNetworkSerial`
with 22,602 retained ARM/native comparisons in each Release/sanitizer mode,
forward replaying all 755 serial cases. Actual CCL formatting/substrings and
libc preserve decimal-width/truncation quirks and debug arguments. The two new
64-bit return declarations remain pending, alongside the refreshed serial
declaration; no network/device I/O or original class-layout claim is made.
Simulate/serial checkpoint: `temp/uc-recovery/checkpoints/2026-10-27-simulate-serial.md`
(repository-relative).

Shared `Presonus::FileCleanup` now uses actual CCL FileName, vectors, iterators
and filesystem operations. Six lifecycle entries are ready; six ordinary-return
declarations remain pending. Active Release and sanitizer replays each pass 72
retained original cases over uniquely owned project-temp trees, including
deletion failures, continued work, hidden/subdirectory skips and actual vector
deallocation. No recursive cleanup of unrelated files occurs in verification.
FileCleanup checkpoint: `temp/uc-recovery/checkpoints/2026-10-27-file-cleanup.md`
(repository-relative).

The ProtocolComm/UARTComm batch adds real shared panel framing and POSIX UART
transport bound to actual CCL locks and clocks. The active replay matches 39,994
codec/base and 4,810 UART original-ARM fixture cases. Sixteen lifecycle entries
are ready; 26 ordinary/C declarations remain pending. Malformed receive-prefix
and failed termios-query behavior have explicit source-port limits; no UART
device was opened during validation. Current compact checkpoint:
`temp/uc-recovery/checkpoints/2026-10-27-protocol-uart.md` (repository-relative).

`Presonus::Panel::DigitalPotControl` is integrated against actual CCL parameters,
including original compiler-helper float conversion behavior. UC dispatcher
registration now uses actual CCL IDSet/map/list state, with original namespace
and mangling checks. The client UART assembly method and its real CCL
buffer/vector/lock adapters are integrated once. Its793 original ARM/native
traces preserve the complete67-byte pre-mutex span, receiver snapshot and clock
ordering; the return declaration remains pending. The explicit rejection of the
first mutex-overlap write and other unsupported states is logged as a source-port
adaptation. Actual UART I/O/lifecycle remains separate work; the recovered packet
log implementation is now connected through the independent CclPacketLogSink.
UART registration/removal is now integrated over the same CCL lock/vector,
including duplicate/null entries and first-match removal.2438 original ARM
registration cases passed, and the793 parser traces were replayed after the
header extension. All three original method declarations remain pending.
The current proof is `validation/dice-uart-registration-active/logger-header-01/validation.json`;
the earlier assembly-only proof remains immutable historical evidence.

Shared UC variable-data codecs now use actual CCL Buffer storage. Their60024
original ARM/native cases cover partial failures, metadata byte order, cursor and
payload mutations, borrowed/owned storage and clone behavior. Eight numeric-result
methods contribute16 per-ELF ready entries; the clone's two original pointer
return declarations remain pending. Current proof: `validation/uc-data-codecs/`.
The original18-ready candidate classification is superseded by its READINESS-NOTE.

Application managers share one engine with original `Presonus::OmapApplicationManager`
and `Presonus::Mixer::MixerManager` wrappers, actual CCL Singleton/string/file
environment services, the real SimpleReader environment adapter and explicit
unresolved concrete application endpoints.
All22 manager symbol entries are compiled. Eight C1/C2/D1/D0 lifecycle entries are
portable-ready after separate native ABI-variant and real deallocation checks;
fourteen ordinary-method declarations remain pending.4346 cases
passed per Release/sanitizer replay, retaining startup selection and role-specific
cleanup behavior. Concrete application constructors/lifecycle/release and full
original class declarations/layouts remain unrecovered; no complete executable is
claimed. Current proof:
`candidates/application-managers/validation/seals/active-20261027T053608.588250Z/validation.json`.
The lifecycle supplement is
`candidates/application-managers/lifecycle-variant/validation/20261027T054513.728418Z/`.

DICE/NOAA packet logging shares one formatter and retains separate original
namespaces, local statics and command mappings.2365 original log cases per role
and256 NOAA command cases pass; actual CCL clocks/debug and UART callback-to-sink
integration are separately checked. The three new log/getter declarations remain
pending. The old DICE getter was also reclassified pending because its static
pointer return declaration is unproven; its compiled code and behavior proof are
retained. New proofs: `validation/dice-packet-log-active/active-01/`,
`validation/dice-packet-log-dependencies/runs/20261027T055906.058579Z/` and
`validation/dice-uart-registration-active/logger-header-01/`.

Readiness admission now enforces disjoint ready/pending identities. Guarded
demotions require the previous proof hash, a reason and a fresh pending record;
validated promotions remove the old pending entry. Both old ledgers and status
transition journals are preserved in `validation/history/`. Six project-temp
snapshot tests verified these transitions without modifying the real ledgers.

Shared `Presonus::Panel::AlertManager` now uses actual CCL Singleton services.
Its2304 ARM/native cases verify argument forwarding, pointer identity, constructor
aliases, actual loaded-vtable D1/D0 calls and real deallocation. Eight lifecycle
entries are ready; six ordinary declarations remain pending. IAlertDelegate stays
opaque, with its two observed calls represented by an independent typed bridge.
Current proofs: `validation/panel-alert-manager/`.

`Presonus::SimpleReader` now provides actual CCL stream/file parsing and the
manager's device-name reader. One CPP covers nine shared entries plus the server's
extra position setter.4810 original ARM/native cases per Release/sanitizer mode
and the manager-reader binding smoke pass. Four constructor entries are ready;
fifteen ordinary declarations remain pending. Original parser quirks and read/write
file-open mode are retained. Exact-type assignment copies all64 bytes, verified
against original memcpy64 and native stores; indeterminate tail values remain
outside the proof. Current seal:
`candidates/application-reader/validation/seals/active-20261027T065904.279227Z/`.

Original-named C++ reconstruction has started in `src/`. The first
`Presonus::UC::DicePacketQueue::{fromMIDI,toMIDI}` implementations preserve the
original namespace, class, parameter types and compiled mangled names. They
passed 908 original-ARM encode fixtures, 1,272 decode fixtures and 200 valid
length roundtrips on Linux and macOS. Their portable `Packet` storage does not
reproduce the original ARM object/vtable layout. See
`validation/dice-packet/ready-functions.fragment.json` for current sealed
proof references, tested memory domains and source hashes. Further validated
bundles cover DICE command helpers, panel controls, DSP numeric operations and
UC buffer and event payload operations. The current per-ELF readiness ledger is
`validation/ready-functions.json`; compiled functions with unresolved original
declarations are separate in `validation/compiled-functions.json`.
Remaining functions stay pending until their own evidence supports
readiness; pseudocode export alone does not make them complete.

The integrated EventQueue update methods use caller-owned live items and explicit
portable synchronization/typed-view callbacks. Incoming and queued typed storage
must be disjoint, strings NUL-bounded and nonoverlapping, and lock/unlock callbacks
must succeed without throwing. The port preserves first-match coalescing and
original stale-field behavior; it does not recover Core locks, allocation or queue
construction. AVB packet transforms preserve unmasked nibble decoding and forward
overlap where proved; SPI lengths and buffer padding must satisfy the linked
bounded proof, since the original lacks a lower-length guard. See each package's
validation README and per-symbol domain before using these original interfaces.

This folder contains **recovery evidence and a tested, partial portable C++17
implementation**. It is not a complete replacement for the original UC client
or server library. A successful decompiler export does not mean the output is
correct C++, preserves the ABI, or works on hardware.

## Verified inputs

Repository: `DjFix/Presonus-RM-RML-Analysis`, commit
`87e9e92d96d69271dc9971c314d5b1a9e1bfa9c3` on the analysis VM.
The completed local checkout is at `73e6bfde70e154972c57fdeb2974b1ef4cf709c7`;
recovery source identity is bound to the ELF hashes below.
Analysis machine: VM101 (`rs@192.168.50.238`), checkout
`/home/rs/projects/opencs/ai-line-analysis`.

The newest **unstripped versions present in this checkout** are:

| Role | Version | Rootfs-relative ELF | UC symbol entries | UC function entries |
|---|---:|---|---:|---:|
| CS18AI client | 13840 | `CS18_v13840/home/root/surface` | 2,568 | 1,514 |
| RM/RML server | 13731 | `RML16AI_Rack_13731/home/root/mixer` | 2,659 | 1,587 |

SHA-256:

```text
304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0  surface 13840
9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07  mixer 13731
```

The RM16, RML16 and RML32 13731 mixer copies have identical hashes.
`recovered/inventory.json` inventories all rootfs application binaries.
The newer CS18AI 16403/16613, SL1642AI/SL3242AI 16191 and RML16/RML32 16489
applications are UPX-packed. Unpacking restores dynamic ARM ELFs, but these
copies are **stripped**; none supersedes the inputs above for symbol recovery.
UPX 5.2.1 reported bad `b_info` / recovery warnings for those files. They are
comparison artifacts, not assumed byte-perfect original ELF reconstructions.

Both selected ELFs are ARM32 EABI4, use `/lib/ld-linux.so.3`, and have full
symbol tables. DWARF is present, but the inspected compilation units describe
GCC/glibc runtime code, not recovered UC application types. Ordinary Itanium
function names generally encode parameter types but not return types or class
member layouts. Names alone cannot recreate the original headers.

## Contents

- `include/presonus/uc/protocol.hpp`, `src/protocol.cpp`: buildable independent
  wire API; raw events, route fields, TCP frames, UDP envelopes, keepalives and
  parameter values.
- `include/presonus/uc/network.hpp`, `src/network.cpp`: POSIX IPv4 TCP client,
  listener and connection with deadlines, incremental receive, full sends and
  RAII ownership. The default listener binds only to loopback.
- `include/presonus/uc/abi32.hpp`: observed original ARM32 event data
  offsets, with static assertions; binary-inspection structures only.
- Original-named implementations live directly under `src/`, including
  `src/Presonus/UC/`, `src/Presonus/DICE/`, `src/core_uc/`,
  `src/surface_panel/` and `src/mixer_dsp/`. Public include paths omit
  `_recovered`; filesystem organization does not alter original C++ scopes.
- `validation/formatting.json`: clang-format version, configuration and
  checked source hashes. Format before validation and sealing source hashes.
- `include/presonus/uc/events.hpp` and `transport_events.hpp`: original-named
  common event, parameter-value/string, UDP mapping, MIDI and extension-query
  payload methods. Read/write boundaries, partial failures and arbitrary byte
  values are checked against both original ARM ELFs. Storage remains portable;
  original inheritance and virtual event dispatch remain unresolved.
- `include/presonus/uc/event_factory.hpp`: seven original-named factory
  hash/create/read/write methods, tested against both ELFs. An explicit
  independent registry/callback interface replaces original container and
  allocation storage; original constructor registrations, pooled allocation,
  class/vtable ABI and destructor variants remain pending. See
  `validation/uc-factory/DEPENDENCIES.md` for the exact boundary.
- `discovery_events.hpp`, `primitive_dispatch.hpp` and
  `typed_factory_codec.hpp` under `include/presonus/uc/`: original discovery
  payload methods and six original typed dispatch pairs, with independent
  portable factory adapters. Returned items require explicit binding before
  writing/cloning, and unbinding before deletion; composed tests cover this
  contract. See `validation/uc-registration/COVERAGE.md` for all 35 original
  registrations, including unresolved construction/registration dependencies.
- `include/presonus/mixer_state/MixerState.hpp`: original channel predicates,
  GEQ counts with virtual override dispatch, and cascade state. Original link
  pointee types and return declaration spelling remain explicitly unresolved;
  see `validation/mixer-state/SYMBOLS.md` and its bounded proof.
- `include/presonus/uc/meter_events.hpp`, `parameter_events.hpp`: original
  8/16-bit meter and six parameter payload classes plus their typed dispatch.
  Count limits, capped-copy/failed-skip mutations, raw numeric bits and partial
  strings are tested. Unsafe oversized original writer accesses remain outside
  the stated port domains, not silently clamped into different behavior.
- `include/presonus/dice/codec.hpp`: original global unpack helpers and
  output-only pack ports. Packer return declarations remain pending. Original
  noncanonical-byte behavior is preserved; no volatile/MMIO order is claimed.
- `include/presonus/dice/manager.hpp`: original routing profile and monitor
  selection methods with a documented independent route endpoint contract.
  Ordered calls, endpoint reloading, arithmetic wraparound and ignored endpoint
  errors are validated; UART/wait implementation is separate.
- `include/presonus/embedded_dice/mix.hpp`, `src/embedded_dice/mix.cpp`:
  independent `presonus::embedded_dice` wrappers for five raw-image mixer
  callbacks. Their original C++ symbols are unknown. Exact modeled I/O traces
  are tested offline; see `validation/dice-image/EMBEDDED-SYMBOLS.md` for the
  separate embedded-image tracker and its limitations.
- `recovered/{client,server}/symbols.hpp`: compilable per-role catalogues of
  original mangled names, demangled parameter signatures, addresses and sizes.
  These are not callable wrappers or complete class declarations.
- `recovered/{client,server}/symbols.json`, `all-symbols.json`: UC and complete
  symbol inventories. UC selection includes external application functions
  whose parameter types mention `Presonus::UC`; it is not a proven closed
  dependency set.
- `recovered/{client,server}/machine-code/`: original bytes for selected function
  symbols, indexed by virtual address. Files may include compiler literal pools.
- `recovered/{client,server}/uc.arm.asm`, `calls.json`: ARM disassembly and direct
  branch/call evidence. Indirect dispatch and external Core dependencies still
  require analysis.
- `recovered/{client,server}/pseudocode/*.cpp.txt`: explicitly **unvalidated**
  angr output; excluded from the build. Expect missing/incorrect types, control
  flow, indirect calls and stack variables. Some observed output disagrees with
  raw ARM instructions, so manual assembly review is mandatory before porting.
- `recovered/{client,server}/decompilation.json`: per-function export status and
  failures; `decompiler.log` records tool diagnostics and final completion.
- `tests/vectors/`: captured UC transport frames and capture provenance.
- `tools/`: repeatable extraction/decompilation/vector generators and a Python
  environment lock file. Original firmware, downloaded tools and virtualenv are
  excluded by `.gitignore`.

## Build and validate

On a machine with CMake and a C++17 compiler:

```sh
cmake -S uc-library -B uc-library/build -DBUILD_TESTING=ON
cmake --build uc-library/build
ctest --test-dir uc-library/build --output-on-failure
uc-library/build/uc_loopback
```

The VM also supports a direct build from inside `uc-library`:

```sh
mkdir -p build
g++ -std=c++17 -O2 -Wall -Wextra -Wpedantic -pthread -Iinclude src/protocol.cpp src/network.cpp tests/uc_tests.cpp -o build/uc_tests
build/uc_tests tests/vectors/capture-vectors.txt
```

The tests cover 14,258 distinct captured UDP frames, 380 distinct captured TCP
frames, 213 distinct parameter-value payloads, split/coalesced frames, malformed
headers/lengths, decoder reset, maximum lengths, and a real TCP loopback exchange
between the reconstructed client and server. Byte-for-byte frame roundtrips
validate framing/preservation; they do not validate semantic handling of every
event. The loopback example is an echo, not a mixer emulator.

## Reproduce recovery on VM101

Run from the repository root, after creating `uc-library/.venv` with Python 3.12
and installing `tools/requirements-lock.txt`:

```sh
uc-library/.venv/bin/python uc-library/tools/extract_uc.py . --output uc-library/recovered
uc-library/.venv/bin/python uc-library/tools/decompile_uc.py . client --recovery uc-library/recovered-all --reuse-from uc-library/recovered --reuse-from uc-library/recovered-dice --priority application --batch-size 250 --max-rss-mb 2048 --min-available-mb 1024 --quarantine-untrusted --stop-file temp/uc-recovery/STOP
uc-library/.venv/bin/python uc-library/tools/decompile_uc.py . server --recovery uc-library/recovered-all --reuse-from uc-library/recovered --reuse-from uc-library/recovered-dice --priority application --batch-size 250 --max-rss-mb 2048 --min-available-mb 1024 --quarantine-untrusted --stop-file temp/uc-recovery/STOP
uc-library/.venv/bin/python uc-library/tools/capture_vectors.py 'captures/session Start, meters, a bit control.pcapng' uc-library/tests/vectors
```

Run heavy decompilation sequentially. Inspect live processes before resuming;
an observation timeout is not proof of termination. Trusted existing exports
are reused only with source identity and recorded output hashes. Unrecorded
outputs are quarantined under project `temp/`, not treated as completed work.
Preserve prior evidence when inputs or tools change. Each bounded process writes
`run-state.json`; exit zero can mean a partial batch, so inspect its state,
reason, pending count and failures. Create the stop file to request a checkpoint
between functions. See `validation/extraction-verification/CONTINUATION.md`.
The full scope includes the statically linked framework and application/hardware
functions, but exporting pseudocode does not port those functions to C++.

The capture parser supports pcapng Ethernet/IPv4, VLANs and contiguous TCP
payloads with overlap removal. It excludes fragmented IP, does not handle TCP
sequence-number rollover or multiple connections reusing the same four-tuple,
and reports gaps/conflicting duplicate segments rather than silently treating
such input as a verified trace. This capture had no reported gaps/conflicts.

The original `scripts/extract-symbol.sh` incorrectly uses the symbol-table row
number as a byte offset. This recovery computes file offsets as
`section.sh_offset + symbol.st_value - section.sh_addr`, validates section bounds
and records a hash for every extracted function. It does not mount filesystems,
execute the ARM application, flash devices or alter mixer hardware.

## Verified protocol and evidence addresses

Addresses refer to mixer 13731; original symbols are retained in the catalogues.

| Behavior | Original function/address | Validation |
|---|---|---|
| Event tag BE16 + two LE16 route fields | `EventClass::write`, `0x000dbdec` | ARM + captured frames |
| TCP `UC 00 01` + LE16 event length | `Connection::writeEvent`, `0x000ef604`; `readEvents`, `0x000ee2f8` | ARM + 380 captured frames |
| UDP `UC 00 01` + LE16 reply port | `MulticastConnection::writeEvent`, `0x000f15e8` | ARM + 14,258 captured frames |
| Path/NUL, LE16 index, binary32 bits | `ParamValueEventClass::write`, `0x000e3fdc`; `read`, `0x000e63a8` | ARM + 213 payloads |
| Keepalive has no payload | `PrimitiveEventClassNoMembers<KeepAliveEvent,19265>::write`, `0x000dcb80` | ARM + captured KA frames |

`47809` was the captured UDP discovery destination and `53000` the advertised
reply port. Neither is silently used as a TCP server default.

## Work still required for a full replacement

1. Recover and port all event payload codecs, including discovery descriptors,
   JSON/binary/compressed messages, meters, file transfer and MIDI.
2. Recover registration, routing-ID allocation, authentication/permission policy,
   keepalive scheduling, subscriptions and the UC model/metadata synchronization
   state machines from `NetworkManager`, `ConnectionHandler`,
   `ClientImplementation`, `ServerImplementation`, `ElementParser` and related
   classes. Raw-event preservation does not implement those behaviors.
3. Replace or port required Core containers, memory pools, threading, sockets,
   messaging and parameter-tree facilities, preserving their observable behavior.
4. Recover CS18-specific integration and RM hardware adapters separately from UC.
   Audio/AVB/DICE/front-panel control is outside the current portable transport.
5. Compare the latest stripped builds with the unstripped baselines, then verify
   with independent real-device client/server sessions and concrete bug cases.

No physical CS18/RM session or full interoperability test has been performed.
Do not replace the working control application with this partial library yet.

Manual Core-owned binary reconstruction and extraction remain deferred;
existing evidence is retained as incomplete. The user now prefers the earliest
official public Core source release, pinned as a Git submodule in `third_party`,
with matching APIs supplied from upstream rather than manually recovered.
The official `ccl-5.0.0` commit is pinned on both checkouts; the frozen matcher
records 1,566 client and 945 server exact encoded-interface matches, with 2,357
body-backed ELF records and 154 declaration/synthesis-only records. The tracker checks
all 413 source-file Git blob/SHA-256 identities and direct/generic body extents.
The active Linux build now compiles the pinned upstream `corelib` and its
allocator from source and publicly links `PresonusCore::Provider`. All 39
pre-binding application suites passed. The installed package passed relocation,
all 248 CCL headers matched upstream, and an installed consumer exercised real
Buffer, Lock, NumericParam, recovered DbTable and application RTTI. See
`validation/core-upstream/root-provider-validation.json`. This does not prove
original ARM ABI, binary behavior or every template instantiation's native linkage.
Source-based behavior is preferred for differences, which must be recorded as
intentional source-port adaptations, not binary/ARM ABI equivalence. Earliest
Residual API adaptation and per-method linkage are tracked separately. The active work scope is recorded
in `tracking/work-scope.json`, and per-function tables label Core owner/alias
deferrals. Presonus methods that merely refer to Core types remain eligible.
The bounded extractor excludes deferred starts and byte regions from CFG as
well as from new per-function attempts. A completed eligible scope does not
mean the original full workload is complete.

Installation includes only the explicitly integrated public headers, excluding
unfinished work. `tools/audit_install.py` verifies installed header hashes and
the original ready mangles in the archive. Current Linux results are preserved
under `evidence/recovery/2026-10-27/common-build-root/`; previous macOS results remain
historical evidence. These checks do not establish ARM ABI or hardware compatibility.

Tool references: [UPX releases](https://github.com/upx/upx/releases),
[angr CFG recovery](https://api.angr.io/en/latest/analyses/cfg.html),
[angr decompiler](https://api.angr.io/en/latest/api/angr.analyses.decompiler.html).
