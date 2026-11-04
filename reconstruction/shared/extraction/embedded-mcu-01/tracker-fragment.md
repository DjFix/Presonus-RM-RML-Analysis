
## XMEN STM32 image extraction — 2026-10-27

Offline data-object extraction; no function-readiness or C++ count changes.
Full original identities, source/image hashes, addresses, section/PT_LOAD
mappings and saved exports: project evidence
`evidence/recovery/2026-10-27/xmen-stm32/manifest.json`. Findings and boundaries:
the same directory's `REPORT.md`; Linux proof: `linux-verification.json`.

| Binary / firmware | Original object | Bytes | Catalogued | Extracted and byte-verified | Pseudocode | C++ / behavior / hardware |
| --- | --- | ---: | --- | --- | --- | --- |
| mixer 13731 | `_ZL13nimh_arm_code` | 216,908 | yes | yes | pending | pending |
| mixer 13731 | `_ZL13noaa_arm_code` | 173,808 | yes | yes | pending | pending |
| mixer 13731 | `_ZL12esa_arm_code` | 147,900 | yes | yes | pending | pending |
| mixer 13731 | `xmenpanel_code` | 58,072 | yes | yes | pending | pending |
| mixer 13731 | `xrackpanel_code` | 28,308 | yes | yes | pending | pending |
| surface 13840 | `_ZL18dice3_surface_code` | 230,512 | yes | yes | existing bounded DICE analysis | see separate embedded DICE tracker |
| surface 13840 | `panel_surface_code` | 53,364 | yes | yes | pending | pending |

Mixer ELF SHA-256:
`9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07`.
Surface ELF SHA-256:
`304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0`.
NIMH board photo identifies STM32F103ZET6 (Cortex-M3). Surface DICE III is
ARM926/ARM9EJ-S, not Cortex-M. Panel images remain separately classified.
These are embedded images/data objects, not individually recovered host functions.

The manifest covers 19 input instances, 100 extracted objects and 32 STM32
image instances including duplicates. Newer RML 16489 and SL 16191 files lack
section tables: their boundaries remain unresolved; no guessed exports.
