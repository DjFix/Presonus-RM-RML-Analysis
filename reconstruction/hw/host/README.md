# Linux host processor and control boundaries

Canonical hardware knowledge independent of the software release used to observe it.

## Mixer architecture

Static loader and processing-location evidence identifies an **OMAP-L138 ARM9 + C674x DSP** architecture for the inspected mixer. Linux ARM configures DSP processors and coefficients, boots embedded DSP payloads and exchanges shared-memory messages. This is stronger than the prior user-only OMAP lead; it does not establish every surface/mixer board uses the same processor.

The DSP link maps physical `0x8001c000`, length `0x4000`. `OMAPTargetHandler` and `Presonus::Link::Messenger` connect host property messages to DSP consumers. Main mixing, channel EQ, gate, compressor, limiter, reverb and delay execute on DSP callbacks; GEQ parameters and insertion take the separate NOAA subsystem path.

## Host-to-peripheral partition

The mixer emits card command/control packets over SPI; acceptance ACKs are separate from clock/audio completion. The surface host uses panel UART `/dev/ttyS1`; runtime codec emits ASCII-hex fields followed by opcode, normally 115200 with optional 230400 in the source port. Its panel firmware update path invokes outer LPC ISP, not direct nested EFM flash access.

Host symbols identify application interfaces, not embedded raw-image functions or fitted boards. Shared fader-related classes in mixer ELF do not establish the presence of motorized fader hardware.

## Open questions

Exact processor package/board revisions, surface host identity, connector maps, active stream topology and scheduling/latency remain unresolved here. No live host/peripheral communication or hardware test was performed.

## Sources and detailed evidence

- [Dsp](<../../../evidence/recovery/2026-10-27/c674x-dsp/REPORT.md>)
- [Dsp process](<../../../evidence/recovery/2026-10-27/c674x-dsp/extraction-01/process-map.json>)
- [Command](<../../artifacts/mixer-13731/nimh-stm32-dice/analysis/command-paths.md>)
- [Protocol](<../../../evidence/recovery/2026-10-27/efm32-update-protocol/PROTOCOL.md>)
- [Fader](<../../../evidence/recovery/2026-10-27/efm32-faders/REPORT.md>)

## Software extraction points

- [mixer-13731](<../../artifacts/mixer-13731/app/README.md>)
- [mixer-5652](<../../artifacts/mixer-5652/app/README.md>)
- [mixer-5844](<../../artifacts/mixer-5844/app/README.md>)
- [mixer-7784](<../../artifacts/mixer-7784/app/README.md>)
- [mixer-8591](<../../artifacts/mixer-8591/app/README.md>)
- [mixer-9244](<../../artifacts/mixer-9244/app/README.md>)


[System architecture and discovery workflow](<../README.md>)
