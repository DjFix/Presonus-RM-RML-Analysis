# panel — mixer-5652

Software extraction and validation record. Hardware architecture is maintained separately. The directory names the containing host release; it does not establish the embedded firmware version.

## Hardware model

[Canonical panel architecture, patterns, findings and open questions](<../../../hw/panel/README.md>). Read this before analyzing the image. New software observations must be reconciled with that model and cited with their source identity and validation scope.

## Established findings

Separate panel image objects and original hashes are retained. Their names do not establish board wiring, protocol semantics or interchangeability.

Status: `extracted-bytes-verified`. No new behavior, ABI or hardware validation is implied by this README.

## Software reconstruction questions

Corroborate exact MCU/board identity, vector and memory layout, GPIO mapping, host transport and panel-control behavior.

## Reports and evidence

- [Cross-version extraction report](../../../shared/extraction/embedded-mcu-01/REPORT.md)
- [Original symbols, ranges and source hashes](../../../shared/extraction/embedded-mcu-01/manifest.json)
- [Extraction byte verification](../../../shared/extraction/embedded-mcu-01/linux-verification.json)
- [Local TCAT architecture guide](<../../../../doc/DICE_III_User_Guide/TCD30xx - Firmware Development.pdf>)

## Firmware and identity

[Component manifest](manifest.json) records identities and validation limits.

- [RM16AI_5652 / xrackpanel_code.bin](firmware/RM16AI_5652/xrackpanel_code.bin)
- [RM16AI_5652 / xmenpanel_code.bin](firmware/RM16AI_5652/xmenpanel_code.bin)

[All components and releases](../../../README.md)
