
## NIMH STM32 startup and command paths — phase 01

Original embedded object `_ZL13nimh_arm_code`, mixer 13731 ELF SHA-256
`9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07`,
image SHA-256 `b0979352e18a1093051fc6118a47694773cb9240e88087eca03aaa2ffe0f5e17`.
[Phase proof](../../history/legacy-validation-index/validation.json) and
[evidence index](../../history/legacy-validation-index/README.md).

| Scope | Byte identity | Analysis | Offline native validation | C++ / hardware |
| --- | --- | --- | --- | --- |
| Startup / memory | verified | eCos reset pattern, data/BSS/vector ranges | Bounded startup replay; hardware init/SVC hooked | pending |
| Host clock/rate packets | original ELF identities and ranges verified | 0x11 rate/link and 0x28 AVB source paths | 27 cases; libc/time/log/ACK/transport models | no new production C++ |
| STM32 commands | verified image | Dispatcher and SDK boundaries | 222 cases; 12 deferred-consumer cases | full scheduler/device behavior pending |
| NIMH mixer callback | verified image | CLI mix.gain pointer and external register write | 216 index/gain/error cases against RAM MMIO | FPGA/audio/timing pending |
| SDK / RTOS | verified image and source references | 124 CLI records, 24 SDK path strings; public eCos source pinned | exact TCAT eCos revision unresolved | no source/body equivalence promotion |

Embedded function labels are analysis identities, not original C/C++ symbols.
This phase follows local manual architecture and uses no CS18AI/RM firmware
mapping/comparison. Zero function promotions and zero hardware actions.
