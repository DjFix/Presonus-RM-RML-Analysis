# NIMH startup, RTOS/SDK and command paths — phase 01

Completed 2026-10-28 MSK; evidence remains in the phase's 2026-10-27 UTC bucket.
Analysis and execution were offline on VM101. No devices were accessed.

## Result and boundaries

The NIMH image uses an **eCos Cortex-M runtime and TCAT SDK**, with customer
control code and FPGA-backed peripheral access. Following the user's architecture
clarification, STM32 + FPGA implements the logical DICE role. The analysis uses
architectural patterns in the local TCAT manuals. No CS18AI/RM firmware address,
function or binary mapping is used as validation in this phase.

The first host packet paths are reconstructed through the STM32 dispatcher and
explicit SDK boundaries: rate/link, AVB clock source, routing and selected AVB
stream controls. The rate request's deferred consumer is also replayed in a
bounded inactive-link state. An independent NIMH mixer callback is replayed down
to its actual external register write. These are separate proofs; they do not
establish complete clock reconfiguration, FPGA logic or audio equivalence.

| Offline proof | Cases | Actual original code executed | Explicit boundaries |
| --- | ---: | --- | --- |
| Reset/memory setup | 1 trace | SRAM vectors, VTOR, data copy, BSS clear | Early hardware initializer and SVC trampoline hooked; stops before later initialization |
| Host packet construction | 27 | Mixer ARM `TCard::setClockSource` and `sendSampleRate` | libc operations modelled; time/log/ACK and virtual transport modelled |
| STM32 command loop | 222 | Dispatch, field decoding, acknowledgements and small state helpers | Completed RX packet injected; readiness, synchronization, selected SDK device calls and TX enqueue modelled |
| Deferred rate consumer | 12 | Request-to-active-state copy and request clearing | Inactive link-state branch; transition helper modelled; no scheduler/topology completion |
| NIMH mixer register callback | 216 | Thumb instructions and index/error paths | Register page is emulated RAM; assertion diagnostic returns normally |

Full domains, inputs, calls and output traces: [startup](../../../../evidence/mixer-13731/nimh-stm32-dice/jobs/command-map-01/startup-replay.json),
[host](../../../../evidence/mixer-13731/nimh-stm32-dice/jobs/command-map-01/host-replay.json), [STM32/worker](../../../../evidence/mixer-13731/nimh-stm32-dice/jobs/command-map-01/stm-replay.json),
[register writes](../../../../evidence/mixer-13731/nimh-stm32-dice/jobs/command-map-01/fpga-register-replay.json). Earlier failed harness runs are
retained in their numbered logs. No production C++ was changed and no recovered
function was admitted to readiness.

## Input identity

- Host: mixer 13731, original ELF SHA-256
  `9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07`.
- Embedded original symbol: `_ZL13nimh_arm_code` (`nimh_arm_code`), `.rodata`,
  ELF address `0x002608d7`, ELF file offset `0x002588d7`, 216,908 bytes.
- Image SHA-256:
  `b0979352e18a1093051fc6118a47694773cb9240e88087eca03aaa2ffe0f5e17`.
- Board identification and FPGA resource selection reuse the hash-bound
  [linked FPGA analysis](codex://threads/01a17e03-d528-7102-af84-2a680a143ee3)
  and project `validation/fpga-identification/assessment.json`: NIMH is a
  variant-specific bundle, not proof of several simultaneous FPGA devices.

Original host identities and byte hashes are retained in the proof/index files.
Names assigned to stripped embedded routines below are **analysis labels**;
they are not recovered original C/C++ symbols or declarations.

## Startup and memory layout

The first eight bytes contain SP `0x20010000` and reset pointer `0x08004511`.
The following words are not a full Cortex-M flash vector table. At `0x08000010`
there is a stack-load/branch trampoline to the reset implementation.

| Region or operation | Observed range/address | Evidence |
| --- | --- | --- |
| Raw image mapped for analysis | `0x08000000..0x08034f4c` | Reset and literal addresses; blob length |
| Reset implementation, eCos `hal_reset_vsr` pattern | `0x08004510` | Instruction trace and public HAL source sequence |
| Runtime vectors | Base `0x20000000`, entries 2..74 written | Native replay; entries 0/1 are untouched in this segment |
| VTOR write | `0xe000ed08 <- 0x20000000` | Native replay |
| Initialized data in flash | `0x080340e8..0x08034f4c` | Native copy operands |
| Initialized data in SRAM | `0x20000400..0x20001264` (3,684 bytes) | Entire copied range equals flash bytes |
| Untouched gap | `0x20001264..0x20001268` | Sentinel retained in replay; purpose unresolved |
| BSS | `0x20001268..0x2000e414` (53,676 bytes) | Entire range cleared by native loop |
| Bytes above BSS end | 7,148 bytes to `0x20010000` | Not a claim of available heap/stack capacity |
| Constructor walker, inferred | `0x080044f4` | Startup call and pointer/call iteration; not independently executed here |
| `cyg_start` pattern, inferred | `0x0800586a` | Startup call sequence; user/default hooks and scheduler startup calls |

No original linker script, heap boundary, complete section map or full boot has
been established. The provisional linear disassembly/literal-reference file
contains candidates because inline pools can decode as instructions; only the
reviewed/replayed paths carry stronger evidence.

## eCos and TCAT source identification

The local [TCAT firmware-development guide](<../../../../../doc/DICE_III_User_Guide/TCD30xx - Firmware Development.pdf>),
PDF pages 1–2, explicitly identifies eCos, GNU ARM EABI, HAL, DAL, CLI, routing,
mixing, flash and AVB modules. It describes an SDK distributed through Subversion
and configurable via eCos CDL. That is architectural context, not evidence that
the proprietary TCAT SDK is publicly available.

The blob has 24 SDK source-path strings under
`/media/psf/Home/Presonus/svn/tcat/trunk/firmware/project/sdk/packages/dice/`,
including `dal`, `cli`, `misc`, `dicedriver`, `fw_trl`, `avs`, `avb_audio`,
`dice_audio` and their concrete source filenames. Its 124 parsed CLI descriptor
records expose groups including `kernel`, `dal`, `dice`, `dicedriver`, `avbst`,
`mix`, `fw`, `nvm`, `tcp`, `ptp`, `marvell`, `mdio` and others. The parser
preserves tag/value pairs and callback pointers; function extents and original
symbols remain unresolved. See [SDK paths](../runtime-identification/sdk-source-paths.json) and
[CLI records](../runtime-identification/cli-registrations.json).

The public eCos Cortex-M `hal_misc.c` matches the reset's distinctive sequence:
exception vector installation, special SVC/PendSV handlers, SRAM VTOR, temporary
SVC replacement, data/BSS handling, default interrupt handlers and priorities,
variant/platform initialization, constructors and `cyg_start`. The `Idle Thread`
string provides another kernel-family anchor. This supports eCos lineage,
not an exact vendor build identification.

The two version strings are resolved by their actual banner references:

| Printed banner field | Value |
| --- | --- |
| Built with SDK Version | `1.0.0.0 local beta` |
| Firmware Application Version | `1.5.5.0` |

Neither is an eCos version. [Banner pointers](../runtime-identification/version-banner.json) retain the
instruction and string addresses. **The exact eCos release and TCAT revision
remain unknown.** The public 3.0-lineage Cortex-M source is an appropriate
reference family; TCAT may have used a CVS snapshot and private/backported
changes. The April 2012 vector-limit fix is retained as a candidate fingerprint,
not used to assert an exact version or build date.

Sources are available in [the pinned runtime source archive](../../../../shared/upstream/ecos/2580ee933ff5bed1f39c18c882f2e1593d980ef6/ecos-reference-2580ee933ff5.tar.gz),
commit `2580ee933ff5bed1f39c18c882f2e1593d980ef6` (2012-10-04), from a public
community mirror. Selected HAL/kernel/infra/I/O/libc/network source and license
notices are preserved unmodified. [Source provenance](../../../../shared/upstream/ecos/2580ee933ff5bed1f39c18c882f2e1593d980ef6/ecos-source.json) records
all archived file hashes, scope, release-branch reference and limitations.
The local sparse Git checkout also retains history. These are reference sources,
not the complete TCAT FDE/SDK or a configured, proven firmware rebuild.

The next source identification targets are HAL vectors, scheduler/thread
wrappers, synchronization, STM32 SPI/DMA drivers, flash and libc. Prefer matching
available source over translating their decompiler output; validate individual
matches before assigning original symbol identities or claiming behavior.

## Concrete command paths

The Linux host uses `Presonus::NOAA::TCard` and the `TCardSPI` transport. Existing
host SPI reconstruction records 20 MHz maximum-speed setup and SysEx framing;
its actual device path, concurrency, DMA and physical transfers are not replayed
by this phase. The packet consumer's function candidate starts at `0x08001454`;
the tested loop entry is `0x080014a2` and dequeue dependency `0x08000ce8`.

| Command | Native observed path | Status |
| --- | --- | --- |
| `0x11 UI_SET` | Host `sendSampleRate` -> `f0 11 rate (link & 0x7f) f7` -> case `0x08001686` -> store `rate+1`, post request `0x08003338`, update AVB rate state `0x0800f584` -> ACK | Host + STM32 + deferred-consumer replay |
| `0x28 AVB clock source` | Host `setClockSource` -> `f0 28 hi-nibble lo-nibble f7` -> case `0x080019b6` -> source byte update -> SDK boundary `0x0800fd60(0, source, cached_rate)` -> ACK | Host + STM32 replay; SDK peripheral work modelled |
| `0x16 ROUTE` | Four bytes per route -> case `0x080016f0` -> asymmetric source/destination block conversion -> `0x0800fda4(0, source_block, source_channel, destination_block, destination_channel, 1)` -> ACK | STM32 replay, 192 translation cases plus SDK-error case; host builder identity/static evidence only |
| `0x23 AVB start` | Nibble fields -> case `0x0800180e` -> `0x0800f544` | STM32 field/call/ACK replay; API side effects modelled |
| `0x24 AVB talker config` | Case `0x08001868` -> `0x0800f5b0` | Same bounded replay scope |
| `0x25 AVB talker enable` | Case `0x080018b0` -> `0x0800f5d4` | Same bounded replay scope |
| `0x2d AVB stop` | Case `0x0800185c` -> `0x0800f56c` | Same bounded replay scope |
| `0x30` | Re-apply stored AVB rate via `0x0800f584` | Static observation; not the host clock-source setter |
| `0x31` | Decode two nibbles -> `0x08003368` -> `0x08002840` | STM32 replay; separate direct-clock path, not host `setClockSource` |
| `0x17/0x19` | Special status/card request branches before the main table | Static observation, not replayed here |
| `0x1c/0x1d/0x20` | Shared secondary decoder at `0x08001d88`; GEQ-related paths | Static observation; processing remains pending |

The full main jump table is preserved in `dispatch-table.json`. The old host
debug-label routine does not label all later AVB commands; its labels are not a
complete command specification. Flash/update/serial-programming branches were
not executed.

### Deferred rate/link handoff

`0x08003338` writes state based at `0x20002a54`:
pending byte `+0x13c`, rate `+0x13d`, source `+0x13e`, link `+0x13f`;
then calls synchronization boundary `0x0800612c` on state `+0x20`.
Do not assume a particular semaphore/flag declaration from this call alone.

The link worker candidate starts at `0x08002fac`. Its segment at `0x08003000`
copies pending link to state `+4` and rate to `+0x10`, clears pending and requests
a state transition. Later branches at `0x0800319c` and `0x08003302` use the cached
source before calling `0x08002740`. Only the inactive-state consumer segment was
replayed. **An immediate positive ACK is not proof of completed clock lock or
successful asynchronous topology reconfiguration.**

### Route block conversion

| Wire type | Source block | Destination block | Channel adaptation |
| ---: | ---: | ---: | --- |
| 0 | 1 | 1 | unchanged |
| 1 | 1 | 1 | +64 |
| 2 | 3 | 0 | unchanged |
| 3 | 5 | 5 | unchanged |
| 4 | 5 | 5 | +64 |
| 5 | 12 | 12 | unchanged |
| 6 | 8 | 8 | unchanged |
| 7 | 9 | 9 | unchanged |

The DAL boundary error code `0xc4000005` causes `f0 16 00 f7`; the successful
modelled call produces `f0 16 01 f7`. Those are actual dispatcher/ACK instructions,
while DAL device behavior remains modelled. Numeric block IDs are retained;
external connector/signal meanings are not assigned from similarity alone.

## NIMH FPGA register boundary and manual use

The CLI `mix.gain` descriptor points to Thumb callback `0x0801d235` (instruction
entry `0x0801d234`). It checks two indices against 31 and writes:

`*(uint32_t*)0x60005204 = (arg0 << 27) | (arg1 << 22) | (gain & 0xffff)`.

The local mixer manual, PDF pages 5–8, describes a 32x32 coefficient matrix and
16-bit coefficients. Its diagram and prose/table have inconsistent index-bit
labels. This phase preserves the observed bit packing with neutral argument
names. NIMH's external address is measured from NIMH code; the manual's silicon
address is not substituted and no whole-address-space translation is inferred.

The 216 replay cases include normal indices, out-of-range indices and gain
truncation. They prove register-write shape/error paths against an emulated RAM
page, not FPGA coefficient interpretation, signal routing, timing or audio.

## Next bounded work

1. Trace STM32 SPI/DMA receive framing into the packet queue; current command
   tests inject completed frames and capture TX enqueue.
2. Reconstruct the link-worker transition helpers and DAL clock body, with valid
   state fixtures, through the relevant FPGA register writes and completion
   notifications. Preserve the ACK/completion distinction.
3. Continue route commits and GEQ/AVB handlers using local manual architecture;
   correlate exact FPGA register transactions with the existing NIMH bitstream
   evidence when that decoder has coverage.
4. Use the pinned eCos source to identify runtime/library routines and narrow
   vendor changes. Exact revision identification needs stronger fingerprints or
   TCAT configuration/FDE material; do not relabel the application/SDK banners.

Whole-image emulation, exact C/C++ declarations, an original linker script,
complete command coverage, concurrency, full FPGA behavior and hardware/audio
validation remain unresolved. No device programming, erase, live SPI or flash
operations were performed.
