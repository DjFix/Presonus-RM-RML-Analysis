# NIMH STM32: control, memory and external bus

Canonical hardware knowledge independent of the software release used to observe it.

## Architecture

Photograph records identify STM32F103ZET6, Cortex-M3, 512 KiB flash and 64 KiB SRAM. The board uses the MCU with FPGA-backed peripherals. Software provides an eCos/TCAT runtime and customer command/control code. The part's capabilities and a firmware-configured interface are distinct from a measured board pinout.

## Memory and boot observations

| Item | Observed range/value | Scope |
|---|---|---|
| Initial stack / reset | `0x20010000` / pointer `0x08004511` | Raw NIMH vector/header |
| Image | `[0x08000000,0x08034f4c)` | 216,908-byte export, not complete flash dump |
| Runtime vectors | VTOR `0x20000000`; entries 2..74 written | Bounded reset replay; slots 0/1 untouched in tested segment |
| Initialized data | Flash `[0x080340e8,0x08034f4c)` → RAM `[0x20000400,0x20001264)` | 3,684 bytes copied |
| BSS | `[0x20001268,0x2000e414)` | 53,676 bytes cleared |
| Unclassified gap | `[0x20001264,0x20001268)` | Not labeled heap/stack |
| Above BSS to initial SP | 7,148 bytes | Not established free memory |

Flash words after the first SP/reset entries are metadata, not a conventional full flash vector table. Reset execution stops before complete boot; early hardware init and SVC are modeled boundaries in that replay.

## External bus and peripheral patterns

Static hardware-init code at `0x08004a44` configures FSMC with BCR1/BCR2 `0x81915` and BCR4 `0x1011`; the width field selects 16 bits. Real code references use control `0x6000xxxx` and table/buffer `0x6400xxxx` regions. Initialized RAM pointer `0x20000e08` holds HPLL base `0x60006000`; it is an initial value, not an immutable runtime guarantee. Exact address/data/control pin connections and memory sharing remain unknown.

The SPI1 receive setup programs data register `0x4001300c`, DMA1 channel 2, control `0xaf`, count 1,024 and buffer `0x2000cd14`. Parser `0x08000aa4` consumes modulo-1024 DMA position, recognizes frames and selects queues. Ordinary queue at `0x2000b480` has eight 256-byte slots with seven committed packets usable; other queues serve command `0x15` and commands above `0x3f`.

The replay covers 20 framing/queue cases, three alternate-queue cases and four fragmented commands through native dispatch/release. GPIO, interrupt delivery, scheduling and physical DMA arrivals remain modeled. A whole unseen DMA revolution is not detectable from the modulo index alone.

## Software-derived interface findings

- Host rate/link command `0x11`, AVB clock-source `0x28`, routes `0x16`; ACK proves acceptance, not clock lock or completed topology changes.
- Producer state at `0x20002b90` wakes a deferred worker; 12 tested inactive-link consumer cases copy pending rate/link state and clear the request.
- Runtime family is eCos/TCAT; 124 CLI records and 24 SDK paths are analysis anchors. Application `1.5.5.0` and SDK `1.0.0.0 local beta` identify the sampled software, not MCU hardware or exact eCos revision.
- Mixer coefficient callback writes `0x60005204`; index roles remain neutral where manual labels conflict.

## Open questions

Exact eCos vendor source/configuration, complete initialization and callback flow, clock completion, external bus timing, overrun/concurrency behavior and physical pin assignments remain unresolved. No embedded original C++ identities, production reconstruction, ABI compatibility or hardware equivalence is claimed.

## Sources and detailed evidence

- [Extraction](<../../shared/extraction/embedded-mcu-01/REPORT.md>)
- [Command](<../../artifacts/mixer-13731/nimh-stm32-dice/analysis/command-paths.md>)
- [Rx](<../../artifacts/mixer-13731/nimh-stm32-dice/analysis/receive-path.md>)
- [Functional](<../../../evidence/recovery/2026-10-27/nimh-functional-03/REPORT.md>)
- [Blocks](<../../../evidence/recovery/2026-10-27/nimh-functional-03/block-assessment.json>)

## Software extraction points

- [mixer-13731](<../../artifacts/mixer-13731/nimh-stm32-dice/README.md>)
- [mixer-6184](<../../artifacts/mixer-6184/nimh-stm32-dice/README.md>)
- [mixer-6439](<../../artifacts/mixer-6439/nimh-stm32-dice/README.md>)
- [mixer-7784](<../../artifacts/mixer-7784/nimh-stm32-dice/README.md>)
- [mixer-8591](<../../artifacts/mixer-8591/nimh-stm32-dice/README.md>)
- [mixer-9244](<../../artifacts/mixer-9244/nimh-stm32-dice/README.md>)


[System architecture and discovery workflow](<../README.md>)
