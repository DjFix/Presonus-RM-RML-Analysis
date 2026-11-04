# Hardware architecture and discovered knowledge

This is the canonical physical-system model. A software version is an evidence source,
not a hardware identity. Read a component here before extraction; reconcile new software
facts back into it with source hashes and explicit validation scope.

## System partition

- **Mixer host / DSP:** OMAP-L138 ARM9 runs Linux control; C674x executes main mixing,
  dynamics, channel EQ and effects. Shared memory links host and DSP.
- **NIMH AVB card:** STM32F103ZET6 plus XC6SLX45, external ISSI memory, Marvell switch
  and LSI FireWire-side group. STM32 code exposes FPGA-backed routing, AVB/PTP and clock interfaces.
- **Surface:** integrated ARM926 DICE III firmware is distinct from the LPC panel MCU.
  The panel contains and distributes a separate EFM32 fader application over I2C.
- **Variants:** NOAA/ESA images establish separate MCU/FPGA software families; physical
  board mapping and package assumptions must not be copied from NIMH without evidence.

## Component knowledge

| Component | What is established | Main unknown |
|---|---|---|
| [dice3](<dice3/README.md>) | ARM926 boot image, memory and CLI organization | Checksum, full runtime and physical behavior |
| [dsp](<dsp/README.md>) | Loaded C674x audio callbacks and shared-memory control | Complete equations, modes and timing |
| [esa-fpga-dice](<esa-fpga-dice/README.md>) | Variant-specific extraction/header observations | Physical board mapping and semantic behavior |
| [esa-stm32-dice](<esa-stm32-dice/README.md>) | Variant-specific extraction/header observations | Physical board mapping and semantic behavior |
| [faderboard](<faderboard/README.md>) | EFM32ZG application, command model and absent boot bytes | Original bootloader and motor/ADC pin mapping |
| [host](<host/README.md>) | Mixer OMAP-L138 and host control boundaries | Board revisions and surface host identity |
| [nimh-card](<nimh-card/README.md>) | Board inventory and joint MCU/FPGA role | Physical interconnect and revision applicability |
| [nimh-firewire](<nimh-firewire/README.md>) | LSI marking and connector group | PHY/link net assignments |
| [nimh-fpga-dice](<nimh-fpga-dice/README.md>) | Frames, partial logic, routing and I/O candidates | Complete primitive semantics, net assignments and timing |
| [nimh-marvell](<nimh-marvell/README.md>) | 88E6240 photo identity and candidate Ethernet boundary | Ports, straps and configuration |
| [nimh-memory](<nimh-memory/README.md>) | ISSI 512K × 16 pseudo-SRAM photo identity | Ownership, pin order and timing |
| [nimh-stm32-dice](<nimh-stm32-dice/README.md>) | Memory, SPI/DMA queues, FSMC configuration and register accesses | Physical buses, completion and concurrency |
| [noaa-fpga-dice](<noaa-fpga-dice/README.md>) | Variant-specific extraction/header observations | Physical board mapping and semantic behavior |
| [noaa-stm32-dice](<noaa-stm32-dice/README.md>) | Variant-specific extraction/header observations | Physical board mapping and semantic behavior |
| [panel](<panel/README.md>) | LPC-family images and panel-to-fader I2C protocol | Exact part/revision and physical control mapping |

## Evidence levels and corrections

Photograph observations establish visible markings/topology; local manuals establish
reference architecture; native loads/stores and static register arithmetic establish
software-visible interfaces; bounded execution establishes only the modeled/tested domain.
None alone proves fitted wiring, audio equivalence or live timing.

The initial FSMC uncertainty is refined by later configured-bus evidence. The initially
opaque fader target bytes are now seven-bit I2C addresses following the decoded helper.
DSP and fader skeletons have been replaced with the existing DSP and EFM reports.
Earlier FPGA identification/decode statuses are historical checkpoints superseded by
connectivity and partial-functional work, while their unknowns and denominators remain.
The absent PreSonus bootloader is not replaced by stock AN0003 reference sources.

## Updating the hardware model

1. Before extraction or reconstruction, read the component README and its open questions.
   Use its known processor, memory, boot and interface constraints to guide analysis.
2. Record each new observation in evidence: source ELF/blob SHA-256, container release,
   original symbol/range or embedded address, method, outcome and bounded validation domain.
3. Reconcile the observation with this hardware description. Mark it as board/document
   evidence, software-observed behavior, inference, user-reported information or unresolved.
   Software programming a register proves the observed code path; it alone does not prove
   wiring, physical timing or implementation of the peripheral.
4. Correct the canonical component README and open questions when warranted, citing the
   new evidence. Preserve the previous statement and reason in the discovery journal.
   Conflicting observations remain visible until resolved; do not overwrite uncertainty.
5. Keep runtime versions, SDK identity and version-specific behavior in software artifacts.
   Link those extraction points back to the hardware model. A version change alone does
   not create another hardware component; a proven physical revision can.

## Discovery journal

- 2026-10-28: separated physical component knowledge from software extraction points.
  Existing software observations are retained with their original validation limits.
  Faderboard application and bootloader map to the same physical board. `app` maps to
  the host processor rather than a fictional hardware component named app.

[Software results by release](../README.md#software-extraction-points) · [Shared provenance](../shared/README.md)

## Source provenance and history

[Source catalog](SOURCES.md) · [Discovery and correction journal](DISCOVERIES.md)
