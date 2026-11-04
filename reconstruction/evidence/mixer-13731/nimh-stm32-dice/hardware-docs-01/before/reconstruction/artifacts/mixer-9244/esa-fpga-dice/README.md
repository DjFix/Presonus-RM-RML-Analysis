# esa-fpga-dice — mixer-9244

Human entry point for architecture, findings and remaining work. The directory names the containing host release; it does not establish the embedded firmware version.

## Architecture and patterns

This is an FPGA programming payload extracted from a host ELF, separate from executable MCU firmware. Preserve container/compression identity separately from the decoded bitstream and any derived netlist.

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

## Firmware and identity

[Component manifest](manifest.json) records identities and validation limits.

- [RM16_TC20_9244 / _ZL13esa_fpga_code.bin](firmware/RM16_TC20_9244/_ZL13esa_fpga_code.bin)
- [RML16_TC20_9244 / _ZL13esa_fpga_code.bin](firmware/RML16_TC20_9244/_ZL13esa_fpga_code.bin)

[All components and releases](../../../README.md)
