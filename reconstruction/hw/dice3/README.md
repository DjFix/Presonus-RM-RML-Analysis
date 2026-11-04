# Surface integrated DICE III processor

Canonical hardware knowledge independent of the software release used to observe it.

## Architecture and boot

Local hardware/memory-map manuals identify an ARM926/ARM9EJ-S core and 320 KiB internal SRAM. This is integrated DICE III firmware, not Cortex-M, STM32 or a Linux ARM ELF. The raw image is 230,512 bytes, SHA-256 `0468d888f3d615e70065f5d535b9eadac7f8bf67185b53cc19c2cb7986c1d946`. The separate `components/dice3-surface-bin` has four trailing zeros and is a distinct artifact.

| ROM SPI header field | Observed value |
|---|---|
| Magic / family | `TCAT` / 3 |
| Flags | `0x31`: divider field1, PLL enabled, checksum enabled, fast-read disabled |
| PLL multiplier / pre-divider | 100 / 3 |
| Load address | `0x200` |
| Payload | 57,624 words, 230,496 bytes |
| SPI baud divider | 2 |

Entry `0x200` branches to `0x240`; runtime address = image file offset + `0x1f0`. Startup configures ARM modes/banked stacks and copies exception vectors to low memory. This is the 16-byte ROM header, not BOOT2 magic `0x20120710`.

## Runtime and register observations

The image contains 105 tagged CLI descriptors with 105 aligned ARM callbacks. Labels include mixer gain/configuration and six DAL callbacks; they are registration labels, not original C++ names or exact extents. Bounded mixer callbacks address coefficient register `0xc4000204` and configuration `0xc4000200`. Shared architectural roles with NIMH do not establish identical addresses, binaries or peripheral semantics.

SDK banner `1.0.0.0 local beta`, application `0.0.0.6`, target `Surface-AVB/DICE Option Card` and December 2015 build/date strings identify software provenance leads. They do not establish exact eCos source revision.

## Open questions and validation limits

ROM checksum validity is unresolved: tested MSB-first interpretations did not yield the documented zero residue. Bytes were not changed to force a match. No firmware execution, complete boot, physical peripheral behavior, original internal function symbols or cross-platform binary equivalence is established. Map subsystem behavior using local architecture manuals rather than direct CS18/RM firmware mapping.

## Sources and detailed evidence

- [Dice](<../../../uc-library/validation/dice-image/REPORT.md>)
- [Extraction](<../../shared/extraction/embedded-mcu-01/REPORT.md>)

## Software extraction points

- [surface-13840](<../../artifacts/surface-13840/dice3/README.md>)


[System architecture and discovery workflow](<../README.md>)
