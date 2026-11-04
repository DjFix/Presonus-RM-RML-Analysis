# esa-stm32-dice — mixer-8591

Software extraction and validation record. Hardware architecture is maintained separately. The directory names the containing host release; it does not establish the embedded firmware version.

## Hardware model

[Canonical esa-stm32-dice architecture, patterns, findings and open questions](<../../../hw/esa-stm32-dice/README.md>). Read this before analyzing the image. New software observations must be reconciled with that model and cited with their source identity and validation scope.

## Established findings

Original bytes, ELF symbol identity, offsets and hashes are recorded. No command-path or complete boot replay for this particular version is claimed here.

Status: `extracted-bytes-verified`. No new behavior, ABI or hardware validation is implied by this README.

## Software reconstruction questions

Confirm board identity and embedded version; map startup and runtime dependencies; trace host commands and device boundaries; validate behavior for this exact image.

## Reports and evidence

- [Cross-version extraction report](../../../shared/extraction/embedded-mcu-01/REPORT.md)
- [Original symbols, ranges and source hashes](../../../shared/extraction/embedded-mcu-01/manifest.json)
- [Extraction byte verification](../../../shared/extraction/embedded-mcu-01/linux-verification.json)
- [Local TCAT architecture guide](<../../../../doc/DICE_III_User_Guide/TCD30xx - Firmware Development.pdf>)

## Firmware and identity

[Component manifest](manifest.json) records identities and validation limits.

- [RM16_8591 / _ZL12esa_arm_code.bin](firmware/RM16_8591/_ZL12esa_arm_code.bin)

[All components and releases](../../../README.md)
