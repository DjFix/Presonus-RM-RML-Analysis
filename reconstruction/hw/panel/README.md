# LPC panel/system controller

Canonical hardware knowledge independent of the software release used to observe it.

## Identification and images

All three inspected outer panel arrays use initial SP `0x10002000` and LPC-family SYSCON `0x40048000`, IOCON `0x40044000` and USART `0x40008000`. Their sizes fit the user-identified LPC1317 and its SRAM0/flash map. Exact suffix/revision remains unproved by bytes alone; keep surface, rack and additional variants distinct.

| Source role | Host symbol | Bytes | Reset pointer |
|---|---|---:|---|
| Surface | `panel_surface_code` | 53,364 | `0x127` |
| Rack mixer | `xrackpanel_code` | 28,308 | `0x165` |
| Additional mixer-carried variant | `xmenpanel_code` | 58,072 | `0x11f` |

The additional image's presence does not prove it runs on the fitted rack panel. Initial eight-word checksum sums are nonzero and word `0x1c` is zero; no updater transformation or checksum repair is inferred. Arrays are exact update payloads, not complete certified flash dumps.

## Host and fader boundaries

Surface host UART `/dev/ttyS1` carries runtime ASCII-hex/opcode messages. Outer-panel replacement uses LPC ISP; `LPCProgrammer::open` includes `unlockFlash`, so it is not a read-only discovery routine. Host code references GPIO102/110 sequencing; physical reset/boot wiring remains unverified.

The surface panel contains a separate EFM32 application at outer offset `0x9e40`, length `0x2f70`. Normal-return startup calls updater `0x80d8` before its main loop. Panel I2C wrapper uses base `0x40000000`; address helper emits `(address<<1)|direction`. Logical target addresses are **0x61,0x60,0x69,0x68,0x6f**, not raw eight-bit write addresses or a verified board count.

Update transfer sends a 14-byte header and then fixed nested image bytes. Header includes version `0x1b`, LE32 length `0x2f70`, CRC-32 `0x2a9026dc`, and modulo-255 checks. Response helper returns only byte3 of a separate six-byte receive. A terminal I2C error can still yield the wrapper's nonzero completion return; normal return does not prove successful programming.

## Patterns and corrected findings

The earlier fader extraction retained ambiguous raw target bytes. Later address-helper analysis establishes seven-bit address values and explicit TX/RX address-byte formation. This updates the protocol knowledge without proving physical wiring. Header CRC/checksum models and nested-app behavioral checks are different proof domains from outer updater execution.

## Open questions

Confirm exact panel MCU/board revisions, physical target selection, controls and host reset wiring. ADC/buttons/encoders/fader/touch/LED maps and outer-updater timing/error behavior remain incomplete. No bootloader-read path follows from normal UART/I2C receive capability.

## Sources and detailed evidence

- [Panel](<../../../evidence/recovery/2026-10-27/lpc-system-control/REPORT.md>)
- [Panel protocol](<../../../evidence/recovery/2026-10-27/efm-reconstruction/panel/PANEL_PROTOCOL.md>)
- [Protocol](<../../../evidence/recovery/2026-10-27/efm32-update-protocol/PROTOCOL.md>)
- [Fader](<../../../evidence/recovery/2026-10-27/efm32-faders/REPORT.md>)
- [Readback](<../../../evidence/recovery/2026-10-27/efm-reconstruction/review/READBACK_REVIEW.md>)

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


[System architecture and discovery workflow](<../README.md>)
