"""Execute the original ARM callback from the hash-identified ELF."""
import argparse
import hashlib
import io
import json
from pathlib import Path

from elftools.elf.elffile import ELFFile
from unicorn import UC_ARCH_ARM, UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE, UC_MODE_ARM, Uc
from unicorn.arm_const import (
    UC_ARM_REG_FP, UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_SP,
)

MANGLED = '_ZN8Presonus5Mixer17AVBCascadeManager15onServerChangedEPNS_2UC11NetworkItemE'
ELF_HASH = '9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
BODY_HASH = '60cf0e8b51daf6a0ce5a5eea619d9a3e219bccf7fa26c553983e5baf3012cfad'


def observe(path):
    data = path.read_bytes()
    assert hashlib.sha256(data).hexdigest() == ELF_HASH
    elf = ELFFile(io.BytesIO(data))
    symbols = elf.get_section_by_name('.symtab').get_symbol_by_name(MANGLED)
    assert len(symbols) == 1
    symbol = symbols[0]
    index, address, size = (symbol[k] for k in ('st_shndx', 'st_value', 'st_size'))
    assert (index, address, size) == (12, 0x5ea2c, 16)
    section = elf.get_section(index)
    offset = section['sh_offset'] + address - section['sh_addr']
    assert section.name == '.text' and 0 <= address - section['sh_addr'] <= section['sh_size'] - size
    body = data[offset:offset + size]
    assert offset == 0x56a2c and hashlib.sha256(body).hexdigest() == BODY_HASH
    cases = []
    code_page = address & ~0xfff
    receiver, selected, other = 0x100000, 0x101000, 0x102000
    stack, frame, stop = 0x201000, 0x200f80, code_page + 0xf00
    for name, pointer in [('null', 0), ('selected', selected), ('other', other)]:
        arm = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        arm.mem_map(code_page, 4096)
        arm.mem_write(address, body)
        arm.mem_map(receiver, 3 * 4096)
        marker = bytes(range(256)) * 48
        arm.mem_write(receiver, marker)
        arm.mem_map(0x200000, 4096)
        for reg, value in [(UC_ARM_REG_R0, receiver), (UC_ARM_REG_R1, pointer),
                           (UC_ARM_REG_SP, stack), (UC_ARM_REG_FP, frame), (UC_ARM_REG_LR, stop)]:
            arm.reg_write(reg, value)
        trace, accesses = [], []
        arm.hook_add(UC_HOOK_CODE, lambda _, pc, _size, _user: trace.append(pc))
        arm.hook_add(UC_HOOK_MEM_READ | UC_HOOK_MEM_WRITE,
                     lambda _, kind, loc, width, _value, _user: accesses.append([kind, loc, width]))
        arm.emu_start(address, stop, count=8)
        assert trace == list(range(address, address + size, 4))
        assert arm.reg_read(UC_ARM_REG_PC) == stop
        assert arm.reg_read(UC_ARM_REG_FP) == frame and arm.reg_read(UC_ARM_REG_SP) == stack
        assert arm.reg_read(UC_ARM_REG_R0) == receiver and arm.reg_read(UC_ARM_REG_R1) == pointer
        assert all(stack - 16 <= loc and loc + width <= stack for _, loc, width in accesses)
        unchanged = arm.mem_read(receiver, len(marker)) == marker
        assert unchanged
        cases.append({'argument': name, 'objects_unchanged': unchanged, 'external_calls': 0,
                      'instruction_addresses': trace, 'stack_accesses': accesses,
                      'restored_sp': stack, 'restored_fp': frame, 'r0': receiver, 'r1': pointer})
    return {'elf_sha256': ELF_HASH, 'mangled': MANGLED, 'section_index': index,
            'section': section.name, 'address': address, 'size': size, 'file_offset': offset,
            'body_sha256': BODY_HASH, 'cases': cases}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--elf', type=Path, required=True)
    parser.add_argument('--verify', type=Path)
    args = parser.parse_args()
    observed = observe(args.elf)
    if args.verify:
        if observed != json.loads(args.verify.read_text()):
            parser.exit(1, 'Original ARM observations differ from the fixture\n')
        print(f"Original ARM cases verified: {len(observed['cases'])}")
    else:
        print(json.dumps(observed, indent=2))
