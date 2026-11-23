"""Replay the exact Book append method in each sealed application ELF."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import struct

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_SP


def sha(data):
    return hashlib.sha256(data).hexdigest()


def probe(address, code, count, pointer):
    uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    stack, stop, receiver, storage = 0x60000000, 0x70000000, 0x50000100, 0x51000200
    for address_to_map in (address, stack, stop, receiver, storage):
        uc.mem_map(address_to_map & ~0xfff, 0x1000)
    uc.mem_write(address, code)
    book = bytearray(b"B" * 160)
    slots = bytearray(b"S" * 136)
    struct.pack_into("<II", book, 4, storage, count)
    uc.mem_write(receiver, bytes(book))
    uc.mem_write(storage, bytes(slots))
    writes = []

    def observe(_emu, _access, destination, width, value, _context):
        if not stack <= destination < stack + 0x1000:
            writes.append([destination, width, value])

    uc.hook_add(UC_HOOK_MEM_WRITE, observe)
    for register, value in [(UC_ARM_REG_R0, receiver), (UC_ARM_REG_R1, pointer),
                            (UC_ARM_REG_SP, stack + 0xff0), (UC_ARM_REG_LR, stop)]:
        uc.reg_write(register, value)
    uc.emu_start(address, stop, count=40)
    assert uc.reg_read(UC_ARM_REG_PC) == stop and uc.reg_read(UC_ARM_REG_SP) == stack + 0xff0
    inserted = count < 32
    if inserted:
        struct.pack_into("<I", book, 8, count + 1)
        struct.pack_into("<I", slots, 4 * count, pointer)
    assert uc.mem_read(receiver, len(book)) == book and uc.mem_read(storage, len(slots)) == slots
    return {"count": count, "pointer_word": pointer, "inserted": inserted,
            "receiver_writes": writes, "guards_preserved": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    path = args.snapshot / ("temp/recovery-work/control10x20-after-4fed70d11/"
                            "selection/panel-medium/book-add-current01/TYPED_APPEND_CURRENT_NATIVE.json")
    data = path.read_bytes()
    assert sha(data) == "785d21a093f0b5cd92fb206f2c17c902484f16cdce05cee4b6c6449d4865db0a"
    evidence = json.loads(data)
    originals = []
    for member in evidence["exact_cases"]["book-add"]:
        row = member["original"]
        digest = row["elf_sha256"]
        elf_path = evidence["source_elfs"][digest]["path"]
        data = (args.snapshot / elf_path).read_bytes()
        assert sha(data) == digest
        elf = ELFFile(io.BytesIO(data))
        assert elf.elfclass == 32 and elf.little_endian and elf["e_machine"] == "EM_ARM"
        name = row["original_mangled"]
        symbol, = elf.get_section_by_name(".symtab").get_symbol_by_name(name)
        address, size = row["original_address"], row["original_size"]
        assert (symbol["st_value"], symbol["st_size"], symbol["st_shndx"]) == (address, size, 12)
        section = elf.get_section(12)
        assert section.name == ".text" and section["sh_flags"] & 4
        delta = address - section["sh_addr"]
        assert 0 <= delta <= delta + size <= section["sh_size"]
        offset = section["sh_offset"] + delta
        code = data[offset:offset + size]
        assert offset == row["file_offset"] and sha(code) == row["content_sha256"]
        cases = [probe(address, code, case["count"], case["pointer_word"]) for case in member["native_cases"]]
        assert len(cases) == 8 and cases == member["native_cases"], cases
        client = elf_path.endswith("surface")
        originals.append({"elf_sha256": digest, "address": address, "mangled": name,
            "file_offset": offset, "range_sha256": sha(code), "section": 12, "size": size,
            "role": "client" if client else "server",
            "firmware": "CS18AI surface 13840" if client else "RM/RML mixer 13731", "cases": cases})
    assert len(originals) == 2
    args.out.write_text(json.dumps({"originals": originals}, indent=2) + "\n")


if __name__ == "__main__":
    main()
