# nimh-fpga-dice — mixer-6184

Human entry point for architecture, findings and remaining work. The directory names the containing host release; it does not establish the embedded firmware version.

## Architecture and patterns

This is an FPGA programming payload extracted from a host ELF, separate from executable MCU firmware. Preserve container/compression identity separately from the decoded bitstream and any derived netlist.

For NIMH, board/format evidence identifies a Spartan-6 XC6SLX45; STM32 and FPGA share the logical DICE role. Hardware partitioning and board signal names need independent evidence.

## Established findings

The extraction preserves original payload bytes and source identity. Extraction alone does not recover HDL, establish primitive behavior or prove hardware equivalence.

Status: `extracted-bytes-verified`. No new behavior, ABI or hardware validation is implied by this README.

## Open questions

Bind compressed payload to decoded-image hashes; identify device/format per variant; recover functional modules and physical interfaces; verify sequential behavior and hardware timing.

## Reports and evidence

- [Cross-version extraction report](../../../shared/extraction/embedded-mcu-01/REPORT.md)
- [Original symbols, ranges and source hashes](../../../shared/extraction/embedded-mcu-01/manifest.json)
- [Extraction byte verification](../../../shared/extraction/embedded-mcu-01/linux-verification.json)
- [Local TCAT architecture guide](<../../../../doc/DICE_III_User_Guide/TCD30xx - Firmware Development.pdf>)
- [Related FPGA connectivity report (separate task; check its input hashes before reuse)](../../../../evidence/recovery/2026-10-27/nimh-fpga-connectivity-02/REPORT.md)

## Firmware and identity

[Component manifest](manifest.json) records identities and validation limits.

- [RM16_RC2_AVB_6184 / _ZL14nimh_fpga_code.bin](firmware/RM16_RC2_AVB_6184/_ZL14nimh_fpga_code.bin)

[All components and releases](../../../README.md)
