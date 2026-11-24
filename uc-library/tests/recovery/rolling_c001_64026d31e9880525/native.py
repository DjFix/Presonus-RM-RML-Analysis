"""Execute the exact original ARM default preset hook with sentinel memory."""
import hashlib
import io
import json
from pathlib import Path
import struct

from elftools.elf.elffile import ELFFile
from unicorn import UC_ARCH_ARM, UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE, UC_MODE_ARM, Uc
from unicorn.arm_const import (
    UC_ARM_REG_CPSR, UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_SP,
    UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_R4,
    UC_ARM_REG_R5, UC_ARM_REG_R6, UC_ARM_REG_R7, UC_ARM_REG_R8, UC_ARM_REG_R9,
    UC_ARM_REG_R10, UC_ARM_REG_R11,
)

ELF = Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling-c001-20261124/packeting/next59/snapshot/rootfs/CS18_v13840/home/root/surface')
ORIGINAL = {'elf_sha256': '304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0', 'firmware': 'CS18AI surface 13840', 'role': 'client', 'mangled': '_ZN8Presonus14IPresetHandler10savePresetENS0_10PresetTypeEiRN4Core13CStringBufferILi128EEEPKci', 'address': 397340, 'size': 16, 'section': 12}
VTABLES = {'_ZTVN8Presonus14IPresetHandlerE': (36, 1681820), '_ZTVN8Presonus20MixerClientComponentE': (172, 2052860), '_ZTVN8Presonus24MixerClientComponentBaseE': (168, 1680304)}
REGS = (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_R4,
        UC_ARM_REG_R5, UC_ARM_REG_R6, UC_ARM_REG_R7, UC_ARM_REG_R8, UC_ARM_REG_R9,
        UC_ARM_REG_R10, UC_ARM_REG_R11, UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_CPSR)
CASES = (
    (0, 0, 0, 65, 0, 0, 0),
    (1, 1, -1, 90, 127, 1, 1),
    (6, -1, 9, 75, 4, 0, 1),
    (7, -2147483648, 2147483647, 68, 1, 1, 0),
    (8, 2147483647, -2147483648, 81, 64, 0, 1),
    (-1, 44, -7, 72, 7, 1, 1),
    (2147483647, -3, 8, 87, 55, 1, 0),
)
NAME = b"Preset\0"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_original():
    raw = ELF.read_bytes()
    assert digest(raw) == ORIGINAL["elf_sha256"]
    elf = ELFFile(io.BytesIO(raw))
    assert elf.little_endian and elf["e_machine"] == "EM_ARM"
    syms = elf.get_section_by_name(".symtab")
    target, = syms.get_symbol_by_name(ORIGINAL["mangled"])
    assert target["st_info"]["type"] == "STT_FUNC"
    assert target["st_shndx"] == ORIGINAL["section"]
    assert target["st_value"] == ORIGINAL["address"]
    assert target["st_size"] == ORIGINAL["size"]
    section = elf.get_section(target["st_shndx"])
    assert section.name == ".text"
    assert section["sh_addr"] <= target["st_value"]
    assert target["st_value"] + target["st_size"] <= section["sh_addr"] + section["sh_size"]
    offset = section["sh_offset"] + target["st_value"] - section["sh_addr"]
    body = raw[offset:offset + target["st_size"]]
    assert offset == 0x5901c
    assert digest(body) == "60cf0e8b51daf6a0ce5a5eea619d9a3e219bccf7fa26c553983e5baf3012cfad"
    tables = []
    for name, (slot_offset, address) in VTABLES.items():
        table, = syms.get_symbol_by_name(name)
        table_section = elf.get_section(table["st_shndx"])
        assert slot_offset + 4 <= table["st_size"]
        assert table["st_value"] + slot_offset == address
        delta = address - table_section["sh_addr"]
        assert 0 <= delta <= table_section["sh_size"] - 4
        table_offset = table_section["sh_offset"] + delta
        word, = struct.unpack_from("<I", raw, table_offset)
        assert word == target["st_value"]
        tables.append(dict(mangled=name, slot_offset=slot_offset, address=address,
                           file_offset=table_offset, word=word))
    return body, dict(**ORIGINAL, section_name=section.name, file_offset=offset,
                      byte_sha256=digest(body), bytes_hex=body.hex()), tables


def execute(body, params):
    preset, index, option, letter, length, choice, has_name = params
    code = ORIGINAL["address"]
    stop = 0x62000
    arena = 0x100000
    stack = 0x200000
    sp = stack + 0x800
    receiver = arena + 0x100 + 0x100 * choice
    buffer = arena + 0x300
    name = arena + 0x400
    buffer_bytes = bytearray([letter] * 128)
    buffer_bytes[length] = 0
    emu = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    emu.mem_map(code & ~0xFFF, 0x2000)
    emu.mem_map(arena, 0x1000)
    emu.mem_map(stack, 0x1000)
    emu.mem_write(code, body)
    emu.mem_write(arena, b"\x5a" * 0x1000)
    emu.mem_write(stack, b"\xa5" * 0x1000)
    emu.mem_write(buffer, bytes(buffer_bytes))
    emu.mem_write(name, NAME)
    emu.mem_write(sp, struct.pack("<Ii", name if has_name else 0, option))
    arena_before = bytes(emu.mem_read(arena, 0x1000))
    stack_before = bytes(emu.mem_read(stack, 0x1000))
    inputs = [receiver, preset & 0xFFFFFFFF, index & 0xFFFFFFFF, buffer,
              *[0x80004000 + i for i in range(8)], sp, stop, 0x60000010]
    emu.reg_write(UC_ARM_REG_CPSR, inputs[-1])
    for reg, value in zip(REGS, inputs):
        emu.reg_write(reg, value)
    reads, writes, pcs = [], [], []
    emu.hook_add(UC_HOOK_CODE, lambda _, address, size, _data: pcs.append(address))
    emu.hook_add(UC_HOOK_MEM_READ, lambda _, access, address, size, value, data:
                 reads.append([address, size]))
    emu.hook_add(UC_HOOK_MEM_WRITE, lambda _, access, address, size, value, data:
                 writes.append([address, size, value]))
    emu.emu_start(code, stop, count=5)
    outputs = [emu.reg_read(reg) for reg in REGS]
    assert emu.reg_read(UC_ARM_REG_PC) == stop
    assert pcs == list(range(code, code + len(body), 4))
    assert outputs == inputs
    assert all(sp - 16 <= address and address + size <= sp
               for address, size in reads)
    assert sorted((address, size) for address, size, _ in writes) == [
        (address, 4) for address in range(sp - 16, sp, 4)]
    assert bytes(emu.mem_read(arena, 0x1000)) == arena_before
    stack_after = bytes(emu.mem_read(stack, 0x1000))
    frame = sp - stack
    assert stack_after[:frame - 16] == stack_before[:frame - 16]
    assert stack_after[frame:] == stack_before[frame:]
    # r3 carries the buffer. The opaque register/stack words deliberately cover
    # distinct values without making any claim about the exact firmware ABI.
    return dict(inputs=list(params), registers_before=inputs, registers_after=outputs,
                instruction_addresses=pcs, memory_reads=reads, memory_writes=writes,
                buffer_after=list(emu.mem_read(buffer, 128)),
                name_after=list(emu.mem_read(name, len(NAME))),
                npc=stop, no_nonframe_writes=True)


def generate():
    body, original_range, tables = read_original()
    return dict(original_range=original_range, vtable_words=tables,
                cases=[execute(body, params) for params in CASES])


if __name__ == "__main__":
    print(json.dumps(generate(), sort_keys=True, indent=2))
