# NIMH STM32 SPI receive path — offline phase 02

Validated locally on VM101, 2026-10-28. All new paths use the physical checkout
`/home/rs/projects/opencs/ai-line-analysis`. The Mac-style `/Users/.../Presonus-RM-RML-Analysis`
path resolves to that checkout through a symlink. Historical proof paths were preserved.

Input: mixer 13731, embedded `_ZL13nimh_arm_code`, 216908 bytes.
The blob was compared byte-for-byte to its SHA-256-bound ELF symbol section/range.
See [source bindings](../../../../evidence/mixer-13731/nimh-stm32-dice/jobs/spi-rx-02/source-bindings.json) for exact original identity and document hashes.
Embedded routine names below are analytical descriptions; original embedded symbols
and exact routine extents remain unavailable.

## Native path

SPI1 data register -> DMA1 channel 2 -> 1024-byte circular buffer -> parser ->
selected packet queue -> native dequeue -> command dispatcher -> native release.

| Stage | Address/evidence |
|---|---|
| Transport setup | `0x08000f2c` |
| SPI control writes | `0x40013000 = 0x151`; `0x40013004 = 1` |
| RX DMA setup | CCR `0x4002001c = 0xaf`, CNDTR `0x40020020 = 1024`, peripheral `0x40020024 = 0x4001300c`, memory `0x40020028 = 0x2000cd14` |
| RX DMA descriptor | `0x2000ccd4`; callback pointer `0x08000c4d` |
| Periodic alarm callback | pointer `0x08000c49`; actual scheduling modeled |
| Both callback trampolines | branch to `0x08000aa4` |
| Parser state | `0x2000d114`; selected queue pointer `0x2000d118`; byte count `0x2000d11c`; output pointer `0x2000d120`; consumed DMA index `0x2000d124` |
| Ordinary command queue | `0x2000b480`, eight slots, mask 7; seven committed packets usable |
| Command `0x15` queue | `0x2000c4b8` |
| Commands above `0x3f` queue | `0x2000bc9c` |
| Ordinary dequeue / release | `0x08000ce8` / `0x08000d28` |
| Dispatcher loop | `0x080014a2` |

The DMA driver executes native register programming against mapped RAM. Control
`0xaf` selects circular, incrementing-memory reception with interrupt enables.
The exact physical timing, interrupt delivery and eCos synchronization are not executed.

The parser derives the producer index from `1024 - CNDTR`, saves the consumer index,
and handles wrap modulo 1024. `f0` begins/restarts recognition while awaiting a command.
`f8` resets that recognition state. Once copying payload, bytes are copied until `f7`
or the 255-byte limit; an internal `f8` is retained in the tested payload.
Each queue slot is 256 bytes: up to 255 packet bytes and a length at offset 255.
Publication advances the producer index and calls the wake boundary when configured.
Queue full increments offset `+0xc`; oversized frames increment `+0x10`.
These counters were asserted for the ordinary queue.

## Linux replay

[Replay results](../../../../evidence/mixer-13731/nimh-stm32-dice/jobs/spi-rx-02/replay.json): **20 framing/queue cases, three alternate queue cases,
four receive-to-dispatch cases**, all passed. Native initialization precedes every case.
Domains include every split of a five-byte rate command, bytewise delivery, noise,
two frames per delivery, incomplete frames, wrap near the end of DMA RAM, queue full,
a 255-byte packet, oversized-frame recovery, command-dependent queue selection,
and `f8` inside a payload.

The four receive-to-dispatch cases execute native framing, publication, dequeue,
rate-command dispatch and release. Each captures ACK `f0 11 01 f7`, verifies pending
rate state `01 01`, and confirms the ordinary queue was released. The second dequeue
entry is the stopping point. SDK readiness is supplied and TX enqueue is captured.

GPIO setup, interrupt registration, alarm/time APIs, semaphore operations and
scheduler locks are explicit boundary models. The initializer's zero-fill helper
is modeled with its byte-fill semantics. DMA arrivals are injected into the actual
configured buffer and CNDTR; this is not a peripheral-cycle or concurrent RTOS model.
A full unseen DMA revolution cannot be detected from a modulo index alone; overrun
timing and callback interleavings remain unvalidated.

The first alternate-queue fixture used an incorrectly calculated address and failed.
It was corrected from the native literal arithmetic; `replay-03.log` is retained,
and `replay-04.log` records the final passing run.

## Architectural source and status

The local `doc/DICE_III_User_Guide/TCD30xx - Firmware Development.pdf` describes
application APIs above HAL/peripheral drivers and eCos scheduling (pages 1–2).
That layering guides the boundaries here. Its DICE peripheral addresses do not
establish STM32 register addresses. No CS18/RM DICE firmware was loaded or compared.

Bytes: verified against original host ELF. Native disassembly: exported analysis.
Behavior: bounded original-instruction Linux replay. Compiled reconstructed C++,
original embedded symbol identities, ABI fidelity, concurrency, physical SPI/DMA,
clock completion and hardware interoperability: unresolved/not validated.
No production sources, readiness ledgers or device programming were changed.
