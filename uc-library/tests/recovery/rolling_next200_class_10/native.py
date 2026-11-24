"""Execute the exact direct ARM occurrence from the hash-bound surface ELF."""
import argparse
import hashlib
import io
import json
from pathlib import Path

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE
from unicorn.arm_const import (
    UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R11, UC_ARM_REG_SP, UC_ARM_REG_LR,
    UC_ARM_REG_PC,
)

ELF_SHA256 = '304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
MANGLED = '_ZN8Presonus7Surface21NetworkSetupComponent15onServerChangedEPNS_2UC11NetworkItemE'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def observe(path):
    data = path.read_bytes()
    if digest(data) != ELF_SHA256:
        raise ValueError('Unexpected surface ELF hash')
    elf = ELFFile(io.BytesIO(data))
    symbol, = elf.get_section_by_name('.symtab').get_symbol_by_name(MANGLED)
    address, size, index = [symbol[key] for key in ('st_value', 'st_size', 'st_shndx')]
    section = elf.get_section(index)
    offset = section['sh_offset'] + address - section['sh_addr']
    if (address, size, index, section.name, offset) != (0xa4378, 16, 12, '.text', 0x9c378):
        raise ValueError('ELF symbol range differs from the sealed occurrence')
    if not 0 <= address - section['sh_addr'] <= section['sh_size'] - size:
        raise ValueError('ELF symbol is outside its section')
    code = data[offset:offset + size]
    if digest(code) != '60cf0e8b51daf6a0ce5a5eea619d9a3e219bccf7fa26c553983e5baf3012cfad':
        raise ValueError('ELF body hash differs from the sealed occurrence')
    cases = []
    for has_item, populated in ((0, 0), (1, 0), (0, 1), (1, 1)):
        machine = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        for page in (address & ~0xfff, 0x10000, 0x20000, 0x30000):
            machine.mem_map(page, 0x1000)
        machine.mem_write(address, code)
        receiver, argument = 0x10080, 0x20080 if has_item else 0
        sp, fp, sentinel = 0x30800, 0x30700, 0x30f00
        memory = {
            receiver: bytes([0xa5 if populated else 0]) * 512,
            0x20080: bytes([0x5a]) * 512,
        }
        for where, pattern in memory.items():
            machine.mem_write(where, pattern)
        initial = {
            UC_ARM_REG_R0: receiver, UC_ARM_REG_R1: argument, UC_ARM_REG_SP: sp,
            UC_ARM_REG_R11: fp, UC_ARM_REG_LR: sentinel,
        }
        for register, value in initial.items():
            machine.reg_write(register, value)
        instructions, accesses = [], []
        machine.hook_add(UC_HOOK_CODE, lambda _, at, width, data: instructions.append((at, width)))
        machine.hook_add(
            UC_HOOK_MEM_READ | UC_HOOK_MEM_WRITE,
            lambda _, kind, at, width, value, data: accesses.append((kind, at, width)),
        )
        machine.emu_start(address, sentinel, count=8)
        state_unchanged = all(machine.mem_read(at, len(pattern)) == pattern for at, pattern in memory.items())
        no_object_access = all(sp - 16 <= at and at + width <= sp for _, at, width in accesses)
        restored = all(machine.reg_read(register) == value for register, value in initial.items())
        returned = machine.reg_read(UC_ARM_REG_PC) == sentinel
        direct = instructions == [(at, 4) for at in range(address, address + size, 4)]
        if not (state_unchanged and no_object_access and restored and returned and direct):
            raise ValueError('Native execution escaped the expected direct callback domain')
        cases.append({
            'input': [has_item, populated],
            'output': [int(state_unchanged)],
            'instructions': instructions,
            'data_accesses': accesses,
            'entry_registers_preserved': restored,
            'returned_to_sentinel': returned,
        })
    return {
        'elf_sha256': ELF_SHA256, 'mangled': MANGLED, 'address': address,
        'size': size, 'section': index, 'section_name': section.name,
        'file_offset': offset, 'range_sha256': digest(code), 'cases': cases,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--elf', type=Path, required=True)
    options = parser.parse_args()
    print(json.dumps(observe(options.elf), indent=2))


if __name__ == '__main__':
    main()
