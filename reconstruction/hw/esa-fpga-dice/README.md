# ESA FPGA variant: identified configuration target

Canonical hardware knowledge independent of the software release used to observe it.

## Established configuration facts

The mixer carries a variant-specific gzip payload `xmen_esa_top.bin` with decompressed size 1,485,512 bytes. Its recorded IDCODE is `0x04008093`, identifying Spartan-6 XC6SLX45. No package/speed-grade claim for this variant follows from the NIMH board photographs.

The stream uses 16-bit big-endian packet words, sync at raw offset `0x10`, and clear CTL DEC bits in the inspected writes. Gzip CRC/ISIZE and complete packet accounting pass; FPGA configuration CRC is not recomputed.

ESA `xmen_esa_top.bin` uses direct FDRI writes without observed MFWR/MFW compression.


## Architecture pattern and open questions

Host bundle selection distinguishes NIMH, ESA and NOAA variants; bundled images do not prove multiple fitted FPGA chips or the image currently programmed. NIMH decode/connectivity/functional results must not be generalized to this variant. Physical board/part mapping, package, pinout, active feature set, logic and interface behavior remain unresolved here.

## Sources and detailed evidence

- [Fpga id](<../../../evidence/recovery/2026-10-27/fpga-identification/assessment.json>)
- [Fpga images](<../../../evidence/recovery/2026-10-27/fpga-identification/manifest.json>)
- [Extraction](<../../shared/extraction/embedded-mcu-01/REPORT.md>)

## Software extraction points

- [mixer-13731](<../../artifacts/mixer-13731/esa-fpga-dice/README.md>)
- [mixer-7784](<../../artifacts/mixer-7784/esa-fpga-dice/README.md>)
- [mixer-8591](<../../artifacts/mixer-8591/esa-fpga-dice/README.md>)
- [mixer-9244](<../../artifacts/mixer-9244/esa-fpga-dice/README.md>)


[System architecture and discovery workflow](<../README.md>)
