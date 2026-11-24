"""Execute the hash-bound application method offline in ARM mode."""
import hashlib
import io
import json
from pathlib import Path

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE
from unicorn.arm_const import (
    UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3,
    UC_ARM_REG_FP, UC_ARM_REG_LR, UC_ARM_REG_SP, UC_ARM_REG_PC,
)
import unicorn

ELF = Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling-c001-20261124/packeting/first10/snapshot/rootfs/RML16AI_Rack_13731/home/root/mixer')
ELF_SHA = '9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
BODY_SHA = '60cf0e8b51daf6a0ce5a5eea619d9a3e219bccf7fa26c553983e5baf3012cfad'
NAME = '_ZN8Presonus4Link9Messenger4initEv'
ADDRESS = 0x86a70
SIZE = 16
ARG_REGS = (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def case(body, released):
    machine = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    ret = 0xa0000
    stack = 0x100000
    receiver = 0x200140 + 0x200 * released
    args = [receiver, 0x49532614 + released, 0xabcdef08, 0xfedcba98]
    sp, fp = stack + 0x800, stack + 0x880
    machine.mem_map(ADDRESS & ~0xfff, 0x1000)
    machine.mem_write(ADDRESS, body)
    machine.mem_map(ret, 0x1000)
    machine.mem_map(stack, 0x1000)
    machine.mem_map(0x200000, 0x1000)
    sentinel = bytes((i * 41 + 29 * released) & 255 for i in range(64))
    machine.mem_write(receiver, sentinel)
    for reg, value in zip(ARG_REGS, args):
        machine.reg_write(reg, value)
    for reg, value in ((UC_ARM_REG_SP, sp), (UC_ARM_REG_FP, fp), (UC_ARM_REG_LR, ret)):
        machine.reg_write(reg, value)

    accesses = []

    def observe(_machine, kind, addr, size, value, _user):
        accesses.append([kind, addr, size, value])

    machine.hook_add(UC_HOOK_MEM_READ | UC_HOOK_MEM_WRITE, observe)
    machine.emu_start(ADDRESS, ret, count=4)
    output = [machine.reg_read(reg) for reg in (*ARG_REGS, UC_ARM_REG_SP, UC_ARM_REG_FP, UC_ARM_REG_PC)]
    data_after = bytes(machine.mem_read(receiver, len(sentinel)))
    assert output == [*args, sp, fp, ret], output
    assert accesses and all(sp - 16 <= addr and addr + size <= sp
                            for _, addr, size, _ in accesses), accesses
    assert data_after == sentinel
    return dict(portable_pre_released=released, receiver=receiver, sentinel_hex=sentinel.hex(),
                arguments=args, stack_pointer=sp, frame_pointer=fp, return_pc=ret,
                output_registers=output, memory_accesses=accesses, receiver_unchanged=True)


def observations():
    data = ELF.read_bytes()
    assert digest(data) == ELF_SHA
    elf = ELFFile(io.BytesIO(data))
    section = elf.get_section(12)
    matches = [sym for sym in elf.get_section_by_name('.symtab').get_symbol_by_name(NAME)
               if sym['st_shndx'] == 12 and sym['st_value'] == ADDRESS and sym['st_size'] == SIZE]
    assert len(matches) == 1 and elf['e_machine'] == 'EM_ARM'
    assert section.name == '.text' and section['sh_type'] == 'SHT_PROGBITS'
    start = ADDRESS - section['sh_addr']
    assert 0 <= start <= section['sh_size'] - SIZE
    offset = section['sh_offset'] + start
    body = data[offset:offset + SIZE]
    assert offset == 0x7ea70 and digest(body) == BODY_SHA
    return dict(elf=str(ELF), elf_sha256=ELF_SHA, mangled=NAME, section=12, section_name=section.name,
                address=ADDRESS, size=SIZE, file_offset=offset, body_sha256=BODY_SHA,
                body_hex=body.hex(), engine='Unicorn ' + unicorn.__version__,
                cases=[case(body, released) for released in (0, 1)])


if __name__ == '__main__':
    print(json.dumps(observations(), indent=2))
