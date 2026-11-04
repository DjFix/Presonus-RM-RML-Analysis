# Reconstruction: architecture and findings

Start with a component README. It summarizes architecture, useful patterns, established
findings and open questions, then links to reports, exact binaries and validation evidence.
Container releases and embedded firmware versions are tracked separately.

## Components

| Component | Start here | Current scope in this task |
|---|---|---|
| `app` | [Linux host application inputs](artifacts/mixer-13731/app/README.md) | Extraction and linked evidence; broader work remains separate |
| `esa-fpga-dice` | [ESA FPGA](artifacts/mixer-13731/esa-fpga-dice/README.md) | Extraction and linked evidence; broader work remains separate |
| `esa-stm32-dice` | [ESA MCU](artifacts/mixer-13731/esa-stm32-dice/README.md) | Extraction and linked evidence; broader work remains separate |
| `nimh-fpga-dice` | [NIMH FPGA: payload and related connectivity work](artifacts/mixer-13731/nimh-fpga-dice/README.md) | Extraction and linked evidence; broader work remains separate |
| `nimh-stm32-dice` | [NIMH MCU: architecture, runtime and command paths](artifacts/mixer-13731/nimh-stm32-dice/README.md) | Bounded offline native replay |
| `noaa-fpga-dice` | [NOAA FPGA](artifacts/mixer-13731/noaa-fpga-dice/README.md) | Extraction and linked evidence; broader work remains separate |
| `noaa-stm32-dice` | [NOAA MCU](artifacts/mixer-13731/noaa-stm32-dice/README.md) | Extraction and linked evidence; broader work remains separate |
| `panel` | [Panel controller](artifacts/mixer-13731/panel/README.md) | Extraction and linked evidence; broader work remains separate |
| `dice3` | [Surface integrated DICE III](artifacts/surface-13840/dice3/README.md) | Extraction and linked evidence; broader work remains separate |

Marvell switch configuration, OMAP DSP, faderboard firmware and its bootloader have
no deliverables from this task in this tree yet. Their absence is not a claim that no
other task has studied them.

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
