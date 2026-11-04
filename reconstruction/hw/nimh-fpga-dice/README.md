# NIMH Spartan-6: fabric, interfaces and recovery limits

Canonical hardware knowledge independent of the software release used to observe it.

## Physical and configuration identity

The photographed FPGA is XC6SLX45 CSG324 `-2C`; IDCODE `0x04008093` independently corroborates XC6SLX45, but not package or speed grade. The NIMH gzip object is 450,319 bytes, SHA-256 `0a6ff55b76117590464f2f32708b255c8db99406f4dac4490ae563e260513c20`. Its decompressed `xmen_nimh_avb_top.bin` is 1,485,512 bytes, SHA-256 `945b2c3a0f74cd39825ec361da680c92303f20ac7f7a98756b7a829216ef9dbb`. These two hashes identify successive representations, not conflicting firmware. Both were independently checked during consolidation.

The stream uses 16-bit big-endian Spartan-6 packet words, sync at raw offset `0x10`, and direct FDRI writes. No MFWR/MFW compression or CTL DEC encryption is indicated. Gzip CRC/size checks pass; FPGA configuration CRC is a separate unproven check.

## Configuration, connectivity and logic findings

| Layer | Established result | Important limit |
|---|---|---|
| Frames | 9,072 main, 128 BRAM, one I/O frame; 11,856,256 storage bits | Frame-byte audit is not independent semantic validation |
| Decode | 10,335,005 unique bits, 87.1692% | Includes zeros/defaults; not utilization or algorithm coverage |
| Unknown bits | 1,521,251 total; two set bits | HCLK frames 8491/8492 bits 513/512 remain unnamed |
| Connectivity | 695,847 canonical wires; 575,677 directed edges | Routing abstraction, not electrical timing |
| Primitive bindings | 360,748/360,748 mapped | 2,441 distinct primitive-input nets lack modeled source |
| Input binding sources | 255,527/257,975 have unique abstract source (99.0511%) | Not functional-equivalence percentage |
| Package | 218 user-I/O paths; 65 configured output drivers | Configured does not prove runtime drive |
| Partial equations | 43,000 equations across 6,254 slice instances; 130 output/tristate roots | Cone/boundary counts, not independent algorithms |

Recovered equation categories include 18,361 LUTs, 18,073 FF equations, 1,637 mux equations, 1,272 XOR equations and explicit gaps. Modeled behavior includes LUT truth tables, register controls, latches and carry equations. BRAM, DSP, serializers, complex input-register and clock-generator behavior retain boundaries; F7/F8 polarity, SRL and dedicated modes require further independent semantics.

Eight structural increment counters have widths 11,11,11,10,9,8,8,8. All 8,448 word states were checked for the increment relation. Width alone does not assign RTC/PTP/audio roles. A bounded raw-to-simplified audit compared 104,320 values and 1,156,928 register-transition tuples; it validates the rewrite domain, not FPGA silicon behavior. Final Yosys checking establishes parsing/hierarchy, not full synthesis or timing closure.

## Interface discoveries

STM32 code supports a 16-bit FSMC control region and AVB/listener/talker, MAC/RTC/PTP, router, clock, HPLL and InS register blocks. Exact register-to-cell-cone assignment remains open; see the card interface map.

Candidate DDR RX lanes are C18,D18,E18,F18,G18; candidate rank2-clock TX/clock lanes are E16,F16,G16,H16,J16,K16. Widths, I/O structure, switch photos and MCU MAC code support an RGMII grouping hypothesis. Individual RXD/TXD order, control/clock assignment, switch port and DDR phases are unverified. No exact original board-net assignments have been admitted.

## Patterns and historical corrections

The initial identification report predates decode, connectivity and partial-logic work; its 'logic not decoded' status is historical. Storage coverage, routed-source coverage and bounded functional rewrite checks have different denominators and must remain separate. The earlier SPI_BUSWIDTH database issue was corrected by using MODE-register semantics; a reboot setting is not evidence of the active programming transport.

## Open questions

Resolve the two HCLK bits and missing primitive semantics, confirm physical FPGA/FSMC/RGMII/serial-audio pin assignments, bind decoder cones to named registers, and recover packet/timestamp/audio behavior. Complete HDL hierarchy, original signal names, timing closure, full equivalence and hardware interoperability are not recovered.

## Sources and detailed evidence

- [Fpga id](<../../../evidence/recovery/2026-10-27/fpga-identification/assessment.json>)
- [Fpga images](<../../../evidence/recovery/2026-10-27/fpga-identification/manifest.json>)
- [Photos](<../../../evidence/recovery/2026-10-27/nimh-fpga-decode-01/photo-correlations.json>)
- [Decode](<../../../evidence/recovery/2026-10-27/nimh-fpga-decode-01/REPORT.md>)
- [Connectivity](<../../../evidence/recovery/2026-10-27/nimh-fpga-connectivity-02/REPORT.md>)
- [Functional](<../../../evidence/recovery/2026-10-27/nimh-functional-03/REPORT.md>)
- [Blocks](<../../../evidence/recovery/2026-10-27/nimh-functional-03/block-assessment.json>)

## Software extraction points

- [mixer-13731](<../../artifacts/mixer-13731/nimh-fpga-dice/README.md>)
- [mixer-6184](<../../artifacts/mixer-6184/nimh-fpga-dice/README.md>)
- [mixer-6439](<../../artifacts/mixer-6439/nimh-fpga-dice/README.md>)
- [mixer-7784](<../../artifacts/mixer-7784/nimh-fpga-dice/README.md>)
- [mixer-8591](<../../artifacts/mixer-8591/nimh-fpga-dice/README.md>)
- [mixer-9244](<../../artifacts/mixer-9244/nimh-fpga-dice/README.md>)


[System architecture and discovery workflow](<../README.md>)
