# dice3: hardware knowledge

Canonical component description, independent of the release used to extract software. Physical board revisions remain separate identities when evidence shows a difference.

## Architecture and patterns

The surface contains integrated DICE III firmware with an ARM926/ARM9EJ-S core, not Cortex-M. Its boot format and peripheral architecture must be treated separately from the NIMH STM32. Use the local TCAT manuals for architecture patterns.

## Findings and their scope

The exact `_ZL18dice3_surface_code` export is 230,512 bytes. It has a TCAT boot header and ARM entry at offset `0x200`; preserve the exact symbol range rather than a padded derivative.

Status: `extracted-bytes-verified`. No new behavior, ABI or hardware validation is implied by this README.

A firmware release does not define a new hardware component. Software-derived observations retain their image identity and tested domain; they are not silently generalized across versions or physical board revisions.

## Open questions

Map integrated-processor startup and runtime, application interfaces and command completion. Shared architectural roles do not establish binary compatibility with NIMH.

## Reports and evidence

- [Architecture and extraction report](<../../shared/extraction/embedded-mcu-01/REPORT.md>)
- [TCAT architecture documentation](<../../../doc/DICE_III_User_Guide/TCD30xx - Firmware Development.pdf>)

## Software extraction points

- [surface-13840](<../../artifacts/surface-13840/dice3/README.md>)

[How discoveries update hardware knowledge](../README.md#updating-the-hardware-model)
