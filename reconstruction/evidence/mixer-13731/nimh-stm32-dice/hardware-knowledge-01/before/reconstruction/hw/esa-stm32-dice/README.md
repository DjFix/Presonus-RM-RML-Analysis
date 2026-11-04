# esa-stm32-dice: hardware knowledge

Canonical component description, independent of the release used to extract software. Physical board revisions remain separate identities when evidence shows a difference.

## Architecture and patterns

This is a separate raw STM32 firmware family embedded in the Linux mixer application. Startup/header inspection supports STM32 flash/RAM and Thumb code; exact board/part assignment for NOAA and ESA remains unresolved in this work.

Use [the NIMH architecture study](../nimh-stm32-dice/README.md) as a documented analysis pattern. Its tested behavior and runtime version do not automatically apply to this release or image family.

## Findings and their scope

Original bytes, ELF symbol identity, offsets and hashes are recorded. No command-path or complete boot replay for this particular version is claimed here.

Status: `extracted-bytes-verified`. No new behavior, ABI or hardware validation is implied by this README.

A firmware release does not define a new hardware component. Software-derived observations retain their image identity and tested domain; they are not silently generalized across versions or physical board revisions.

## Open questions

Confirm board identity and embedded version; map startup and runtime dependencies; trace host commands and device boundaries; validate behavior for this exact image.

## Reports and evidence

- [Architecture and extraction report](<../../shared/extraction/embedded-mcu-01/REPORT.md>)
- [TCAT architecture documentation](<../../../doc/DICE_III_User_Guide/TCD30xx - Firmware Development.pdf>)

## Software extraction points

- [mixer-13731](<../../artifacts/mixer-13731/esa-stm32-dice/README.md>)
- [mixer-7784](<../../artifacts/mixer-7784/esa-stm32-dice/README.md>)
- [mixer-8591](<../../artifacts/mixer-8591/esa-stm32-dice/README.md>)
- [mixer-9244](<../../artifacts/mixer-9244/esa-stm32-dice/README.md>)

[How discoveries update hardware knowledge](../README.md#updating-the-hardware-model)
