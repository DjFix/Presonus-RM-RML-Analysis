# NIMH Marvell switch and Ethernet boundary

Canonical hardware knowledge independent of the software release used to observe it.

## Physical findings

Photograph records identify Marvell **88E6240**, nearby Pulse magnetics and RJ45. This establishes the visible Ethernet-facing group, not the FPGA-connected port number, strap configuration or exact management wiring.

## Software and FPGA observations

STM32 Ethernet initialization references base `0x60004000`, MAC configuration `+0x300`, PTP RX `+0x80/+0x84/+0x88`, TX status `+0x104` and system configuration `+0x288`. RTC snapshots use `+0x0c/+0x10/+0x14`. These are FPGA-side software-visible MAC/PTP interfaces; do not call them proven Marvell internal register addresses.

The FPGA has five candidate DDR receive lanes at C18..G18 and six candidate TX/clock lanes at E16,F16,G16,H16,J16,K16. RGMII grouping is a strong structural hypothesis, not confirmed signal order or port wiring. CLI/source records contain marvell and mdio groups; their presence alone does not establish completed switch configuration recovery.

## Architectural pattern

Separate the external switch/PHY management plane, FPGA MAC/PTP datapath and host/STM32 control plane. A named register block or status string does not prove end-to-end Ethernet/AVB conformance.

## Open questions

Switch port mapping, MDC/MDIO continuity, straps, initialization sequence, VLAN/forwarding configuration, timestamp ingress/egress boundaries and live link behavior remain unresolved. No standalone switch configuration artifact or hardware capture has been validated by this task.

## Sources and detailed evidence

- [Photos](<../../../evidence/recovery/2026-10-27/nimh-fpga-decode-01/photo-correlations.json>)
- [Photo hashes](<../../../evidence/recovery/2026-10-27/nimh-fpga-decode-01/photos/manifest.json>)
- [Functional](<../../../evidence/recovery/2026-10-27/nimh-functional-03/REPORT.md>)
- [Avb](<../../../evidence/recovery/2026-10-27/nimh-functional-03/avb-register-map.json>)
- [Command](<../../artifacts/mixer-13731/nimh-stm32-dice/analysis/command-paths.md>)

[System architecture and discovery workflow](<../README.md>)
