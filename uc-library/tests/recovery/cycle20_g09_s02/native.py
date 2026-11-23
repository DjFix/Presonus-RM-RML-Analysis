"""Offline execution of the exact RM tap and its ELF-backed vtable slot."""
import hashlib
import json
import struct
import sys
from pathlib import Path

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import (
    UC_ARM_REG_FP, UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_SP,
)

ELF = Path(
    "/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/"
    "control10x20-after-4fed70d11/packeting/actual03-separate-ui-audio-batch08/"
    "snapshot/rootfs/RML16AI_Rack_13731/home/root/mixer"
)
ELF_SHA256 = "9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07"
CLASS_NAME = "FXComponent"
NAME = f"_ZN8Presonus5Mixer{len(CLASS_NAME)}{CLASS_NAME}3tapEv"
VTABLE = f"_ZTVN8Presonus5Mixer{len(CLASS_NAME)}{CLASS_NAME}E"
ADDRESS = 0x3c934
TABLE = 0x16fc38
TABLE_SLOT_OFFSET = 80


def digest(data):
    return hashlib.sha256(data).hexdigest()


def bound_symbol(elf, raw, name, address, size, section_name, expected_sha):
    symbols = elf.get_section_by_name(".symtab").get_symbol_by_name(name)
    assert len(symbols) == 1, name
    symbol = symbols[0]
    assert (symbol["st_value"], symbol["st_size"]) == (address, size), name
    section = elf.get_section(symbol["st_shndx"])
    delta = address - section["sh_addr"]
    assert section.name == section_name and 0 <= delta <= section["sh_size"] - size
    offset = section["sh_offset"] + delta
    data = raw[offset:offset + size]
    assert digest(data) == expected_sha, name
    return data, {
        "mangled": name, "address": address, "size": size, "section": section.name,
        "section_index": symbol["st_shndx"], "file_offset": offset,
        "sha256": expected_sha,
    }


def generate():
    raw = ELF.read_bytes()
    assert digest(raw) == ELF_SHA256
    with ELF.open("rb") as source:
        elf = ELFFile(source)
        body, body_range = bound_symbol(
            elf, raw, NAME, ADDRESS, 16, ".text",
            "60cf0e8b51daf6a0ce5a5eea619d9a3e219bccf7fa26c553983e5baf3012cfad",
        )
        table, table_range = bound_symbol(
            elf, raw, VTABLE, TABLE, 116, ".rodata", "62096bd7e53a5e14a047fd224980965b82406bf07da07e6073bf0d0c6c400a95",
        )
        for name in (".rel.dyn", ".rel.plt"):
            assert all(rel["r_offset"] != TABLE + TABLE_SLOT_OFFSET
                       for rel in elf.get_section_by_name(name).iter_relocations())
    assert struct.unpack_from("<I", table, TABLE_SLOT_OFFSET)[0] == ADDRESS
    assert body_range["section_index"] == 12

    cases = []
    for route in (0, 1):
        for seed in range(4):
            entry, end, stack, receiver = 0x810000, 0x810008, 0x820f00, 0x830100 + seed * 128
            machine = Uc(UC_ARCH_ARM, UC_MODE_ARM)
            for page in {ADDRESS & ~4095, TABLE & ~4095, entry, stack & ~4095, receiver & ~4095}:
                machine.mem_map(page, 4096)
            machine.mem_write(ADDRESS, body)
            machine.mem_write(TABLE, table)
            # Synthetic caller helper: ldr ip,[r0]; ldr pc,[ip,#72].
            # ELF table address point follows offset-to-top and RTTI words.
            machine.mem_write(entry, struct.pack("<II", 0xE590C000, 0xE59CF048))
            before = struct.pack("<I", TABLE + 8) + bytes([0x5A ^ seed]) * 60
            machine.mem_write(receiver, before)
            machine.reg_write(UC_ARM_REG_R0, receiver)
            machine.reg_write(UC_ARM_REG_SP, stack)
            machine.reg_write(UC_ARM_REG_LR, end)
            machine.reg_write(UC_ARM_REG_FP, 0x12345678 + seed)
            instructions, writes = [], []

            def instruction(_uc, addr, _size, _user):
                instructions.append(addr)

            def write(_uc, _access, addr, size, _value, _user):
                writes.append((addr, size))

            machine.hook_add(UC_HOOK_CODE, instruction)
            machine.hook_add(UC_HOOK_MEM_WRITE, write)
            machine.emu_start(entry if route else ADDRESS, end, count=12)
            assert machine.reg_read(UC_ARM_REG_PC) == end
            assert machine.reg_read(UC_ARM_REG_SP) == stack
            assert machine.reg_read(UC_ARM_REG_FP) == 0x12345678 + seed
            assert machine.reg_read(UC_ARM_REG_R0) == receiver
            assert instructions == ([entry, entry + 4] if route else []) + list(range(ADDRESS, ADDRESS + 16, 4))
            assert sorted(writes) == [(address, 4) for address in range(stack - 16, stack, 4)]
            unchanged = (bytes(machine.mem_read(receiver, len(before))) == before
                         and bytes(machine.mem_read(TABLE, len(table))) == table)
            assert unchanged
            cases.append({
                "input": [route, seed], "expected": int(unchanged),
                "r0_after": receiver, "instructions": instructions,
                "stack_write_addresses": sorted(address for address, _ in writes),
            })
    return {
        "elf_sha256": ELF_SHA256, "ranges": [body_range], "vtable": table_range,
        "vtable_slot_offset": TABLE_SLOT_OFFSET, "cases": cases,
    }


if __name__ == "__main__":
    Path(sys.argv[1]).write_text(json.dumps(generate(), indent=2) + "\n")
