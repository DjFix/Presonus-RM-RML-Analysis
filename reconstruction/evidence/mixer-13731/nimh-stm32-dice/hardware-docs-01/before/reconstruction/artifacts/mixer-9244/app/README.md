# app — mixer-9244

Human entry point for architecture, findings and remaining work. The directory names the containing host release; it does not establish the embedded firmware version.

## Architecture and patterns

The Linux application is the container and host-side control endpoint for embedded programming payloads. Original ELF symbols identify host functions and data; they do not name functions inside raw embedded images.

## Established findings

This task retains extracted update-script data and shared input/provenance. It has not migrated or consolidated the broader application reconstruction owned by other tasks.

Status: `extracted-bytes-verified`. No new behavior, ABI or hardware validation is implied by this README.

## Open questions

Connect exact host symbols to packet construction and transport; distinguish upload/erase paths from runtime commands; link the separately maintained application reconstruction when available.

## Reports and evidence

- [Cross-version extraction report](../../../shared/extraction/embedded-mcu-01/REPORT.md)
- [Original symbols, ranges and source hashes](../../../shared/extraction/embedded-mcu-01/manifest.json)
- [Extraction byte verification](../../../shared/extraction/embedded-mcu-01/linux-verification.json)
- [Local TCAT architecture guide](<../../../../doc/DICE_III_User_Guide/TCD30xx - Firmware Development.pdf>)

## Firmware and identity

[Component manifest](manifest.json) records identities and validation limits.

- [RM16_TC20_9244 / fwupdateScript_code.bin](firmware/RM16_TC20_9244/fwupdateScript_code.bin)
- [RML16_TC20_9244 / fwupdateScript_code.bin](firmware/RML16_TC20_9244/fwupdateScript_code.bin)

[All components and releases](../../../README.md)
