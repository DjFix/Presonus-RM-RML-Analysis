# OMAP C674x DSP: audio processing partition

Canonical hardware knowledge independent of the software release used to observe it.

## Loader, memory and control

The inspected mixer embeds ten DSP load payloads totaling **723,936 bytes**, including **161,632 bytes** in three executable objects. Original ARM-side data symbols include `_text`, `_fasttext`, `_text__c_int00`, `_const`, `_cinit`, `_pinit`, `_switch`, `_far`, `_mark` and `_data`.

| Runtime region | Observation |
|---|---|
| `0x80000000` | 128-byte startup entry |
| `0xc7087800` | 137,600-byte `_text` |
| `0x11818600` | 23,904-byte `_fasttext` |
| `0xc7000000` | 554,520-byte loaded `_far` data, not code |
| `0xc70c3960` | 1,140-byte initialization table; 64 parsed records |
| `0x8001c000`, size `0x4000` | ARM/DSP shared-memory link |

`bootDSP` copies section-bound embedded payloads. `mixer_dsp.out` is a manager argument; it does not prove an external file was read. The synthetic C6000 load ELF is analysis scaffolding, not an original `.out` or a flash image.

## Processing discoveries

| Role | Target ID | DSP audio callback |
|---|---:|---|
| Main mixing engine | 30 | `0xc708dfa0` |
| Channel EQ | 12 | `0x1181cda8` |
| Gate | 5 | `0xc709b192` |
| Compressor | 6 | `0xc709fb32` |
| Limiter | 4 | `0x1181db0a` |
| Reverb | 22 | `0xc7089a20` |
| Delay | 23 | `0xc7095978` |

These analyst role labels bind host target IDs, DSP type-accessor values, process tables, property consumers and executable arithmetic. They are not recovered original DSP class/function names. Main-engine floating-point summation and child callback calls establish actual processing paths, not merely parameter setters.

Host messages include `comp`, `gate`, `lim `, `iir4`, `mbqd`, `mprm` and `mpro`; endian presentation is documented in the source report. Compressor, gate and EQ callbacks reach fast arithmetic kernels. Seven expected process bindings passed static assertions; no DSP code was executed.

## Offload boundary

NOAA GEQ sends a 36-byte SysEx frame: command `0x1d`, selectors and 31 seven-bit band values, then configures a TDM GEQ insert or bypass. This establishes GEQ control/routing offload to the card subsystem, not the exact CPU/FPGA location of GEQ arithmetic. Do not move the independently identified OMAP dynamics/effects into the card model.

## Open questions

Complete kernel equations and modes, model/sample-rate-specific graph, DMA/audio serial pin mapping, original DSP declarations, runtime latency and exact GEQ execution hardware remain unresolved. Disassembly coverage and byte extraction are not semantic or timing validation.

## Sources and detailed evidence

- [Dsp](<../../../evidence/recovery/2026-10-27/c674x-dsp/REPORT.md>)
- [Dsp process](<../../../evidence/recovery/2026-10-27/c674x-dsp/extraction-01/process-map.json>)

[System architecture and discovery workflow](<../README.md>)
