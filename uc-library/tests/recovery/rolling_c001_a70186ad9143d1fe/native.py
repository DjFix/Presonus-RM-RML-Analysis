"""Replay sealed ELF accessors against isolated synthetic ARM receivers."""
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

ORIGINS = [{'elf_sha256': '9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07', 'firmware': 'RM/RML mixer 13731', 'role': 'server', 'mangled': '_ZNK8Presonus9SLChannel17getColorParameterEv', 'address': 158752, 'size': 20, 'section': 12, 'byte_sha256': 'acec9493472e294bb95cdf87af83effef4d5d547d19acb27184d1b885c68544f', 'path': '/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling-c001-20261124/packeting/next59/snapshot/rootfs/RML16AI_Rack_13731/home/root/mixer', 'file_offset': 125984}, {'elf_sha256': '304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0', 'firmware': 'CS18AI surface 13840', 'role': 'client', 'mangled': '_ZNK8Presonus9SLChannel17getColorParameterEv', 'address': 873968, 'size': 20, 'section': 12, 'byte_sha256': 'acec9493472e294bb95cdf87af83effef4d5d547d19acb27184d1b885c68544f', 'path': '/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling-c001-20261124/packeting/next59/snapshot/rootfs/CS18_v13840/home/root/surface', 'file_offset': 841200}]
SLOT = 520
SETTER = False
REGS = (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_R4,
        UC_ARM_REG_R5, UC_ARM_REG_R6, UC_ARM_REG_R7, UC_ARM_REG_R8, UC_ARM_REG_R9,
        UC_ARM_REG_R10, UC_ARM_REG_R11, UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_CPSR)
CASES = ((0, 0), (1, 0), (2, 0), (1, 1), (0, 1), (2, 1), (0, 0))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_original(origin):
    raw = Path(origin["path"]).read_bytes()
    assert digest(raw) == origin["elf_sha256"]
    elf = ELFFile(io.BytesIO(raw))
    assert elf.little_endian and elf["e_machine"] == "EM_ARM"
    target, = elf.get_section_by_name(".symtab").get_symbol_by_name(origin["mangled"])
    assert target["st_info"]["type"] == "STT_FUNC"
    assert target["st_shndx"] == origin["section"]
    assert target["st_value"] == origin["address"]
    assert target["st_size"] == origin["size"]
    section = elf.get_section(origin["section"])
    displacement = origin["address"] - section["sh_addr"]
    assert section.name == ".text" and 0 <= displacement <= section["sh_size"] - origin["size"]
    offset = section["sh_offset"] + displacement
    assert offset == origin["file_offset"]
    body = raw[offset:offset + origin["size"]]
    assert digest(body) == origin["byte_sha256"]
    return body, dict(origin, bytes_hex=body.hex(), section_name=section.name)


def execute(body, addr, identity, instance):
    arena, stack, stop = 0x300000, 0x400000, 0x500000
    sp = stack + 0x800
    receiver = arena + 0x100 + 0x500 * instance
    pointers = (0, arena + 0xC00, arena + 0xD00)
    target = receiver + SLOT
    emu = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    for address in (addr & ~0xFFF, arena, stack):
        emu.mem_map(address, 0x1000)
    emu.mem_write(addr, body)
    emu.mem_write(arena, b"\x5a" * 0x1000)
    emu.mem_write(stack, b"\xa5" * 0x1000)
    emu.mem_write(target, struct.pack("<I", 0xBADC0DE if SETTER else pointers[identity]))
    before = bytearray(emu.mem_read(arena, 0x1000))
    expected = list((receiver, pointers[identity], *[0x123000+i for i in range(10)],
                     sp, stop, 0x60000010))
    emu.reg_write(UC_ARM_REG_CPSR, expected[-1])
    for reg, value in zip(REGS, expected):
        emu.reg_write(reg, value)
    reads, writes, pcs = [], [], []
    emu.hook_add(UC_HOOK_CODE, lambda _, address, size, data: pcs.append(address))
    emu.hook_add(UC_HOOK_MEM_READ, lambda _, kind, address, size, value, data:
                 reads.append([address, size]))
    emu.hook_add(UC_HOOK_MEM_WRITE, lambda _, kind, address, size, value, data:
                 writes.append([address, size, value]))
    emu.emu_start(addr, stop, count=6)
    assert emu.reg_read(UC_ARM_REG_PC) == stop
    assert pcs == list(range(addr, addr + len(body), 4))
    actual = [emu.reg_read(reg) for reg in REGS]
    outside_reads = [row for row in reads if not (sp - 16 <= row[0] < sp)]
    outside_writes = [row for row in writes if not (sp - 16 <= row[0] < sp)]
    assert sorted((address, size) for address, size, _ in writes if sp - 16 <= address < sp) == [
        (address, 4) for address in range(sp - 16, sp, 4)]
    if SETTER:
        assert not outside_reads and outside_writes == [[target, 4, pointers[identity]]]
        before[target-arena:target-arena+4] = struct.pack("<I", pointers[identity])
        result, = struct.unpack("<I", emu.mem_read(target, 4))
    else:
        assert outside_reads == [[target, 4]] and not outside_writes
        expected[0] = pointers[identity]
        result = actual[0]
    assert actual == expected and bytes(emu.mem_read(arena, 0x1000)) == before
    return dict(inputs=[identity, instance], result=[pointers.index(result)],
                pc_trace=pcs, reads=reads, writes=writes, registers_after=actual)


def generate():
    ranges, cases = [], []
    for origin in ORIGINS:
        body, verified = read_original(origin)
        ranges.append(verified)
        for identity, instance in CASES:
            case = execute(body, origin["address"], identity, instance)
            cases.append(dict(elf_sha256=origin["elf_sha256"], **case))
    return dict(ranges=ranges, cases=cases)


if __name__ == "__main__":
    print(json.dumps(generate(), sort_keys=True, indent=2))
