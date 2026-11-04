
## NIMH STM32 SPI receive path — phase 02

Input `_ZL13nimh_arm_code` in mixer 13731, host ELF SHA-256
`9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07`;
blob SHA-256 `b0979352e18a1093051fc6118a47694773cb9240e88087eca03aaa2ffe0f5e17`.

| Binary/range | Catalogue / bytes | Analysis / behavioral status | C++ / ABI / hardware |
|---|---|---|---|
| Embedded NIMH setup `0x08000f2c`, parser `0x08000aa4`, dequeue `0x08000ce8`, release `0x08000d28` (candidate entries; exact extents unresolved) | Original container symbol retained; bytes verified via ELF section mapping | Disassembly exported; 20 framing/queue + 3 alternate queue + 4 receive-to-dispatch Linux cases passed with explicit MMIO/RTOS models | No reconstructed C++; original embedded names and ABI unresolved; no hardware validation |

Evidence: [report](../../../../../artifacts/mixer-13731/nimh-stm32-dice/analysis/receive-path.md),
[replay](replay.json),
[seal](validation.json).
DMA delivery, interrupts and scheduling remain modeled; no readiness promotions.
