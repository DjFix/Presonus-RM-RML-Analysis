# noaa-stm32-dice — mixer-6184

Human entry point for architecture, findings and remaining work. The directory names the containing host release; it does not establish the embedded firmware version.

## Architecture and patterns

This is a separate raw STM32 firmware family embedded in the Linux mixer application. Startup/header inspection supports STM32 flash/RAM and Thumb code; exact board/part assignment for NOAA and ESA remains unresolved in this work.

Use [the NIMH architecture study](../../mixer-13731/nimh-stm32-dice/README.md) as a documented analysis pattern. Its tested behavior and runtime version do not automatically apply to this release or image family.

## Established findings

Original bytes, ELF symbol identity, offsets and hashes are recorded. No command-path or complete boot replay for this particular version is claimed here.

Status: `extracted-bytes-verified`. No new behavior, ABI or hardware validation is implied by this README.

## Open questions

Confirm board identity and embedded version; map startup and runtime dependencies; trace host commands and device boundaries; validate behavior for this exact image.

## Reports and evidence

- [Cross-version extraction report](../../../shared/extraction/embedded-mcu-01/REPORT.md)
- [Original symbols, ranges and source hashes](../../../shared/extraction/embedded-mcu-01/manifest.json)
- [Extraction byte verification](../../../shared/extraction/embedded-mcu-01/linux-verification.json)
- [Local TCAT architecture guide](<../../../../doc/DICE_III_User_Guide/TCD30xx - Firmware Development.pdf>)

## Firmware and identity

[Component manifest](manifest.json) records identities and validation limits.

- [RM16_RC2_AVB_6184 / _ZL13noaa_arm_code.bin](firmware/RM16_RC2_AVB_6184/_ZL13noaa_arm_code.bin)

[All components and releases](../../../README.md)
