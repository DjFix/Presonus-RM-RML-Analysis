# panel — mixer-5844

Human entry point for architecture, findings and remaining work. The directory names the containing host release; it does not establish the embedded firmware version.

## Architecture and patterns

Panel-controller firmware is separate from the AVB STM32 images. Initial SP `0x10002000` and reset pointers near zero are useful architecture clues. The user identifies the panel MCU as LPC1317F; byte/header evidence alone does not independently establish that exact part.

## Established findings

Separate panel image objects and original hashes are retained. Their names do not establish board wiring, protocol semantics or interchangeability.

Status: `extracted-bytes-verified`. No new behavior, ABI or hardware validation is implied by this README.

## Open questions

Corroborate exact MCU/board identity, vector and memory layout, GPIO mapping, host transport and panel-control behavior.

## Reports and evidence

- [Cross-version extraction report](../../../shared/extraction/embedded-mcu-01/REPORT.md)
- [Original symbols, ranges and source hashes](../../../shared/extraction/embedded-mcu-01/manifest.json)
- [Extraction byte verification](../../../shared/extraction/embedded-mcu-01/linux-verification.json)
- [Local TCAT architecture guide](<../../../../doc/DICE_III_User_Guide/TCD30xx - Firmware Development.pdf>)

## Firmware and identity

[Component manifest](manifest.json) records identities and validation limits.

- [RM16_5844 / xrackpanel_code.bin](firmware/RM16_5844/xrackpanel_code.bin)
- [RM16_5844 / xmenpanel_code.bin](firmware/RM16_5844/xmenpanel_code.bin)

[All components and releases](../../../README.md)
