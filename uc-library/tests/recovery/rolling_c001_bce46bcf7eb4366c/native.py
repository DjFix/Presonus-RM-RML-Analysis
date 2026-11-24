import hashlib
import json
import sys
from pathlib import Path

import unicorn
from elftools.elf.elffile import ELFFile
from unicorn import UC_ARCH_ARM, UC_HOOK_MEM_WRITE, UC_MODE_ARM, Uc
from unicorn.arm_const import UC_ARM_REG_PC, UC_ARM_REG_R0

MANGLED = "_ZN8Presonus7Surface14CascadeHandler17onNetworkShutdownEv"
ELF_SHA = "304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0"
RANGE_SHA = "60cf0e8b51daf6a0ce5a5eea619d9a3e219bccf7fa26c553983e5baf3012cfad"


def observe(path):
    assert hashlib.sha256(path.read_bytes()).hexdigest() == ELF_SHA
    with path.open("rb") as stream:
        elf = ELFFile(stream)
        matches = elf.get_section_by_name(".symtab").get_symbol_by_name(MANGLED)
        assert len(matches) == 1
        symbol = matches[0]
        address, size = symbol["st_value"], symbol["st_size"]
        section = elf.get_section(symbol["st_shndx"])
        assert (address, size, symbol["st_shndx"], section.name) == (0x7B750, 16, 12, ".text")
        displacement = address - section["sh_addr"]
        assert 0 <= displacement <= section["sh_size"] - size
        offset = section["sh_offset"] + displacement
        code = section.data()[displacement:displacement + size]
    assert offset == 0x73750 and hashlib.sha256(code).hexdigest() == RANGE_SHA

    cases = []
    for case in range(3):
        cpu = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        cpu.mem_map(0x7B000, 0x1000)
        cpu.mem_write(address, code)
        cpu.mem_map(0x100000, 0x1000)
        cpu.mem_map(0x200000, 0x1000)
        sentinel = bytes([0xAB + case]) * 0x1000
        cpu.mem_write(0x200000, sentinel)
        end = 0x7B900
        registers = [UC_ARM_REG_R0 + i for i in range(13)]
        from unicorn.arm_const import UC_ARM_REG_SP, UC_ARM_REG_LR
        registers += [UC_ARM_REG_SP, UC_ARM_REG_LR]
        values = [0x200100 + case * 16, 0x200200, 0x200300, 0x200400]
        values += [case * 100 + i for i in range(4, 13)]
        values += [0x100800, end]
        for register, value in zip(registers, values):
            cpu.reg_write(register, value)
        writes = []
        cpu.hook_add(UC_HOOK_MEM_WRITE, lambda _, access, at, length, value, data:
                     writes.append([at, length, value]))
        cpu.emu_start(address, end, count=8)
        observed = [cpu.reg_read(register) for register in registers]
        assert cpu.reg_read(UC_ARM_REG_PC) == end
        assert observed[:12] == values[:12] and observed[13:] == values[13:]
        assert sorted((at, length) for at, length, _ in writes) == [
            (0x1007F0 + index * 4, 4) for index in range(4)
        ]
        assert cpu.mem_read(0x200000, 0x1000) == sentinel
        cases.append({"register_inputs": values, "register_outputs": observed,
                      "stack_writes": writes, "portable_observation": "unchanged"})
    return {"elf_sha256": ELF_SHA, "mangled": MANGLED, "address": address, "size": size,
            "section": section.name, "file_offset": offset, "range_sha256": RANGE_SHA,
            "unicorn": unicorn.__version__, "cases": cases}


if __name__ == "__main__":
    observation = observe(Path(sys.argv[1]))
    print(json.dumps(observation, indent=2))
