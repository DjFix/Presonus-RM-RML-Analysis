"""Observe the exact offline ARM entry point with synthetic receiver storage."""

import argparse
import hashlib
import json
from pathlib import Path
import random
import struct

import elftools
from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import Uc, UC_ARCH_ARM, UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE, UC_MODE_ARM
from unicorn.arm_const import (
    UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1,
    UC_ARM_REG_R2, UC_ARM_REG_R11, UC_ARM_REG_R12, UC_ARM_REG_SP,
)

ELF_HASH = "9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07"
SYMBOL = "_ZNK8Presonus5Panel23WolverinePanelRegistrar7getTagsEiRi"
ADDRESS = 504144
SIZE = 20
SECTION = 12
FILE_OFFSET = 471376
RANGE_HASH = "52014dc35dcb0a43c02dfc6dec01fdeeafcc563ba02addaa7295df3a7a57226c"


def observe(elf_path):
    assert hashlib.sha256(elf_path.read_bytes()).hexdigest() == ELF_HASH
    with elf_path.open("rb") as stream:
        elf = ELFFile(stream)
        assert elf["e_machine"] == "EM_ARM" and elf.little_endian
        matches = elf.get_section_by_name(".symtab").get_symbol_by_name(SYMBOL)
        assert len(matches) == 1
        symbol = matches[0]
        assert (symbol["st_value"], symbol["st_size"], symbol["st_shndx"]) == (
            ADDRESS, SIZE, SECTION
        )
        section = elf.get_section(SECTION)
        assert section.name == ".text"
        relative_address = ADDRESS - section["sh_addr"]
        assert 0 <= relative_address <= section["sh_size"] - SIZE
        offset = section["sh_offset"] + relative_address
        assert offset == FILE_OFFSET
        stream.seek(offset)
        body = stream.read(SIZE)
    assert hashlib.sha256(body).hexdigest() == RANGE_HASH

    randomizer = random.Random(203)
    groups = [-2147483648, -2, -1, *range(17), 255, 2147483647]
    cases = []
    for index, group in enumerate(groups):
        for count in (-2147483648, -1, 0, 1, 2147483647):
            cases.append(run_case(body, group, count, index, randomizer))
    return {
        "elf_sha256": ELF_HASH, "mangled": SYMBOL, "address": ADDRESS,
        "size": SIZE, "section": SECTION, "section_name": ".text",
        "file_offset": offset, "range_sha256": RANGE_HASH,
        "unicorn_version": unicorn.__version__, "pyelftools_version": elftools.__version__,
        "cases": cases,
    }


def run_case(body, group, count, index, randomizer):
    machine = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    page = 4096
    data = 0x1000000
    stack = 0x2000000
    sp = stack + 2048
    receiver = data + (0x100 if index % 2 else 0x300)
    count_address = data + (0x700 if index % 2 else 0x900)
    stop = 0x3000000
    frame_pointer = 0x12345678
    machine.mem_map(ADDRESS & ~(page - 1), page)
    machine.mem_map(data, page)
    machine.mem_map(stack, page)
    machine.mem_map(stop, page)
    machine.mem_write(ADDRESS, body)
    canaries = bytearray(randomizer.randbytes(page))
    struct.pack_into("<i", canaries, count_address - data, count)
    machine.mem_write(data, bytes(canaries))
    for register, value in [
        (UC_ARM_REG_R0, receiver), (UC_ARM_REG_R1, group & 0xffffffff),
        (UC_ARM_REG_R2, count_address), (UC_ARM_REG_SP, sp),
        (UC_ARM_REG_R11, frame_pointer), (UC_ARM_REG_R12, 0xa5a5a5a5),
        (UC_ARM_REG_LR, stop),
    ]:
        machine.reg_write(register, value)
    instructions, reads, writes = [], [], []
    machine.hook_add(UC_HOOK_CODE, lambda _, address, size, __: instructions.append(address))
    machine.hook_add(UC_HOOK_MEM_READ, lambda _, __, address, size, value, ___: reads.append([address, size]))
    machine.hook_add(UC_HOOK_MEM_WRITE, lambda _, __, address, size, value, ___: writes.append([address, size, value]))
    machine.emu_start(ADDRESS, stop, count=16)
    assert machine.reg_read(UC_ARM_REG_PC) == stop
    assert machine.reg_read(UC_ARM_REG_SP) == sp
    assert machine.reg_read(UC_ARM_REG_R11) == frame_pointer
    assert instructions == list(range(ADDRESS, ADDRESS + SIZE, 4))
    assert all(sp - 16 <= address and address + size <= sp for address, size in reads)
    assert all(sp - 16 <= address and address + size <= sp for address, size, _ in writes)
    assert machine.mem_read(data, page) == canaries
    return {
        "group": group, "count_before": count,
        "count_after": struct.unpack("<i", machine.mem_read(count_address, 4))[0],
        "return_word": machine.reg_read(UC_ARM_REG_R0),
        "receiver": receiver, "count_address": count_address,
        "instructions": instructions, "stack_reads": reads, "stack_writes": writes,
        "application_writes": [], "external_calls": [],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("elf", type=Path)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    args.out.write_text(json.dumps(observe(args.elf), indent=2) + "\n")
