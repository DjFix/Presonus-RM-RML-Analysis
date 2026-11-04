# NIMH FireWire-side hardware

Canonical hardware knowledge independent of the software release used to observe it.

## Physical findings

Two FireWire connectors and LSI **L-FW842-07** are visible in the photo record, with nearby protection/filter groups. A FireWire PHY/interface role follows connector topology and device-family identification; individual FPGA-link bus signals and balls are not established.

## Software observations and pattern

The NOAA-family host interface includes FireWire/AVB routing and clock-control paths. That application capability is separate from proof of fitted interfaces or active PHY configuration on a specific unit. NOAA/ESA/NIMH bundle selection must not be interpreted as three simultaneously installed FPGA chips.

## Open questions

PHY/link wiring, clock sources/frequencies, reset/control nets, active host route topology and exact electrical behavior remain unresolved.

## Sources and detailed evidence

- [Photos](<../../../evidence/recovery/2026-10-27/nimh-fpga-decode-01/photo-correlations.json>)
- [Fpga id](<../../../evidence/recovery/2026-10-27/fpga-identification/assessment.json>)
- [Dsp](<../../../evidence/recovery/2026-10-27/c674x-dsp/REPORT.md>)

[System architecture and discovery workflow](<../README.md>)
