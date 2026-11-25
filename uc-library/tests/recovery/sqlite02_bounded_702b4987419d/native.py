"""Verify and execute the exact ARM getter from the original ELF."""
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import sys

from elftools.elf.elffile import ELFFile
from unicorn import UC_ARCH_ARM, UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE, UC_MODE_ARM, Uc
from unicorn import arm_const as arm

ELF = '9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
MANGLED = '_ZN8Presonus5Mixer19SendOutputComponent13getAuxPreModeEv'
BODY = 'cc4779cd9931e5090cc7c8a45c3f106a58fc49aa5097cff3909e0dd663715bba'
ADDRESS = 295556
SIZE = 20
REGISTERS = [getattr(arm, f'UC_ARM_REG_R{n}') for n in range(16)]


def observe(code, receiver, word):
    machine = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    for page in (ADDRESS & ~0xfff, 0x10000, 0x11000, 0x12000, 0x13000):
        machine.mem_map(page, 0x1000)
    machine.mem_write(ADDRESS, code)
    for page in (0x10000, 0x11000):
        machine.mem_write(page, bytes(range(256)) * 16)
    machine.mem_write(receiver + 0x1d4, word.to_bytes(4, 'little'))
    before = bytes(machine.mem_read(0x10000, 0x2000))
    stack, stop = 0x12800, 0x13000
    inputs = [receiver, *range(0x901, 0x90d), stack, stop]
    for register, value in zip(REGISTERS, inputs):
        machine.reg_write(register, value)
    reads, writes, instructions = [], [], []
    machine.hook_add(UC_HOOK_MEM_READ,
                     lambda _, __, address, size, ___, ____: reads.append([address, size]))
    machine.hook_add(UC_HOOK_MEM_WRITE,
                     lambda _, __, address, size, ___, ____: writes.append([address, size]))
    machine.hook_add(UC_HOOK_CODE,
                     lambda _, address, __, ___: instructions.append(address))
    machine.emu_start(ADDRESS, stop, count=5)
    outputs = [machine.reg_read(register) for register in REGISTERS]
    assert outputs[0] == word and outputs[1:12] == inputs[1:12]
    assert outputs[13:15] == inputs[13:15] and outputs[15] == stop
    assert instructions == list(range(ADDRESS, ADDRESS + SIZE, 4))
    assert [read for read in reads if 0x10000 <= read[0] < 0x12000] == [[receiver + 0x1d4, 4]]
    assert sorted(writes) == [[address, 4] for address in range(stack - 16, stack, 4)]
    assert bytes(machine.mem_read(0x10000, 0x2000)) == before
    return dict(receiver=receiver, word=word, r0=outputs[0], reads=reads, writes=writes,
                instructions=instructions, receiver_memory_unchanged=True)


def run(path):
    blob = path.read_bytes()
    assert sha256(blob).hexdigest() == ELF
    elf = ELFFile(BytesIO(blob))
    symbol, = elf.get_section_by_name('.symtab').get_symbol_by_name(MANGLED)
    assert (symbol['st_value'], symbol['st_size'], symbol['st_shndx']) == (ADDRESS, SIZE, 12)
    section = elf.get_section(12)
    delta = ADDRESS - section['sh_addr']
    offset = section['sh_offset'] + delta
    assert section.name == '.text' and offset == 262788
    assert 0 <= delta <= section['sh_size'] - SIZE
    code = blob[offset:offset + SIZE]
    assert sha256(code).hexdigest() == BODY
    words = (0, 1, 2, 0x7fffffff, 0x80000000, 0xffffffff)
    return dict(elf_sha256=ELF, mangled=MANGLED, address=ADDRESS, size=SIZE, section=12,
                file_offset=offset, range_sha256=BODY,
                cases=[observe(code, receiver, word)
                       for receiver in (0x10020, 0x11080) for word in words])


if __name__ == '__main__':
    print(json.dumps(run(Path(sys.argv[1])), indent=2))
