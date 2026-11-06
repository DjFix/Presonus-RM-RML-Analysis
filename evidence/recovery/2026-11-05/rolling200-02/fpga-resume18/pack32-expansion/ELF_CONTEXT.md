# ELF context

Full target ranges verified against exact source ELF. Static evidence; C++ return/layout remains unresolved.
One-hop calls/references only. Neighbor bodies require explicit expansion. Pseudocode is unvalidated.

## pack32(unsigned int, unsigned char*)

ELF `9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07`; version `RM/RML mixer 13731`; `server`; original `_Z6pack32jPh`; address `0xa468c`; size 76; section .text; SHA256 `d84b5e489320a5a313d93284642889436b2b26497a908712985c9099a77a4345`
Original ELF path: `rootfs/RML16AI_Rack_13731/home/root/mixer`; file offset `0x9c68c`. Exact full range is offset + size; includes any literal pool bytes.

```asm
000a468c  0dc0a0e1  mov ip, sp
000a4690  30d82de9  push {r4, r5, fp, ip, lr, pc}
000a4694  a03ca0e1  lsr r3, r0, #0x19
000a4698  0140a0e1  mov r4, r1
000a469c  0130c4e4  strb r3, [r4], #1
000a46a0  2029a0e1  lsr r2, r0, #0x12
000a46a4  a035a0e1  lsr r3, r0, #0xb
000a46a8  04b04ce2  sub fp, ip, #4
000a46ac  20c2a0e1  lsr ip, r0, #4
000a46b0  015084e2  add r5, r4, #1
000a46b4  7f2002e2  and r2, r2, #0x7f
000a46b8  7f3003e2  and r3, r3, #0x7f
000a46bc  7fc00ce2  and ip, ip, #0x7f
000a46c0  0f0000e2  and r0, r0, #0xf
000a46c4  0120c1e5  strb r2, [r1, #1]
000a46c8  0130c4e5  strb r3, [r4, #1]
000a46cc  0200c5e5  strb r0, [r5, #2]
000a46d0  01c0c5e5  strb ip, [r5, #1]
000a46d4  30a89de8  ldm sp, {r4, r5, fp, sp, pc}
```

### Unvalidated pseudocode — declarations are not evidence

```text
// UNVALIDATED DECOMPILER OUTPUT. Not buildable C++ or an ABI declaration.
// pack32(unsigned int, unsigned char*)
// Symbol _Z6pack32jPh address=0xa468c
void pack32(unsigned int arg_0, char *arg_1)
{
    unsigned int v0;  // r4
    unsigned int idx;  // r5

    v0 = arg_1 + 1;
    *arg_1 = arg_0 >> 25;
    idx = v0 + 1;
    arg_1[1] = (char)(arg_0 >> 18) & 127;
    *(char *)(v0 + 1) = (char)(arg_0 >> 11) & 127;
    *(char *)(idx + 2) = (char)arg_0 & 15;
    *(char *)(idx + 1) = (char)(arg_0 >> 4) & 127;
    return;
}


```

## Typed relationships

- ELF_MEMORY_ACCESS: `pack32(unsigned int, unsigned char*)` → `r3, [r4], #1` at 0xa469c; {"base_register": "r4", "displacement": 0, "elf_sha256": "9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07", "firmware": "RM/RML mixer 13731", "index_register": null, "instruction": "strb", "instruction_address": 673436, "interpretation": "observed explicit memory operand; original class fields/types/ownership unresolved", "operands": "r3, [r4], #1", "scale": 1, "shift_type": 0, "shift_value": 0}
- ELF_MEMORY_ACCESS: `pack32(unsigned int, unsigned char*)` → `r2, [r1, #1]` at 0xa46c4; {"base_register": "r1", "displacement": 1, "elf_sha256": "9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07", "firmware": "RM/RML mixer 13731", "index_register": null, "instruction": "strb", "instruction_address": 673476, "interpretation": "observed explicit memory operand; original class fields/types/ownership unresolved", "operands": "r2, [r1, #1]", "scale": 1, "shift_type": 0, "shift_value": 0}
- ELF_MEMORY_ACCESS: `pack32(unsigned int, unsigned char*)` → `r3, [r4, #1]` at 0xa46c8; {"base_register": "r4", "displacement": 1, "elf_sha256": "9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07", "firmware": "RM/RML mixer 13731", "index_register": null, "instruction": "strb", "instruction_address": 673480, "interpretation": "observed explicit memory operand; original class fields/types/ownership unresolved", "operands": "r3, [r4, #1]", "scale": 1, "shift_type": 0, "shift_value": 0}
- ELF_MEMORY_ACCESS: `pack32(unsigned int, unsigned char*)` → `r0, [r5, #2]` at 0xa46cc; {"base_register": "r5", "displacement": 2, "elf_sha256": "9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07", "firmware": "RM/RML mixer 13731", "index_register": null, "instruction": "strb", "instruction_address": 673484, "interpretation": "observed explicit memory operand; original class fields/types/ownership unresolved", "operands": "r0, [r5, #2]", "scale": 1, "shift_type": 0, "shift_value": 0}
- ELF_MEMORY_ACCESS: `pack32(unsigned int, unsigned char*)` → `ip, [r5, #1]` at 0xa46d0; {"base_register": "r5", "displacement": 1, "elf_sha256": "9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07", "firmware": "RM/RML mixer 13731", "index_register": null, "instruction": "strb", "instruction_address": 673488, "interpretation": "observed explicit memory operand; original class fields/types/ownership unresolved", "operands": "ip, [r5, #1]", "scale": 1, "shift_type": 0, "shift_value": 0}
- ELF_CALLS: `Presonus::NOAA::TCardFPGAUpdater::update()` → `pack32(unsigned int, unsigned char*)` at 0xa5318; {"instruction": "bl", "target_address": 673420}
- ELF_CALLS: `Presonus::NOAA::TCard::programSerialReset()` → `pack32(unsigned int, unsigned char*)` at 0x9dad8; {"instruction": "bl", "target_address": 673420}
- ELF_CALLS: `Presonus::NOAA::TCard::programSerialReset()` → `pack32(unsigned int, unsigned char*)` at 0x9dae4; {"instruction": "bl", "target_address": 673420}
- ELF_CALLS: `Presonus::NOAA::TCard::programSerialReset()` → `pack32(unsigned int, unsigned char*)` at 0x9dbc4; {"instruction": "bl", "target_address": 673420}

## External-source bindings — do not reconstruct these providers from firmware


## Bound raw data

{}
