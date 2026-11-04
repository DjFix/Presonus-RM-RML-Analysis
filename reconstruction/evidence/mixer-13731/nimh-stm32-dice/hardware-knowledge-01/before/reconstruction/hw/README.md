# Hardware architecture and discovery

Start here for the physical system. Components are independent of the software release
that exposed them. Keep distinct board revisions where evidence establishes differences.
The MCU and FPGA records describe parts of an AVB card; shared DICE functionality is
an architectural relationship, not binary or hardware equivalence.

## Components

- [dice3](<dice3/README.md>)
- [dsp](<dsp/README.md>)
- [esa-fpga-dice](<esa-fpga-dice/README.md>)
- [esa-stm32-dice](<esa-stm32-dice/README.md>)
- [faderboard](<faderboard/README.md>)
- [host](<host/README.md>)
- [nimh-fpga-dice](<nimh-fpga-dice/README.md>)
- [nimh-marvell](<nimh-marvell/README.md>)
- [nimh-stm32-dice](<nimh-stm32-dice/README.md>)
- [noaa-fpga-dice](<noaa-fpga-dice/README.md>)
- [noaa-stm32-dice](<noaa-stm32-dice/README.md>)
- [panel](<panel/README.md>)

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
