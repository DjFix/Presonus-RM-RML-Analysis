# NOAA FPGA variant: identified configuration target

Canonical hardware knowledge independent of the software release used to observe it.

## Established configuration facts

The mixer carries a variant-specific gzip payload `storm_top.bin` with decompressed size 1,301,390 bytes. Its recorded IDCODE is `0x04008093`, identifying Spartan-6 XC6SLX45. No package/speed-grade claim for this variant follows from the NIMH board photographs.

The stream uses 16-bit big-endian packet words, sync at raw offset `0x10`, and clear CTL DEC bits in the inspected writes. Gzip CRC/ISIZE and complete packet accounting pass; FPGA configuration CRC is not recomputed.

NOAA `storm_top.bin` uses repeated-frame compression: 2,162 MFWR register writes and 57 MFW commands. Expand repeated frames before frame-address comparison.


## Architecture pattern and open questions

Host bundle selection distinguishes NIMH, ESA and NOAA variants; bundled images do not prove multiple fitted FPGA chips or the image currently programmed. NIMH decode/connectivity/functional results must not be generalized to this variant. Physical board/part mapping, package, pinout, active feature set, logic and interface behavior remain unresolved here.

## Sources and detailed evidence

- [Fpga id](<../../../evidence/recovery/2026-10-27/fpga-identification/assessment.json>)
- [Fpga images](<../../../evidence/recovery/2026-10-27/fpga-identification/manifest.json>)
- [Extraction](<../../shared/extraction/embedded-mcu-01/REPORT.md>)

## Software extraction points

- [mixer-13731](<../../artifacts/mixer-13731/noaa-fpga-dice/README.md>)
- [mixer-6184](<../../artifacts/mixer-6184/noaa-fpga-dice/README.md>)
- [mixer-6439](<../../artifacts/mixer-6439/noaa-fpga-dice/README.md>)
- [mixer-7784](<../../artifacts/mixer-7784/noaa-fpga-dice/README.md>)
- [mixer-8591](<../../artifacts/mixer-8591/noaa-fpga-dice/README.md>)
- [mixer-9244](<../../artifacts/mixer-9244/noaa-fpga-dice/README.md>)


[System architecture and discovery workflow](<../README.md>)
