"""Observe each sealed MeterControl ARM constructor directly."""
import hashlib
import io
import json
from pathlib import Path
import struct

from elftools.elf.elffile import ELFFile
from unicorn import UC_ARCH_ARM, UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE, UC_MODE_ARM, Uc
from unicorn.arm_const import (
    UC_ARM_REG_CPSR, UC_ARM_REG_FP, UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0,
    UC_ARM_REG_R1, UC_ARM_REG_R4, UC_ARM_REG_SP,
)

TEST = Path(__file__).resolve().parent
TASK = TEST.name
PROJECT = Path("/home/rs/projects/opencs/ai-line-analysis")
PACKET = PROJECT / "temp/recovery-work/rolling-c001-20261124/packeting/sqlite-cycle02/meter_worker07/packet/tasks" / TASK / "CONTEXT.json"
TAGS = (-2147483648, -257, -1, 0, 255, 2147483647)
VTABLE = "_ZTVN8Presonus5Panel12MeterControlE"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def read_original(original, literal):
    path = PROJECT / original["elf_path"]
    raw = path.read_bytes()
    assert digest(raw) == original["elf"]
    elf = ELFFile(io.BytesIO(raw))
    assert elf.little_endian and elf["e_machine"] == "EM_ARM"
    symtab = elf.get_section_by_name(".symtab")
    symbol, = symtab.get_symbol_by_name(original["mangled"])
    assert symbol["st_info"]["type"] == "STT_FUNC"
    index, address, size = (symbol[key] for key in ("st_shndx", "st_value", "st_size"))
    assert (index, address, size) == (original["section"], original["address"], original["size"])
    section = elf.get_section(index)
    assert section.name == original["section_name"]
    relative = address - section["sh_addr"]
    assert 0 <= relative <= section["sh_size"] - size
    offset = section["sh_offset"] + relative
    body = raw[offset:offset + size]
    assert offset == original["file_offset"]
    assert digest(body) == original["range_sha256"] and body.hex() == original["range_hex"]
    table, = symtab.get_symbol_by_name(VTABLE)
    assert table["st_info"]["type"] == "STT_OBJECT" and table["st_size"] >= 12
    assert table["st_value"] == literal["original_vtable_address"]
    address_point, = struct.unpack_from("<I", body, size - 4)
    assert address_point == literal["address_point"] == table["st_value"] + 8
    return body, address_point


def execute(body, code, address_point, index, tag):
    arena, stack, stop = 0x100000, 0x200000, 0x300000
    receiver = arena + 0x100 + 0x40 * index
    sp = stack + 0x800
    sentinel = bytes((17 * n + 31 * index) & 255 for n in range(4096))
    emu = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    emu.mem_map(code & ~0xfff, 0x2000)
    emu.mem_map(arena, 0x1000)
    emu.mem_map(stack, 0x1000)
    emu.mem_write(code, body)
    emu.mem_write(arena, sentinel)
    emu.mem_write(stack, sentinel)
    registers = {UC_ARM_REG_CPSR: 0x60000010, UC_ARM_REG_R0: receiver,
                 UC_ARM_REG_R1: tag & 0xffffffff, UC_ARM_REG_R4: 0x124897,
                 UC_ARM_REG_FP: 0x1A53, UC_ARM_REG_SP: sp, UC_ARM_REG_LR: stop}
    for register, value in registers.items():
        emu.reg_write(register, value)
    instructions, reads, writes = [], [], []
    emu.hook_add(UC_HOOK_CODE, lambda _, address, size, data: instructions.append(address))
    emu.hook_add(UC_HOOK_MEM_READ, lambda _, access, address, size, value, data:
                 reads.append([address, size]))
    emu.hook_add(UC_HOOK_MEM_WRITE, lambda _, access, address, size, value, data:
                 writes.append([address, size, value & 0xffffffff]))
    emu.emu_start(code, stop, count=18)
    assert emu.reg_read(UC_ARM_REG_PC) == stop
    assert instructions == list(range(code, code + len(body) - 4, 4))
    for register, value in registers.items():
        if register == UC_ARM_REG_R1:
            continue
        assert emu.reg_read(register) == value
    assert sorted(reads) == sorted([[code + len(body) - 4, 4], *[
        [address, 4] for address in range(sp - 16, sp - 4, 4)]])
    assert sorted((addr, size) for addr, size, _ in writes) == [
        (addr, 4) for addr in (*range(receiver, receiver + 40, 4), *range(sp - 16, sp, 4))]
    before = receiver - arena
    words = struct.unpack("<IiIIIIiIII", emu.mem_read(receiver, 40))
    assert words == (address_point, -1, 0, 0, 0, 0, tag, 0, 0, 0)
    arena_after = bytes(emu.mem_read(arena, 4096))
    assert arena_after[:before] == sentinel[:before]
    assert arena_after[before + 40:] == sentinel[before + 40:]
    stack_after = bytes(emu.mem_read(stack, 4096))
    assert stack_after[:0x800 - 16] == sentinel[:0x800 - 16]
    assert stack_after[0x800:] == sentinel[0x800:]
    return dict(receiver=receiver, tag=tag, receiver_words=words,
                instructions=instructions, reads=reads, writes=writes)


def generate():
    packet = json.loads(PACKET.read_text())
    binding, = packet["task"]["review"]["evidence"]
    source_evidence = (PROJECT / binding["path"]).read_bytes()
    assert digest(source_evidence) == binding["sha256"]
    verified = json.loads(source_evidence)["native"]
    observations = []
    for entry, verification in zip(packet["originals"], verified, strict=True):
        original = entry["original"]
        assert original == verification["original"]
        site, = verification["site_evidence"]
        literal = dict(original_vtable_address=site["value"] - 8, address_point=site["value"])
        body, address_point = read_original(original, literal)
        observations.append(dict(original=original, literal=literal, cases=[
            execute(body, original["address"], address_point, index, tag)
            for index, tag in enumerate(TAGS)]))
    return observations


if __name__ == "__main__":
    print(json.dumps(generate(), indent=2))
