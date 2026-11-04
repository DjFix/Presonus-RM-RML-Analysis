from pathlib import Path
import hashlib,json,shutil,datetime
from elftools.elf.elffile import ELFFile
from capstone import *
root=Path(__file__).resolve().parents[3]
out=root/'evidence/recovery/2026-10-28/nimh-spi-rx'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
image=root/'evidence/recovery/2026-10-27/xmen-stm32/images/mixer-analysis/_ZL13nimh_arm_code.bin'
elf=root/'evidence/recovery/2026-10-27/xmen-stm32/inputs/mixer-13731.elf'
assert sha(elf)=='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
with elf.open('rb') as f:
 e=ELFFile(f);sym=next(s for s in e.get_section_by_name('.symtab').iter_symbols() if s.name=='_ZL13nimh_arm_code')
 section=e.get_section(sym['st_shndx']);offset=section['sh_offset']+sym['st_value']-section['sh_addr']
 f.seek(offset);assert f.read(sym['st_size'])==image.read_bytes()
 elf_binding=dict(path=str(elf.relative_to(root)),sha256=sha(elf),symbol=sym.name,address=hex(sym['st_value']),size=sym['st_size'],file_offset=hex(offset),section=section.name)
docs=json.loads((root/'evidence/recovery/2026-10-27/nimh-command-map/docs/sources.json').read_text())
for d in docs:assert sha(root/d['path'])==d['sha256']
(out/'source-bindings.json').write_text(json.dumps(dict(elf=elf_binding,image_sha256=sha(image),docs=docs),indent=2)+'\n')
md=Cs(CS_ARCH_ARM,CS_MODE_THUMB|CS_MODE_MCLASS);b=image.read_bytes();parts=[]
for lo,hi in [(0xaa4,0xc30),(0xc48,0xc50),(0xce8,0xd24),(0xd28,0xd3c),(0xf2c,0x10bc),(0x48d4,0x4956),(0x4988,0x4a02)]:
 parts.append('\n'.join(f'{i.address:08x}: {i.mnemonic:9} {i.op_str}' for i in md.disasm(b[lo:hi],0x08000000+lo)))
(out/'receive-path.thumb.txt').write_text('\n\n'.join(parts)+'\n')
for name in ['replay.py','seal.py']:shutil.copyfile(Path(__file__).parent/name,out/name)
report="""# NIMH STM32 SPI receive path — offline phase 02

Validated locally on VM101, 2026-10-28. All new paths use the physical checkout
`/home/rs/projects/opencs/ai-line-analysis`. The Mac-style `/Users/.../Presonus-RM-RML-Analysis`
path resolves to that checkout through a symlink. Historical proof paths were preserved.

Input: mixer 13731, embedded `_ZL13nimh_arm_code`, 216908 bytes.
The blob was compared byte-for-byte to its SHA-256-bound ELF symbol section/range.
See [source bindings](source-bindings.json) for exact original identity and document hashes.
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

[Replay results](replay.json): **20 framing/queue cases, three alternate queue cases,
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
"""
(out/'REPORT.md').write_text(report)
fragment="""
## NIMH STM32 SPI receive path — phase 02

Input `_ZL13nimh_arm_code` in mixer 13731, host ELF SHA-256
`9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07`;
blob SHA-256 `b0979352e18a1093051fc6118a47694773cb9240e88087eca03aaa2ffe0f5e17`.

| Binary/range | Catalogue / bytes | Analysis / behavioral status | C++ / ABI / hardware |
|---|---|---|---|
| Embedded NIMH setup `0x08000f2c`, parser `0x08000aa4`, dequeue `0x08000ce8`, release `0x08000d28` (candidate entries; exact extents unresolved) | Original container symbol retained; bytes verified via ELF section mapping | Disassembly exported; 20 framing/queue + 3 alternate queue + 4 receive-to-dispatch Linux cases passed with explicit MMIO/RTOS models | No reconstructed C++; original embedded names and ABI unresolved; no hardware validation |

Evidence: [report](../evidence/recovery/2026-10-28/nimh-spi-rx/REPORT.md),
[replay](../evidence/recovery/2026-10-28/nimh-spi-rx/replay.json),
[seal](../evidence/recovery/2026-10-28/nimh-spi-rx/validation.json).
DMA delivery, interrupts and scheduling remain modeled; no readiness promotions.
"""
(out/'tracker-fragment.md').write_text(fragment)
tracker=root/'uc-library/SYMBOLS.md'
if '## NIMH STM32 SPI receive path — phase 02' not in tracker.read_text():
 shutil.copyfile(tracker,out/'SYMBOLS-before.md')
 with tracker.open('a') as f:f.write(fragment)
r=json.loads((out/'replay.json').read_text())
assert r['tool_sha256']==sha(out/'replay.py')
assert len(r['cases'])==20 and len(r['alternate_queues'])==3 and len(r['end_to_end'])==4
artifacts={str(p.relative_to(root)):sha(p) for p in sorted(out.iterdir()) if p.is_file() and p.name!='validation.json'}
proof=dict(validated_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='passed-bounded-offline-native-replay',
 root=str(root),image_sha256=sha(image),elf=elf_binding,counts=dict(receive=20,alternate_queue=3,receive_to_dispatch=4),
 artifacts=artifacts,tracker_sha256=sha(tracker),reconstructed_cpp=0,hardware_actions=0)
(out/'validation.json').write_text(json.dumps(proof,indent=2)+'\n')
print('SEALED',len(artifacts),'artifacts; ELF bytes and eight documentation hashes verified; tracker updated')
