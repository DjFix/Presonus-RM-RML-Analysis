"""Execute the hash-bound surface network-item release hook in an isolated ARM machine."""
import argparse
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path

from elftools.elf.elffile import ELFFile
from unicorn import UC_ARCH_ARM, UC_HOOK_MEM_WRITE, UC_MODE_ARM, Uc
from unicorn import arm_const as arm

ELF = '304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
MANGLED = '_ZN8Presonus7Surface14CascadeHandler21onNetworkItemReleasedEPNS_2UC11NetworkItemE'
BODY = '60cf0e8b51daf6a0ce5a5eea619d9a3e219bccf7fa26c553983e5baf3012cfad'
ADDRESS = 0x7B738
REGISTERS = [getattr(arm, f'UC_ARM_REG_R{n}') for n in range(16)]


def observe(code, receiver, pointed):
    machine = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    for page in (ADDRESS & ~0xFFF, 0x10000, 0x11000, 0x12000, 0x13000):
        machine.mem_map(page, 0x1000)
    machine.mem_write(ADDRESS, code)
    sentinel = bytes(range(256)) * 16
    for page in (0x10000, 0x11000):
        machine.mem_write(page, sentinel)
    stack, stop = 0x12800, 0x13000
    inputs = [receiver, pointed, *range(0x912, 0x91C), 0x91C, stack, stop]
    for register, value in zip(REGISTERS, inputs):
        machine.reg_write(register, value)
    writes = []
    machine.hook_add(UC_HOOK_MEM_WRITE,
                     lambda _, __, address, size, value, ___: writes.append((address, size)))
    machine.emu_start(ADDRESS, stop, count=4)
    outputs = [machine.reg_read(register) for register in REGISTERS]
    unchanged_regions = all(machine.mem_read(page, 4096) == sentinel
                            for page in (0x10000, 0x11000))
    assert outputs[:12] == inputs[:12] and outputs[13:15] == inputs[13:15]
    assert outputs[15] == stop and outputs[12] == stack
    assert sorted(writes) == [(stack - offset, 4) for offset in (16, 12, 8, 4)]
    assert unchanged_regions
    return {'receiver': receiver, 'pointed': pointed, 'r0': outputs[0],
            'nonstack_memory_unchanged': unchanged_regions, 'stack_writes': [list(write) for write in sorted(writes)],
            'frame_stack_and_preserved_registers_restored': True}


def run(path):
    blob = path.read_bytes()
    assert sha256(blob).hexdigest() == ELF
    elf = ELFFile(BytesIO(blob))
    symbol, = elf.get_section_by_name('.symtab').get_symbol_by_name(MANGLED)
    assert (symbol['st_value'], symbol['st_size'], symbol['st_shndx']) == (ADDRESS, 16, 12)
    section = elf.get_section(12)
    offset = section['sh_offset'] + ADDRESS - section['sh_addr']
    assert section.name == '.text' and offset == 0x73738
    assert 0 <= ADDRESS - section['sh_addr'] <= section['sh_size'] - 16
    code = blob[offset:offset + 16]
    assert sha256(code).hexdigest() == BODY
    return {'elf_sha256': ELF, 'mangled': MANGLED, 'address': ADDRESS,
            'size': 16, 'section': 12, 'file_offset': offset, 'range_sha256': BODY,
            'cases': [observe(code, 0x10020, 0), observe(code, 0x11080, 0x10100)]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--elf', required=True, type=Path)
    parser.add_argument('--fixture', type=Path)
    args = parser.parse_args()
    observations = run(args.elf)
    if args.fixture:
        assert json.loads(args.fixture.read_text()) == observations
    print(json.dumps(observations, indent=2))


if __name__ == '__main__':
    main()
