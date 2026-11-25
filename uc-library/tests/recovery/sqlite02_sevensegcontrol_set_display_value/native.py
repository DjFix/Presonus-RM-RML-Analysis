"""Replay both original setValue bodies and their original converters offline."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import struct

from capstone import Cs, CS_ARCH_ARM, CS_MODE_ARM
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE, __version__
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_SP

CONVERTER = "_ZNK8Presonus5Panel15SevenSegControl16convertCharToBmpEcb"
CASES = (
    ((32, 32), (0, 0), (0, 0)),
    ((56, 65), (1, 0), (0, 0)),
    ((48, 95), (0, 0), (126, 0)),
    ((122, 95), (1, 0), (0, 16)),
    ((48, 95), (0, 0), (126, 16)),
    ((255, 63), (0, 1), (0xffff, 0x1228)),
    ((57, 97), (0, 1), (206, 239)),
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def function(elf, image, name):
    row, = elf.get_section_by_name(".symtab").get_symbol_by_name(name)
    sid, address, size = row["st_shndx"], row["st_value"], row["st_size"]
    section = elf.get_section(sid)
    relative = address - section["sh_addr"]
    assert row["st_info"]["type"] == "STT_FUNC" and section.name == ".text"
    assert section["sh_type"] == "SHT_PROGBITS" and 0 <= relative <= section["sh_size"] - size
    offset = section["sh_offset"] + relative
    code = image[offset:offset + size]
    return dict(mangled=name, section=sid, address=address, size=size, file_offset=offset,
                range_sha256=sha(code), range_hex=code.hex()), code


def static_data(elf, image, address, size):
    for section in elf.iter_sections():
        delta = address - section["sh_addr"]
        if section["sh_flags"] & 2 and section["sh_type"] == "SHT_PROGBITS" and 0 <= delta <= section["sh_size"] - size:
            offset = section["sh_offset"] + delta
            data = image[offset:offset+size]
            return dict(address=address, size=size, section=section.name, file_offset=offset,
                        sha256=sha(data), hex=data.hex())
    raise ValueError("Unbound converter table")


def execute(identity, code, converter, converter_code, tables, characters, decimal, seed):
    receiver, io_state, args, stack, stop, write = 0x810000, 0x820000, 0x830000, 0x840800, 0x850000, 0x860000
    uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    pages = set()

    def put(address, data):
        for page in range(address & ~4095, ((address + len(data) - 1) & ~4095) + 4096, 4096):
            if page not in pages:
                uc.mem_map(page, 4096)
                pages.add(page)
        uc.mem_write(address, data)

    def bitmaps():
        return list(struct.unpack("<2H", uc.mem_read(receiver + 28, 4)))

    start = identity["address"]
    convert = converter["address"]
    put(start, code)
    put(convert, converter_code)
    for table in tables:
        put(table["address"], bytes.fromhex(table["hex"]))
    data = bytearray((7 * x + 2) % 256 for x in range(64))
    struct.pack_into("<I", data, 20, io_state)
    struct.pack_into("<2H", data, 28, *seed)
    put(receiver, bytes(data))
    put(io_state, struct.pack("<3I", io_state + 4, 0, write))
    put(args, bytes(characters))
    put(args+8, bytes(decimal))
    put(stack, bytes(4))
    put(stop, bytes(4))
    put(write, bytes.fromhex("1eff2fe1"))
    for reg, val in ((UC_ARM_REG_R0, receiver), (UC_ARM_REG_R1, args), (UC_ARM_REG_R2, args+8),
                     (UC_ARM_REG_SP, stack), (UC_ARM_REG_LR, stop)):
        uc.reg_write(reg, val)

    converter_calls, events, writes = [], [], []

    def on_code(machine, pc, _size, _data):
        if pc == convert:
            assert machine.reg_read(UC_ARM_REG_R0) == receiver
            converter_calls.append([machine.reg_read(UC_ARM_REG_R1), machine.reg_read(UC_ARM_REG_R2)])
        elif pc == write:
            assert machine.reg_read(UC_ARM_REG_R0) == io_state and len(converter_calls) == 2
            message = machine.reg_read(UC_ARM_REG_R1)
            assert stack - 64 <= message <= stack - 3
            events.append(dict(prefix=list(machine.mem_read(message, 3)), cache=bitmaps()))
        else:
            assert start <= pc < start + len(code) or convert <= pc < convert + len(converter_code)-8

    def on_write(_machine, _kind, dest, size, value, _data):
        if not stack - 64 <= dest <= stack - size:
            assert dest in (receiver+28, receiver+30) and size == 2
            writes.append([dest-receiver, value])

    uc.hook_add(UC_HOOK_CODE, on_code)
    uc.hook_add(UC_HOOK_MEM_WRITE, on_write)
    uc.emu_start(start, stop, count=200)
    assert uc.reg_read(UC_ARM_REG_PC) == stop and uc.reg_read(UC_ARM_REG_SP) == stack
    assert converter_calls == [list(pair) for pair in zip(characters, decimal, strict=True)]
    assert bytes(uc.mem_read(receiver, 28)) == data[:28]
    assert bytes(uc.mem_read(receiver+32, 32)) == data[32:]
    assert bytes(uc.mem_read(args, 2)) == bytes(characters)
    assert bytes(uc.mem_read(args+8, 2)) == bytes(decimal)
    assert len(events) == len(writes)
    return dict(characters=characters, decimals=decimal, seed=seed, messages=events,
                final=bitmaps(), writes=writes, converter_calls=converter_calls)


def observe(packet, rootfs):
    entries = []
    for item in json.loads(packet.read_text())["originals"]:
        original = item["original"]
        image = (rootfs / Path(original["elf_path"]).relative_to("rootfs")).read_bytes()
        assert sha(image) == original["elf"]
        elf = ELFFile(io.BytesIO(image))
        assert elf.elfclass == 32 and elf.little_endian and elf["e_machine"] == "EM_ARM"
        identity, code = function(elf, image, original["mangled"])
        assert all(original[key] == value for key, value in identity.items())
        converter, converter_code = function(elf, image, CONVERTER)
        for at in (36, 56):
            branch, = Cs(CS_ARCH_ARM, CS_MODE_ARM).disasm(code[at:at+4], identity["address"]+at)
            assert branch.mnemonic == "bl" and int(branch.op_str[1:], 16) == converter["address"]
        digits, letters = struct.unpack("<II", converter_code[-8:])
        tables = [static_data(elf, image, digits, 20), static_data(elf, image, letters, 52)]
        boundary = dict(converter=converter, tables=tables, panel_io_virtual_offset=4)
        entries.append(dict(original=original, boundaries=boundary,
                            cases=[execute(identity, code, converter, converter_code, tables, *case)
                                   for case in CASES]))
    return dict(engine=f"Unicorn {__version__}", entries=entries)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet", type=Path)
    parser.add_argument("rootfs", type=Path)
    parser.add_argument("_direct", type=Path)
    args = parser.parse_args()
    print(json.dumps(observe(args.packet, args.rootfs), indent=2))
