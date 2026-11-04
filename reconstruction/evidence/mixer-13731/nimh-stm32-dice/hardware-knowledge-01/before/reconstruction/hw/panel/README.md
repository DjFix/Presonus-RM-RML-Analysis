# panel: hardware knowledge

Canonical component description, independent of the release used to extract software. Physical board revisions remain separate identities when evidence shows a difference.

## Architecture and patterns

Panel-controller firmware is separate from the AVB STM32 images. Initial SP `0x10002000` and reset pointers near zero are useful architecture clues. The user identifies the panel MCU as LPC1317F; byte/header evidence alone does not independently establish that exact part.

## Findings and their scope

Separate panel image objects and original hashes are retained. Their names do not establish board wiring, protocol semantics or interchangeability.

Status: `extracted-bytes-verified`. No new behavior, ABI or hardware validation is implied by this README.

A firmware release does not define a new hardware component. Software-derived observations retain their image identity and tested domain; they are not silently generalized across versions or physical board revisions.

## Open questions

Corroborate exact MCU/board identity, vector and memory layout, GPIO mapping, host transport and panel-control behavior.

## Reports and evidence

- [Architecture and extraction report](<../../shared/extraction/embedded-mcu-01/REPORT.md>)
- [TCAT architecture documentation](<../../../doc/DICE_III_User_Guide/TCD30xx - Firmware Development.pdf>)

## Software extraction points

- [mixer-13731](<../../artifacts/mixer-13731/panel/README.md>)
- [mixer-5510](<../../artifacts/mixer-5510/panel/README.md>)
- [mixer-5550](<../../artifacts/mixer-5550/panel/README.md>)
- [mixer-5652](<../../artifacts/mixer-5652/panel/README.md>)
- [mixer-5844](<../../artifacts/mixer-5844/panel/README.md>)
- [mixer-6184](<../../artifacts/mixer-6184/panel/README.md>)
- [mixer-6439](<../../artifacts/mixer-6439/panel/README.md>)
- [mixer-7784](<../../artifacts/mixer-7784/panel/README.md>)
- [mixer-8591](<../../artifacts/mixer-8591/panel/README.md>)
- [mixer-9244](<../../artifacts/mixer-9244/panel/README.md>)
- [surface-13840](<../../artifacts/surface-13840/panel/README.md>)

[How discoveries update hardware knowledge](../README.md#updating-the-hardware-model)
