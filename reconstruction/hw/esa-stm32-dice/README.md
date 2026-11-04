# ESA MCU firmware family: hardware constraints

Canonical hardware knowledge independent of the software release used to observe it.

## Established observations

This separate raw MCU image starts with SP `0x20010000` and an odd reset pointer in STM32 flash range `0x08000000`. Strings include `STM32 Internal Flash`, module banners and STM32F1 RCC `0x40021000`, flash `0x40022000` and VTOR `0xe000ed08` references. Thumb startup inspection supports the STM32 family. Exact board/part mapping is not established from the NIMH photograph.

## Architecture pattern

Keep card MCU and FPGA payloads separate. Use vector/memory/peripheral evidence to constrain analysis before interpreting names. Public SDK/runtime matches and NIMH command paths are comparison leads, not recovered behavior for this image. NOAA GEQ host-side control/routing is established at subsystem level; its arithmetic execution site remains unknown.

## Open questions

Confirm variant board and MCU identity, runtime memory layout and source lineage, target selection and transport, physical interfaces and behavior for this exact image. No new hardware or semantic replay is established by extraction alone.

## Sources and detailed evidence

- [Extraction](<../../shared/extraction/embedded-mcu-01/REPORT.md>)
- [Extraction registry](<../../shared/extraction/embedded-mcu-01/manifest.json>)
- [Fpga id](<../../../evidence/recovery/2026-10-27/fpga-identification/assessment.json>)
- [Dsp](<../../../evidence/recovery/2026-10-27/c674x-dsp/REPORT.md>)

## Software extraction points

- [mixer-13731](<../../artifacts/mixer-13731/esa-stm32-dice/README.md>)
- [mixer-7784](<../../artifacts/mixer-7784/esa-stm32-dice/README.md>)
- [mixer-8591](<../../artifacts/mixer-8591/esa-stm32-dice/README.md>)
- [mixer-9244](<../../artifacts/mixer-9244/esa-stm32-dice/README.md>)


[System architecture and discovery workflow](<../README.md>)
