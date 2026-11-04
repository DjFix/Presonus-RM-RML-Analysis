# Hardware model discovery journal

## 2026-10-28 — consolidate existing discovered knowledge

| Earlier state | Reconciled statement | Evidence |
|---|---|---|
| FSMC merely available on the MCU | Native startup configures a 16-bit FSMC bus; physical ball/net assignment remains unknown | [MCU](nimh-stm32-dice/README.md), [card interface map](nimh-card/README.md) |
| FPGA logic not decoded | Later phases add configuration frames, global connectivity and partial functional equations; each has a separate coverage domain | [FPGA](nimh-fpga-dice/README.md) |
| FPGA hashes appear inconsistent | Compressed host object and decompressed configuration stream have distinct, verified identities | [FPGA](nimh-fpga-dice/README.md), [sources](SOURCES.md) |
| PTP diagnostic title implies hardware reads | PTP statistics routine reads MCU RAM; separate native external-register accesses establish the hardware interface | [Card](nimh-card/README.md) |
| OMAP DSP only a user-reported lead in the skeleton | Existing loader/process-table/ARM-to-DSP evidence identifies C674x main mixing, dynamics and effects paths | [DSP](dsp/README.md), [host](host/README.md) |
| Fader application not yet identified in this task's layout | Existing surface nested-image extraction establishes a 12,144-byte EFM32 application at 0x1000; original boot region remains absent | [Faderboard](faderboard/README.md) |
| Five fader target bytes have opaque address convention | Later panel driver analysis forms (address<<1)|direction, establishing seven-bit target values; physical board count remains unknown | [Panel](panel/README.md) |
| Command high bit treated as a query indicator | It does not suppress control side effects for 0x91/0xa4/0xa6 | [Faderboard](faderboard/README.md) |
| Generic receive or version response could imply flash readback | Reviewed app reads fixed contexts/version; absent bootloader capabilities remain unknown | [Faderboard](faderboard/README.md) |

Previous component READMEs are preserved in the consolidation evidence. This journal
records refinements from existing analysis; it does not promote behavioral readiness,
prove physical wiring or add hardware verification.
