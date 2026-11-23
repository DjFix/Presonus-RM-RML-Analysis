"""Execute each bound ARM default directly and through its ELF vtable slot."""

import argparse
import hashlib
import json
import struct
from pathlib import Path

import unicorn as uc
from elftools.elf.elffile import ELFFile
from unicorn import arm_const as arm

MANGLED = "_ZNK8Presonus13SLChannelBase17getSlowLinkParamsERN4Core6VectorIPNS1_8Portable9ParameterEEE"
VTABLE = "_ZTVN8Presonus13SLChannelBaseE"
BODY_SHA = "60cf0e8b51daf6a0ce5a5eea619d9a3e219bccf7fa26c553983e5baf3012cfad"
ORIGINALS = {
    "client": (
        "304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0",
        0x6111C, 0x5911C, 0x19A280,
        "02dde63d0b1b9e36b3a0e5f2a257c14be3801e42aa3f6539073ab810af967907",
    ),
    "server": (
        "9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07",
        0x123EC, 0xA3EC, 0x1590E0,
        "d7073d7d74ca916da634bc271a1767bc8b19a6038db57cc70a88d1382af6ded6",
    ),
}
RECEIVER, VECTOR, STACK, CALLER, STOP = 0x40000000, 0x40001000, 0x50000000, 0x71000000, 0x71000100
STACK_TOP = STACK + 0x800
SLOT = 80  # 88 from the ELF symbol, 80 from its +8 address point.
SHAPES = {"empty": [], "single": [0x40001100], "mixed": [0x40001140, 0, 0x40001100, 0x40001140]}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def checked_range(elf, name, address, size, expected_sha):
    row, = elf.get_section_by_name(".symtab").get_symbol_by_name(name)
    assert (row["st_value"], row["st_size"]) == (address, size)
    index = row["st_shndx"]
    section = elf.get_section(index)
    offset = address - section["sh_addr"]
    assert 0 <= offset and offset + size <= section["sh_size"]
    body = section.data()[offset:offset + size]
    assert sha(body) == expected_sha
    return body, {
        "mangled": name, "address": address, "size": size, "section": index,
        "section_name": section.name, "file_offset": section["sh_offset"] + offset,
        "sha256": expected_sha,
    }


def replay(code, body, table, table_address, route, shape):
    machine = uc.Uc(uc.UC_ARCH_ARM, uc.UC_MODE_ARM)
    pages = {RECEIVER, VECTOR, STACK, CALLER}
    for address, size in ((code, len(body)), (table_address, len(table))):
        pages.update(range(address & ~4095, (address + size + 4095) & ~4095, 4096))
    for page in sorted(pages):
        machine.mem_map(page, 4096)
    machine.mem_write(code, body)
    machine.mem_write(table_address, table)
    machine.mem_write(CALLER, struct.pack("<II", 0xe5902000, 0xe592f000 | SLOT))
    receiver = struct.pack("<I", table_address + 8) + bytes(range(4, 128))
    entries = SHAPES[shape]
    vector = bytearray((index * 41 + len(entries)) % 256 for index in range(384))
    # Seed an opaque vector, its backing entries and canary pointee regions.
    # These fixture offsets make no claim about the native vector layout.
    struct.pack_into("<III", vector, 0, VECTOR + 64, len(entries), 4)
    for index, param in enumerate(entries):
        struct.pack_into("<I", vector, 64 + 4 * index, param)
    machine.mem_write(RECEIVER, receiver)
    machine.mem_write(VECTOR, bytes(vector))

    trace, reads, writes = [], [], []

    def instruction(_machine, address, _size, _data):
        trace.append(address)

    def memory(_machine, kind, address, size, value, _data):
        if not STACK <= address < STACK + 4096:
            if kind == uc.UC_MEM_READ:
                reads.append([address, size])
            else:
                writes.append([address, size, value])

    machine.hook_add(uc.UC_HOOK_CODE, instruction)
    machine.hook_add(uc.UC_HOOK_MEM_READ | uc.UC_HOOK_MEM_WRITE, memory)
    for reg, value in (
        (arm.UC_ARM_REG_R0, RECEIVER), (arm.UC_ARM_REG_R1, VECTOR),
        (arm.UC_ARM_REG_SP, STACK_TOP), (arm.UC_ARM_REG_LR, STOP),
    ):
        machine.reg_write(reg, value)
    machine.emu_start(code if route == "direct" else CALLER, STOP, count=16)
    assert machine.reg_read(arm.UC_ARM_REG_PC) == STOP
    assert machine.reg_read(arm.UC_ARM_REG_SP) == STACK_TOP
    assert trace == ([] if route == "direct" else [CALLER, CALLER + 4]) + list(range(code, code + 16, 4))
    assert reads == ([] if route == "direct" else [[RECEIVER, 4], [table_address + 8 + SLOT, 4]])
    assert not writes
    assert machine.mem_read(RECEIVER, len(receiver)) == receiver
    assert machine.mem_read(VECTOR, len(vector)) == vector
    return {
        "route": route, "shape": shape, "trace": trace,
        "nonstack_reads": reads, "nonstack_writes": writes,
        "receiver_unchanged": True, "vector_and_pointees_unchanged": True,
    }


def generate(path, role):
    elf_sha, address, offset, table_address, table_sha = ORIGINALS[role]
    assert sha(path.read_bytes()) == elf_sha
    with path.open("rb") as stream:
        elf = ELFFile(stream)
        assert elf["e_machine"] == "EM_ARM" and elf.little_endian
        body, original = checked_range(elf, MANGLED, address, 16, BODY_SHA)
        table, mapping = checked_range(elf, VTABLE, table_address, 112, table_sha)
    assert (original["section"], original["file_offset"]) == (12, offset)
    assert struct.unpack_from("<I", table, 8 + SLOT)[0] == address
    return {
        "role": role, "elf_sha256": elf_sha, "original": original, "vtable": mapping,
        "cases": [replay(address, body, table, table_address, route, shape)
                  for route in ("direct", "vtable") for shape in SHAPES],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client", type=Path, required=True)
    parser.add_argument("--server", type=Path, required=True)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--write", type=Path)
    target.add_argument("--check", type=Path)
    args = parser.parse_args()
    result = {
        "unicorn": uc.__version__,
        "originals": [generate(getattr(args, role), role) for role in ORIGINALS],
    }
    encoded = json.dumps(result, indent=2) + "\n"
    if args.write:
        args.write.write_text(encoded)
    else:
        assert json.loads(args.check.read_text()) == result
    print("12 ARM receiver/vector observations matched across both originals")


if __name__ == "__main__":
    main()
