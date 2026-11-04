# noaa-fpga-dice: hardware knowledge

Canonical component description, independent of the release used to extract software. Physical board revisions remain separate identities when evidence shows a difference.

## Architecture and patterns

This is an FPGA programming payload extracted from a host ELF, separate from executable MCU firmware. Preserve container/compression identity separately from the decoded bitstream and any derived netlist.

## Findings and their scope

The extraction preserves original payload bytes and source identity. Extraction alone does not recover HDL, establish primitive behavior or prove hardware equivalence.

Status: `extracted-bytes-verified`. No new behavior, ABI or hardware validation is implied by this README.

A firmware release does not define a new hardware component. Software-derived observations retain their image identity and tested domain; they are not silently generalized across versions or physical board revisions.

## Open questions

Bind compressed payload to decoded-image hashes; identify device/format per variant; recover functional modules and physical interfaces; verify sequential behavior and hardware timing.

## Reports and evidence

- [Architecture and extraction report](<../../shared/extraction/embedded-mcu-01/REPORT.md>)
- [TCAT architecture documentation](<../../../doc/DICE_III_User_Guide/TCD30xx - Firmware Development.pdf>)

## Software extraction points

- [mixer-13731](<../../artifacts/mixer-13731/noaa-fpga-dice/README.md>)
- [mixer-6184](<../../artifacts/mixer-6184/noaa-fpga-dice/README.md>)
- [mixer-6439](<../../artifacts/mixer-6439/noaa-fpga-dice/README.md>)
- [mixer-7784](<../../artifacts/mixer-7784/noaa-fpga-dice/README.md>)
- [mixer-8591](<../../artifacts/mixer-8591/noaa-fpga-dice/README.md>)
- [mixer-9244](<../../artifacts/mixer-9244/noaa-fpga-dice/README.md>)

[How discoveries update hardware knowledge](../README.md#updating-the-hardware-model)
