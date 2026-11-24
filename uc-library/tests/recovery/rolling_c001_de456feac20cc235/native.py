"""Execute each independently verified original ARM function offline."""
import argparse
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import struct

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE, UC_MODE_ARM
from unicorn.arm_const import UC_ARM_REG_FP, UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_SP

SYMBOL = "_ZN8Presonus5Panel12MeterControl6castToEi"
RANGE_SHA = "b51029f595b7e68935b18230d57f18376ac45b93cbe89f459387015cd666c618"
ORIGINALS = [
    ("server", "RM/RML mixer 13731", 0x935f4, 0x8b5f4,
     "9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07"),
    ("client", "CS18AI surface 13840", 0x19d78, 0x11d78,
     "304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0"),
]


def execute(body, address, class_id, receiver):
    machine = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    page = address & ~0xfff
    machine.mem_map(page, 0x1000)
    machine.mem_write(address, body)
    machine.mem_map(0x1000000, 0x1000)
    stack = 0x1000800
    stop = 0x2000000
    frame = 0x1000900
    machine.reg_write(UC_ARM_REG_R0, receiver)
    machine.reg_write(UC_ARM_REG_R1, class_id & 0xffffffff)
    machine.reg_write(UC_ARM_REG_SP, stack)
    machine.reg_write(UC_ARM_REG_FP, frame)
    machine.reg_write(UC_ARM_REG_LR, stop)
    instructions, accesses = [], []

    def record_instruction(_machine, pc, _size, _data):
        instructions.append(pc - address)

    def record_access(_machine, access, pointer, size, _value, _data):
        accesses.append((access, pointer, size))

    machine.hook_add(UC_HOOK_CODE, record_instruction)
    machine.hook_add(UC_HOOK_MEM_READ | UC_HOOK_MEM_WRITE, record_access)
    machine.emu_start(address, stop, count=20)
    assert machine.reg_read(UC_ARM_REG_PC) == stop
    assert machine.reg_read(UC_ARM_REG_SP) == stack
    assert machine.reg_read(UC_ARM_REG_FP) == frame
    assert all(0 <= pc < 40 for pc in instructions)
    assert all((stack - 16 <= pointer <= stack - 4 and size == 4)
               or (pointer in (address + 40, address + 44) and size == 4)
               for _, pointer, size in accesses)
    result = machine.reg_read(UC_ARM_REG_R0)
    assert result in (0, receiver)
    return {"receiver": receiver, "r0": result, "offsets_executed": instructions,
            "memory_accesses": [list(access) for access in accesses]}


def observe(path, original):
    role, firmware, address, offset, elf_hash = original
    image = path.read_bytes()
    assert sha256(image).hexdigest() == elf_hash
    elf = ELFFile(BytesIO(image))
    assert elf.elfclass == 32 and elf.little_endian and elf["e_machine"] == "EM_ARM"
    symbols = elf.get_section_by_name(".symtab").get_symbol_by_name(SYMBOL)
    assert len(symbols) == 1
    symbol = symbols[0]
    assert (symbol["st_value"], symbol["st_size"], symbol["st_shndx"]) == (address, 48, 12)
    section = elf.get_section(12)
    assert section.name == ".text"
    displacement = address - section["sh_addr"]
    assert 0 <= displacement <= section["sh_size"] - 48
    assert section["sh_offset"] + displacement == offset
    body = image[offset:offset + 48]
    assert sha256(body).hexdigest() == RANGE_SHA
    literals = struct.unpack_from("<ii", body, 40)
    class_ids = sorted({-2147483648, -1, 0, 1, 2147483647, *(
        value + delta for value in literals for delta in (-1, 0, 1))})
    rows = [{"class_id": class_id,
             "native": [execute(body, address, class_id, receiver)
                        for receiver in (0x03001000, 0x03002000)]}
            for class_id in class_ids]
    return {"original": {"elf_sha256": elf_hash, "mangled": SYMBOL, "role": role,
                         "firmware": firmware, "address": address, "size": 48, "section": 12},
            "section_name": section.name, "file_offset": offset, "range_sha256": RANGE_SHA,
            "path": str(path), "literals": list(literals), "cases": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server", required=True, type=Path)
    parser.add_argument("--client", required=True, type=Path)
    parser.add_argument("--verify", type=Path)
    args = parser.parse_args()
    document = {"roles": [observe(path, original) for path, original in
                          zip((args.server, args.client), ORIGINALS, strict=True)]}
    if args.verify:
        assert document == json.loads(args.verify.read_text()), "Native replay differs from fixtures"
        print("PASS: 44 fresh native ARM executions across both ELF identities")
    else:
        print(json.dumps(document, indent=2))


if __name__ == "__main__":
    main()
