# host: hardware knowledge

Canonical component description, independent of the release used to extract software. Physical board revisions remain separate identities when evidence shows a difference.

## Architecture and patterns

The host is the physical Linux application processor and its board interfaces. Application ELF versions are software extraction points, not hardware identities. Mixer processor details and board revisions need source-backed identification; no surface/mixer processor equivalence is assumed.

## Findings and their scope

This task retains extracted update-script data and shared input/provenance. It has not migrated or consolidated the broader application reconstruction owned by other tasks.

Status: `extracted-bytes-verified`. No new behavior, ABI or hardware validation is implied by this README.

A firmware release does not define a new hardware component. Software-derived observations retain their image identity and tested domain; they are not silently generalized across versions or physical board revisions.

## Open questions

Connect exact host symbols to packet construction and transport; distinguish upload/erase paths from runtime commands; link the separately maintained application reconstruction when available.

## Reports and evidence

- [Architecture and extraction report](<../../shared/extraction/embedded-mcu-01/REPORT.md>)
- [TCAT architecture documentation](<../../../doc/DICE_III_User_Guide/TCD30xx - Firmware Development.pdf>)

## Software extraction points

- [mixer-13731](<../../artifacts/mixer-13731/app/README.md>)
- [mixer-5652](<../../artifacts/mixer-5652/app/README.md>)
- [mixer-5844](<../../artifacts/mixer-5844/app/README.md>)
- [mixer-7784](<../../artifacts/mixer-7784/app/README.md>)
- [mixer-8591](<../../artifacts/mixer-8591/app/README.md>)
- [mixer-9244](<../../artifacts/mixer-9244/app/README.md>)

[How discoveries update hardware knowledge](../README.md#updating-the-hardware-model)
