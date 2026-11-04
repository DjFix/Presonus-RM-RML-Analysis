# EFM32 faderboard: application, protocol and boot boundary

Canonical hardware knowledge independent of the software release used to observe it.

## Physical and memory identification

Photo evidence appears to show **EFM32ZG222**; the full flash-size suffix is unreadable. Cortex-M0+ instruction/vector and EFM32ZG peripheral-map evidence corroborate the family, not exact flash capacity.

| Region / peripheral | Observation |
|---|---|
| Application | `[0x1000,0x3f70)`, 12,144 bytes |
| Missing boot region | `[0,0x1000)` absent from the application export |
| Initial stack / reset | `0x200008d0` / `0x11dd` |
| Vector relocation | VTOR set to `0x1000` |
| GPIO / I2C0 | `0x40006000` / `0x4000a000` |
| TIMER0 / TIMER1 | `0x40010000` / `0x40010400` |
| ADC0 / CMU / MSC | `0x40002000` / `0x400c8000` / `0x400c0000` |

Exact application hash is `b87a39cea8ff234c0cca785a7c5433e4ff729d365b56fca05b3023caa3aa53b6`; it is nested in outer surface panel bytes at `+0x9e40`. Five logical I2C targets and a four-channel wildcard selector are software observations, not proof of physical board/fader count. The same payload was absent from the inspected primary mixer and 17 mixer archive members; shared fader-related host classes do not negate that bounded result.

## Receive and command model

Normal path: I2C IRQ `0x1d34` → receive FSM `0x1518` → wrapper `0x13ac` → checksum validation `0x2a84` → dispatcher `0x2230`. Packet is `[destination,command,length,payload...,a,b]`. Normal context is `0x200001d8`, packet RAM `0x20000144`, bank zero. Destination high nibble matches board ID or broadcast `0xf`; low nibble selects a channel, with `0xf` selecting `[0,4)`. Selectors 4..14 are not rejected before helpers; malformed-input behavior is not validated.

| Commands (low seven bits) | Reviewed behavior |
|---|---|
| `0x11` | Control/reinitialization; read bit ignored |
| `0x12..0x1f`, `0x27` | Default return in reviewed application table |
| `0x20,0x21,0x22,0x23,0x28` | Fixed RAM-context parameter reads/writes |
| `0x24` | Sets control flag `0x200001ce`; read bit ignored |
| `0x25` / query `0xa5` | Fixed flash version byte at `0x3e28`, value `0x1b` |
| `0x26` | Flag `0x20000378` → persistence-like helper → AIRCR reset request |
| `0x29,0x2a` | Low-byte reads of fixed RAM words; write no-op |

Query bit `0x80` is not a universal read-only modifier: `0x91`, `0xa4`, `0xa6` retain control side effects. No reviewed normal-table command takes a caller-selected flash address and length. That does not prove all indirect/malformed paths or the absent bootloader lack read access.

## Update and validation findings

Panel query bytes are `00 a5 00 a5 4b`; control bytes `00 26 00 26 4c`. Observed update header is `00 27 09 1b 70 2f 00 00 dc 26 90 2a a8 fb`. CRC uses reflected `0xedb88320`, initial all ones and final complement. Checks use `a=(a+x)%255`, `b=(b+a)%255`. These bytes describe offline findings, not commands executed against hardware.

Nested-app checks include 5,632 checksum and 8,192 command25 full-packet native/Thumb comparisons; 17 portable undersized-buffer checks have their own scope. Other table handlers, peripheral behavior and the entire outer updater are not established by those tests.

## Bootloader and open questions

The original bootloader is **not acquired**. No demonstrated arbitrary flash/bootloader dump command exists in the inspected evidence. Command `0x27` is default-return in the normal app; its actual update receiver is absent. Reset landing and `0xfe` status meaning remain unresolved. Stock Silicon Labs AN0003 is UART/XMODEM with a `0x800` application boundary; it is not identified as the PreSonus I2C loader with this observed `0x1000` application base.

Exact part suffix, motor-driver wiring, ADC position/touch origin, timer/PWM pin assignment, persistence semantics, physical board count and full boot/flash behavior remain open. No hardware read, reset, erase, programming or debug unlock was performed.

## Sources and detailed evidence

- [Fader](<../../../evidence/recovery/2026-10-27/efm32-faders/REPORT.md>)
- [Protocol](<../../../evidence/recovery/2026-10-27/efm32-update-protocol/PROTOCOL.md>)
- [Panel protocol](<../../../evidence/recovery/2026-10-27/efm-reconstruction/panel/PANEL_PROTOCOL.md>)
- [Readback](<../../../evidence/recovery/2026-10-27/efm-reconstruction/review/READBACK_REVIEW.md>)

[System architecture and discovery workflow](<../README.md>)
