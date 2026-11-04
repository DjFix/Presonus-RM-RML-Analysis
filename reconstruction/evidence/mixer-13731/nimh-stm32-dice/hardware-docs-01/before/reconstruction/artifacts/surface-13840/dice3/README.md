# dice3 — surface-13840

Human entry point for architecture, findings and remaining work. The directory names the containing host release; it does not establish the embedded firmware version.

## Architecture and patterns

The surface contains integrated DICE III firmware with an ARM926/ARM9EJ-S core, not Cortex-M. Its boot format and peripheral architecture must be treated separately from the NIMH STM32. Use the local TCAT manuals for architecture patterns.

## Established findings

The exact `_ZL18dice3_surface_code` export is 230,512 bytes. It has a TCAT boot header and ARM entry at offset `0x200`; preserve the exact symbol range rather than a padded derivative.

Status: `extracted-bytes-verified`. No new behavior, ABI or hardware validation is implied by this README.

## Open questions

Map integrated-processor startup and runtime, application interfaces and command completion. Shared architectural roles do not establish binary compatibility with NIMH.

## Reports and evidence

- [Cross-version extraction report](../../../shared/extraction/embedded-mcu-01/REPORT.md)
- [Original symbols, ranges and source hashes](../../../shared/extraction/embedded-mcu-01/manifest.json)
- [Extraction byte verification](../../../shared/extraction/embedded-mcu-01/linux-verification.json)
- [Local TCAT architecture guide](<../../../../doc/DICE_III_User_Guide/TCD30xx - Firmware Development.pdf>)

## Firmware and identity

[Component manifest](manifest.json) records identities and validation limits.

- [surface-analysis / _ZL18dice3_surface_code.bin](firmware/surface-analysis/_ZL18dice3_surface_code.bin)

[All components and releases](../../../README.md)
