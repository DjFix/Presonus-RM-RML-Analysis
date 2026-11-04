# NIMH external parallel memory

Canonical hardware knowledge independent of the software release used to observe it.

## Physical findings

The photo record identifies **ISSI IS66WV51216DBLL-55TLI**, a 512K × 16 parallel pseudo-SRAM, adjacent to the FPGA. Device-interface semantics identify address A[18:0], data DQ[15:0] and memory-control signal classes; they do not assign board nets.

## Software observations and pattern

STM32 startup configures a 16-bit FSMC interface and uses `0x6000xxxx` control and `0x6400xxxx` table/buffer regions. This strengthens a parallel-bus architecture but does not establish that every external access targets this memory chip. Keep FPGA register windows separate from physical SRAM capacity and chip selection.

## Open questions

Address/data permutation, byte enables, chip selects, read/write timing, arbitration and MCU/FPGA ownership/sharing remain unmeasured. Physical adjacency does not prove exclusive ownership.

## Sources and detailed evidence

- [Photos](<../../../evidence/recovery/2026-10-27/nimh-fpga-decode-01/photo-correlations.json>)
- [Functional](<../../../evidence/recovery/2026-10-27/nimh-functional-03/REPORT.md>)

[System architecture and discovery workflow](<../README.md>)
