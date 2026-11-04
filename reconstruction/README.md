# Reconstruction: architecture and findings

Start with `hw/` for hardware architecture and open questions. Then follow a software
extraction point for exact binaries, version-specific reports and validation evidence.
Container releases and embedded firmware versions are tracked separately.

## Hardware components

[Start with the version-independent hardware model](<hw/README.md>). Each physical component README consolidates architecture, patterns, findings, evidence and open questions.

## Software extraction points

The entries below identify software containers, not hardware variants. Read the linked hardware description first; use new software evidence to correct or refine it.

## Release-specific entry points

- **mixer-13731**: [app](artifacts/mixer-13731/app/README.md), [esa-fpga-dice](artifacts/mixer-13731/esa-fpga-dice/README.md), [esa-stm32-dice](artifacts/mixer-13731/esa-stm32-dice/README.md), [nimh-fpga-dice](artifacts/mixer-13731/nimh-fpga-dice/README.md), [nimh-stm32-dice](artifacts/mixer-13731/nimh-stm32-dice/README.md), [noaa-fpga-dice](artifacts/mixer-13731/noaa-fpga-dice/README.md), [noaa-stm32-dice](artifacts/mixer-13731/noaa-stm32-dice/README.md), [panel](artifacts/mixer-13731/panel/README.md)
- **mixer-5510**: [noaa-stm32-dice](artifacts/mixer-5510/noaa-stm32-dice/README.md), [panel](artifacts/mixer-5510/panel/README.md)
- **mixer-5550**: [noaa-stm32-dice](artifacts/mixer-5550/noaa-stm32-dice/README.md), [panel](artifacts/mixer-5550/panel/README.md)
- **mixer-5652**: [app](artifacts/mixer-5652/app/README.md), [noaa-stm32-dice](artifacts/mixer-5652/noaa-stm32-dice/README.md), [panel](artifacts/mixer-5652/panel/README.md)
- **mixer-5844**: [app](artifacts/mixer-5844/app/README.md), [noaa-stm32-dice](artifacts/mixer-5844/noaa-stm32-dice/README.md), [panel](artifacts/mixer-5844/panel/README.md)
- **mixer-6184**: [nimh-fpga-dice](artifacts/mixer-6184/nimh-fpga-dice/README.md), [nimh-stm32-dice](artifacts/mixer-6184/nimh-stm32-dice/README.md), [noaa-fpga-dice](artifacts/mixer-6184/noaa-fpga-dice/README.md), [noaa-stm32-dice](artifacts/mixer-6184/noaa-stm32-dice/README.md), [panel](artifacts/mixer-6184/panel/README.md)
- **mixer-6439**: [nimh-fpga-dice](artifacts/mixer-6439/nimh-fpga-dice/README.md), [nimh-stm32-dice](artifacts/mixer-6439/nimh-stm32-dice/README.md), [noaa-fpga-dice](artifacts/mixer-6439/noaa-fpga-dice/README.md), [noaa-stm32-dice](artifacts/mixer-6439/noaa-stm32-dice/README.md), [panel](artifacts/mixer-6439/panel/README.md)
- **mixer-7784**: [app](artifacts/mixer-7784/app/README.md), [esa-fpga-dice](artifacts/mixer-7784/esa-fpga-dice/README.md), [esa-stm32-dice](artifacts/mixer-7784/esa-stm32-dice/README.md), [nimh-fpga-dice](artifacts/mixer-7784/nimh-fpga-dice/README.md), [nimh-stm32-dice](artifacts/mixer-7784/nimh-stm32-dice/README.md), [noaa-fpga-dice](artifacts/mixer-7784/noaa-fpga-dice/README.md), [noaa-stm32-dice](artifacts/mixer-7784/noaa-stm32-dice/README.md), [panel](artifacts/mixer-7784/panel/README.md)
- **mixer-8591**: [app](artifacts/mixer-8591/app/README.md), [esa-fpga-dice](artifacts/mixer-8591/esa-fpga-dice/README.md), [esa-stm32-dice](artifacts/mixer-8591/esa-stm32-dice/README.md), [nimh-fpga-dice](artifacts/mixer-8591/nimh-fpga-dice/README.md), [nimh-stm32-dice](artifacts/mixer-8591/nimh-stm32-dice/README.md), [noaa-fpga-dice](artifacts/mixer-8591/noaa-fpga-dice/README.md), [noaa-stm32-dice](artifacts/mixer-8591/noaa-stm32-dice/README.md), [panel](artifacts/mixer-8591/panel/README.md)
- **mixer-9244**: [app](artifacts/mixer-9244/app/README.md), [esa-fpga-dice](artifacts/mixer-9244/esa-fpga-dice/README.md), [esa-stm32-dice](artifacts/mixer-9244/esa-stm32-dice/README.md), [nimh-fpga-dice](artifacts/mixer-9244/nimh-fpga-dice/README.md), [nimh-stm32-dice](artifacts/mixer-9244/nimh-stm32-dice/README.md), [noaa-fpga-dice](artifacts/mixer-9244/noaa-fpga-dice/README.md), [noaa-stm32-dice](artifacts/mixer-9244/noaa-stm32-dice/README.md), [panel](artifacts/mixer-9244/panel/README.md)
- **surface-13840**: [dice3](artifacts/surface-13840/dice3/README.md), [panel](artifacts/surface-13840/panel/README.md)

## Reading the evidence

[Shared inputs, upstream sources and extraction provenance](shared/README.md) support the component findings. `artifacts/` contains useful results; `evidence/` retains operational jobs, frozen proofs and logs. Earlier proof hashes describe their recorded snapshots; documentation edits are recorded separately and do not add behavioral validation.
