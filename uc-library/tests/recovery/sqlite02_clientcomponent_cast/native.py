"""Execute exact original constructor/dispatch bodies and record boundaries."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import struct

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE, __version__
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC

CORE_C2 = "_ZN4Core8Portable9ComponentC2EPKc"
DISPATCH = "_ZTVN8Presonus2UC15ClientComponentE"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def get_symbol(elf, name):
    match, = elf.get_section_by_name(".symtab").get_symbol_by_name(name)
    return match


def map_body(uc, address, code, pages):
    for page in range(address & ~4095, ((address + len(code) - 1) & ~4095) + 4096, 4096):
        if page not in pages:
            uc.mem_map(page, 4096)
            pages.add(page)
    uc.mem_write(address, code)


def execute(address, code, target, point, case):
    receiver, stack, name, stop = 0x800100, 0x900800, 0xa00140, 0xb00000
    uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    pages = set()
    map_body(uc, address, code, pages)
    map_body(uc, receiver, bytes((31 + x * 11) % 256 for x in range(512)), pages)
    map_body(uc, stack, b"\0", pages)
    map_body(uc, stop, b"\0\0\0\0", pages)
    if target is not None:
        map_body(uc, target, bytes.fromhex("1eff2fe1"), pages)  # boundary return
        if case is not None:
            map_body(uc, name, case.encode("ascii") + b"\0", pages)
        argument = 0 if case is None else name
    else:
        argument = case & 0xffffffff
    for reg, value in ((UC_ARM_REG_R0, receiver), (UC_ARM_REG_R1, argument),
                       (UC_ARM_REG_LR, stop), (UC_ARM_REG_SP, stack)):
        uc.reg_write(reg, value)
    calls = []
    writes = []
    before = bytes(uc.mem_read(receiver, 512))

    def on_instruction(machine, pc, _size, _data):
        if pc == target:
            assert machine.reg_read(UC_ARM_REG_R0) == receiver
            assert machine.reg_read(UC_ARM_REG_R1) == argument
            calls.append(dict(name=case, receiver=True, address=pc))
        else:
            assert address <= pc < address + len(code) - (4 if target is not None else 8)

    def on_write(_machine, _access, dest, size, value, _data):
        if not stack - 24 <= dest <= stack - size:
            assert receiver <= dest <= receiver + 512 - size
            writes.append([dest - receiver, size, value])

    uc.hook_add(UC_HOOK_CODE, on_instruction)
    uc.hook_add(UC_HOOK_MEM_WRITE, on_write)
    uc.emu_start(address, stop, count=25)
    assert uc.reg_read(UC_ARM_REG_PC) == stop and uc.reg_read(UC_ARM_REG_SP) == stack
    after = bytes(uc.mem_read(receiver, 512))
    result = uc.reg_read(UC_ARM_REG_R0)
    if target is not None:
        assert len(calls) == 1 and result == receiver
        assert writes == [[0, 4, point], [4, 4, point + 0x3c]]
        assert after[8:] == before[8:]
    else:
        assert result in (receiver, 0) and after == before and not writes and not calls
    return dict(input=case, receiver_result=result == receiver, calls=calls, writes=writes)


def observe(packet, rootfs):
    entries = []
    for item in json.loads(packet.read_text())["originals"]:
        original = item["original"]
        image = (rootfs / Path(original["elf_path"]).relative_to("rootfs")).read_bytes()
        assert digest(image) == original["elf"]
        elf = ELFFile(io.BytesIO(image))
        assert elf.elfclass == 32 and elf.little_endian and elf["e_machine"] == "EM_ARM"
        row = get_symbol(elf, original["mangled"])
        assert row["st_info"]["type"] == "STT_FUNC"
        addr, size, sid = row["st_value"], row["st_size"], row["st_shndx"]
        assert (addr, size, sid) == (original["address"], original["size"], original["section"])
        section = elf.get_section(sid)
        relative = addr - section["sh_addr"]
        assert section.name == ".text" and section["sh_type"] == "SHT_PROGBITS"
        assert 0 <= relative <= section["sh_size"] - size
        offset = section["sh_offset"] + relative
        assert offset == original["file_offset"]
        code = image[offset:offset + size]
        assert code.hex() == original["range_hex"] and digest(code) == original["range_sha256"]
        if "castTo" in original["mangled"]:
            literals = struct.unpack_from("<ii", code, len(code) - 8)
            cases = [*literals, *(v + d for v in literals for d in (-1, 1)),
                     -2147483648, -1, 0, 2147483647]
            target = point = None
            boundary = None
        else:
            base = get_symbol(elf, CORE_C2)
            table = get_symbol(elf, DISPATCH)
            target, point = base["st_value"], table["st_value"] + 8
            assert size == 48 and int.from_bytes(code[-4:], "little") == point
            sibling_name = original["mangled"].replace("C1E", "C2E") if "C1E" in original["mangled"] else original["mangled"].replace("C2E", "C1E")
            sibling = get_symbol(elf, sibling_name)
            assert sibling["st_value"] != addr and sibling["st_size"] == size
            cases = [None, "", "UC component", "A/B"]
            boundary = dict(symbol=CORE_C2, address=target, section=base["st_shndx"],
                            size=base["st_size"], vtable=DISPATCH, dispatch_points=[point, point+0x3c],
                            sibling_mangled=sibling_name, sibling_address=sibling["st_value"])
        entries.append(dict(original=original, provider_boundary=boundary,
                            cases=[execute(addr, code, target, point, case) for case in cases]))
    return dict(engine=f"Unicorn {__version__}", entries=entries)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet", type=Path)
    parser.add_argument("rootfs", type=Path)
    args = parser.parse_args()
    print(json.dumps(observe(args.packet, args.rootfs), indent=2))
