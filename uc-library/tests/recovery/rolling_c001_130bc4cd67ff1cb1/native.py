import argparse
import hashlib
import io
import json
from pathlib import Path

import unicorn
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE
from unicorn.arm_const import *


def observe(path):
    original = {'elf_sha256': '9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07', 'firmware': 'RM/RML mixer 13731', 'role': 'server', 'mangled': '_ZN8Presonus5Panel16SharedMemoryComm4openEPKc', 'address': 611180, 'size': 20, 'section': '.text', 'section_index': 12}
    data = path.read_bytes()
    assert hashlib.sha256(data).hexdigest() == original["elf_sha256"]
    elf = ELFFile(io.BytesIO(data))
    symbol, = elf.get_section_by_name(".symtab").get_symbol_by_name(original["mangled"])
    assert (symbol["st_value"], symbol["st_size"], symbol["st_shndx"]) == (
        original["address"], original["size"], original["section_index"])
    section = elf.get_section(symbol["st_shndx"])
    assert section.name == original["section"]
    address = symbol["st_value"]
    offset = section["sh_offset"] + address - section["sh_addr"]
    assert offset == 578412
    code = data[offset:offset + symbol["st_size"]]
    assert hashlib.sha256(code).hexdigest() == 'f4fc1200a4af6d09889b5ae7a9a8ab14566224ef17078675ef8021500729a481'
    result = []
    for index, argument in enumerate([0, 196608, 196624]):
        machine = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        machine.mem_map(address & ~0xfff, 0x1000)
        stack_page = 0x1000000
        stack = stack_page + 0x800
        stop = 0x2000000
        frame = 0xaaaabbbb
        receiver = 0x40000 + index * 4
        machine.mem_map(stack_page, 0x1000)
        machine.mem_write(address, code)
        for register, value in [(UC_ARM_REG_SP, stack), (UC_ARM_REG_LR, stop),
                                (UC_ARM_REG_FP, frame), (UC_ARM_REG_R0, receiver),
                                (UC_ARM_REG_R1, argument)]:
            machine.reg_write(register, value)
        accesses = []
        machine.hook_add(UC_HOOK_MEM_READ | UC_HOOK_MEM_WRITE,
                         lambda _, access, addr, size, value, user: accesses.append([access, addr, size]))
        machine.emu_start(address, stop, count=10)
        assert machine.reg_read(UC_ARM_REG_PC) == stop
        assert machine.reg_read(UC_ARM_REG_SP) == stack
        assert machine.reg_read(UC_ARM_REG_FP) == frame
        assert machine.reg_read(UC_ARM_REG_R1) == argument
        assert accesses and all(stack - 16 <= addr and addr + size <= stack
                                for _, addr, size in accesses)
        result.append(dict(argument=argument, receiver=receiver,
                           return_word=machine.reg_read(UC_ARM_REG_R0), accesses=accesses))
    return dict(original=original, file_offset=offset, sha256='f4fc1200a4af6d09889b5ae7a9a8ab14566224ef17078675ef8021500729a481',
                unicorn=unicorn.__version__, cases=result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--elf", type=Path, required=True)
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--record", action="store_true")
    args = parser.parse_args()
    result = observe(args.elf)
    if args.record:
        args.fixtures.write_text(json.dumps(result, indent=2) + "\n")
    else:
        assert result == json.loads(args.fixtures.read_text())
    print(f"Verified {len(result['cases'])} native executions")
