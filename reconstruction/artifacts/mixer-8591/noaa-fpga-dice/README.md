# noaa-fpga-dice — mixer-8591

Software extraction and validation record. Hardware architecture is maintained separately. The directory names the containing host release; it does not establish the embedded firmware version.

## Hardware model

[Canonical noaa-fpga-dice architecture, patterns, findings and open questions](<../../../hw/noaa-fpga-dice/README.md>). Read this before analyzing the image. New software observations must be reconciled with that model and cited with their source identity and validation scope.

## Established findings

The extraction preserves original payload bytes and source identity. Extraction alone does not recover HDL, establish primitive behavior or prove hardware equivalence.

Status: `extracted-bytes-verified`. No new behavior, ABI or hardware validation is implied by this README.

## Software reconstruction questions

Bind compressed payload to decoded-image hashes; identify device/format per variant; recover functional modules and physical interfaces; verify sequential behavior and hardware timing.

## Reports and evidence

- [Cross-version extraction report](../../../shared/extraction/embedded-mcu-01/REPORT.md)
- [Original symbols, ranges and source hashes](../../../shared/extraction/embedded-mcu-01/manifest.json)
- [Extraction byte verification](../../../shared/extraction/embedded-mcu-01/linux-verification.json)
- [Local TCAT architecture guide](<../../../../doc/DICE_III_User_Guide/TCD30xx - Firmware Development.pdf>)

## Firmware and identity

[Component manifest](manifest.json) records identities and validation limits.

- [RM16_8591 / _ZL14noaa_fpga_code.bin](firmware/RM16_8591/_ZL14noaa_fpga_code.bin)

[All components and releases](../../../README.md)
