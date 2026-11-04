# XMEN STM32 firmware extraction — 2026-10-27

The mixer contains three separate raw STM32 firmware images. They can be
disassembled and reconstructed into reviewed C/C++ behavior, but the original
source text, comments, local names and declarations cannot be restored exactly
from these binaries. No embedded functions have been promoted to recovered or
behaviorally validated status by this extraction.

## Hardware and architecture evidence

- Project photo `images/AVB Card/IMG_6616.jpg` shows the MCU marking
  **STM32F103ZET6**. Photo `IMG_6618.jpg` shows board **400-XMEN-NIMH-C**.
  The F103ZE is a Cortex-M3 device with 512 KiB flash and 64 KiB SRAM
  ([ST product documentation](https://www.st.com/en/microcontrollers-microprocessors/stm32f103ze.html)).
- All three mixer `*_arm_code` objects have initial SP `0x20010000`,
  odd reset pointers in the `0x08000000` flash address range, XMEN module
  banners and `STM32 Internal Flash` strings. They contain literal references
  to VTOR `0xe000ed08`, STM32F1 RCC `0x40021000`, and flash `0x40022000`.
- The **NIMH** pairing is supported by the photographed board identity plus
  the embedded `*-NIMH Module` banners. NOAA and ESA are separate image families;
  the precise board/part mapping of those variants is not established here.
- `xmenpanel_code` and `xrackpanel_code` are different images: their initial
  SP is `0x10002000` and reset addresses are near zero. Their symbol names do
  not establish that they belong to the XMEN card's STM32. Keep them separate.
- The surface DICE III payload is **ARM926/ARM9EJ-S**, not Cortex-M. This is
  established by the local TCAT manuals and previous header/startup inspection:
  `temp/recovery-package/uc-library/validation/dice-image/REPORT.md`.
  It has a `TCAT` boot header, ARM entry at `0x200`, and an initial branch to
  `0x240`. The separate `panel_surface_code` does not establish an STM32 on
  the surface.

## Primary extracted binaries: mixer 13731

Input ELF: `Cutter Analysis/mixer`; it is byte-identical to the mixer member
of the RM16/RML16/RML32 Rack 13731 archives.

ELF SHA-256: `9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07`.

| Original ELF symbol | ELF address | ELF file offset | Bytes | Reset pointer | Export |
| --- | --- | --- | ---: | --- | --- |
| `_ZL13nimh_arm_code` | `0x2608d7` | `0x2588d7` | 216,908 | `0x08004511` | [NIMH STM32](../../../artifacts/mixer-13731/nimh-stm32-dice/firmware/mixer-analysis/_ZL13nimh_arm_code.bin) |
| `_ZL13noaa_arm_code` | `0x1c82d8` | `0x1c02d8` | 173,808 | `0x080047b9` | [NOAA STM32](../../../artifacts/mixer-13731/noaa-stm32-dice/firmware/mixer-analysis/_ZL13noaa_arm_code.bin) |
| `_ZL12esa_arm_code` | `0x2f4767` | `0x2ec767` | 147,900 | `0x080040e5` | [ESA STM32](../../../artifacts/mixer-13731/esa-stm32-dice/firmware/mixer-analysis/_ZL12esa_arm_code.bin) |

All are file-backed `.rodata` objects. Their original case-sensitive symbol
identities, full image hashes and per-release provenance are in
[manifest.json](manifest.json). Preserve the entire objects: the words following
SP/reset are not a conventional complete Cortex-M vector table. This report
does not certify the flash packaging, checksum, bootloader partition or a safe
hardware programming procedure. The `0x08000000` analysis base is corroborated
by reset/startup and literal addresses; it is not a flashing instruction.

The surface host ELF is SHA-256
`304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0`.
Its exact `_ZL18dice3_surface_code` export is
[230,512 bytes](../../../artifacts/surface-13840/dice3/firmware/surface-analysis/_ZL18dice3_surface_code.bin), hash
`0468d888f3d615e70065f5d535b9eadac7f8bf67185b53cc19c2cb7986c1d946`.
The existing `components/dice3-surface-bin` has four additional zero bytes;
it must not replace the exact symbol export.

## Verification and coverage

The standard-library extractor uses
`section.file_offset + symbol.address - section.address`, verifies that the
whole range fits the section, and independently corroborates that mapping
against a file-backed `PT_LOAD` segment. Each saved object's bytes and SHA-256
are checked against its source ELF. Symbol-table row numbers are never offsets.
The historical `scripts/extract-symbol.sh` uses such a row number and is not
used as evidence here.

The manifest covers 19 input instances (two analysis ELFs and 17 update
archives), with 100 extracted objects and 32 STM32 image instances. Instance
counts include identical copies across bundles; they are not unique firmware
or recovered-function counts. FPGA, panel and update-script objects retain
their separate original identities. No FPGA logic reconstruction is claimed.

Four archives have no section table and were not assigned guessed symbol
boundaries: RML16AI/RML32AI 1.6.16489 and SL1642AI/SL3242AI 1.6.16191.
Their ELF hashes and empty extraction results remain in the manifest. The
successful 13731 extraction does not establish extraction of those versions.

Linux verification completed with Capstone 5.0.6: all 100 export hashes passed,
and 11 objects were independently re-extracted from the two primary ELFs.
The NOAA, NIMH and ESA startup prefixes decode as Thumb; the surface DICE
prefix decodes as ARM. Proof and bounded disassembly are in
[linux-verification.json](linux-verification.json) and
[startup-disassembly.txt](../../../evidence/mixer-13731/app/extraction-01/startup-disassembly.txt). They do not execute
firmware, reconstruct behavior, establish ABI fidelity, or validate hardware.

## Reconstruction feasibility

The STM32 images contain plaintext machine code, readable CLI/module strings
and, in the NIMH/ESA images, TCAT SDK source-path strings. These provide useful
anchors for recovering startup, peripheral initialization, flash handlers,
host/DICE transport and command handlers. Thumb-2 analysis must account for
embedded data and independently establish function boundaries and return types.
The original host ELF's debug symbols do not name functions inside raw images.

Next recovery work should establish vector relocation and runtime sections,
identify SDK/library code, map callbacks and protocols, then translate and
validate bounded functions. Flash/erase routines remain offline analysis only.
No flashing, device erase, hardware execution or function-readiness promotion
was performed.
