# Hardware discovery source catalog

These are the source reports and registries consumed by the consolidated component descriptions. Their exact hashes are frozen in [the source binding record](<../evidence/mixer-13731/nimh-stm32-dice/hardware-knowledge-01/sources.json>). Later source revisions need a new reconciliation; no live hardware evidence was created by this consolidation.

| Source | Scope |
|---|---|
| [extraction](<../shared/extraction/embedded-mcu-01/REPORT.md>) | Existing report/registry; scope and limits retained on component pages |
| [extraction registry](<../shared/extraction/embedded-mcu-01/manifest.json>) | Existing report/registry; scope and limits retained on component pages |
| [fpga id](<../../evidence/recovery/2026-10-27/fpga-identification/assessment.json>) | Existing report/registry; scope and limits retained on component pages |
| [fpga images](<../../evidence/recovery/2026-10-27/fpga-identification/manifest.json>) | Existing report/registry; scope and limits retained on component pages |
| [photos](<../../evidence/recovery/2026-10-27/nimh-fpga-decode-01/photo-correlations.json>) | Existing report/registry; scope and limits retained on component pages |
| [photo hashes](<../../evidence/recovery/2026-10-27/nimh-fpga-decode-01/photos/manifest.json>) | Existing report/registry; scope and limits retained on component pages |
| [decode](<../../evidence/recovery/2026-10-27/nimh-fpga-decode-01/REPORT.md>) | Existing report/registry; scope and limits retained on component pages |
| [connectivity](<../../evidence/recovery/2026-10-27/nimh-fpga-connectivity-02/REPORT.md>) | Existing report/registry; scope and limits retained on component pages |
| [functional](<../../evidence/recovery/2026-10-27/nimh-functional-03/REPORT.md>) | Existing report/registry; scope and limits retained on component pages |
| [blocks](<../../evidence/recovery/2026-10-27/nimh-functional-03/block-assessment.json>) | Existing report/registry; scope and limits retained on component pages |
| [avb](<../../evidence/recovery/2026-10-27/nimh-functional-03/avb-register-map.json>) | Existing report/registry; scope and limits retained on component pages |
| [clocks](<../../evidence/recovery/2026-10-27/nimh-functional-03/clock-domains.json>) | Existing report/registry; scope and limits retained on component pages |
| [command](<../artifacts/mixer-13731/nimh-stm32-dice/analysis/command-paths.md>) | Existing report/registry; scope and limits retained on component pages |
| [rx](<../artifacts/mixer-13731/nimh-stm32-dice/analysis/receive-path.md>) | Existing report/registry; scope and limits retained on component pages |
| [panel](<../../evidence/recovery/2026-10-27/lpc-system-control/REPORT.md>) | Existing report/registry; scope and limits retained on component pages |
| [fader](<../../evidence/recovery/2026-10-27/efm32-faders/REPORT.md>) | Existing report/registry; scope and limits retained on component pages |
| [protocol](<../../evidence/recovery/2026-10-27/efm32-update-protocol/PROTOCOL.md>) | Existing report/registry; scope and limits retained on component pages |
| [panel protocol](<../../evidence/recovery/2026-10-27/efm-reconstruction/panel/PANEL_PROTOCOL.md>) | Existing report/registry; scope and limits retained on component pages |
| [readback](<../../evidence/recovery/2026-10-27/efm-reconstruction/review/READBACK_REVIEW.md>) | Existing report/registry; scope and limits retained on component pages |
| [dsp](<../../evidence/recovery/2026-10-27/c674x-dsp/REPORT.md>) | Existing report/registry; scope and limits retained on component pages |
| [dsp process](<../../evidence/recovery/2026-10-27/c674x-dsp/extraction-01/process-map.json>) | Existing report/registry; scope and limits retained on component pages |
| [dice](<../../uc-library/validation/dice-image/REPORT.md>) | Existing report/registry; scope and limits retained on component pages |

FPGA gzip-to-raw SHA-256 checks were independently repeated for the NIMH, NOAA and ESA payloads. Hardware-photo identities are attributed to the existing hash-bound photo analysis; this consolidation did not perform new continuity measurements.
