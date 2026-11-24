"""Observe an exact ARM method without emulating any surrounding firmware."""
import hashlib
import io
import itertools
from pathlib import Path

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_LR, UC_ARM_REG_SP, UC_ARM_REG_FP, UC_ARM_REG_PC

ELF = Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling-c001-20261124/packeting/first10/snapshot/rootfs/RML16AI_Rack_13731/home/root/mixer')
ELF_SHA = '9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
BODY_SHA = '60cf0e8b51daf6a0ce5a5eea619d9a3e219bccf7fa26c553983e5baf3012cfad'
MANGLED = '_ZN8Presonus16MeterManagerBase15sendUCNETMetersEb'
ADDRESS, SIZE, SECTION = 0x8bb38, 16, 12


def generate():
    elf_bytes = ELF.read_bytes()
    assert hashlib.sha256(elf_bytes).hexdigest() == ELF_SHA
    elf = ELFFile(io.BytesIO(elf_bytes))
    sections = elf.get_section(SECTION)
    symbols = elf.get_section_by_name('.symtab').get_symbol_by_name(MANGLED)
    assert any((s['st_value'], s['st_size'], s['st_shndx']) ==
               (ADDRESS, SIZE, SECTION) for s in symbols)
    offset = sections['sh_offset'] + ADDRESS - sections['sh_addr']
    assert sections.name == '.text' and offset == 0x83b38
    assert ADDRESS + SIZE <= sections['sh_addr'] + sections['sh_size']
    body = elf_bytes[offset:offset + SIZE]
    assert hashlib.sha256(body).hexdigest() == BODY_SHA

    cases = []
    for state, flag in itertools.product(range(4), range(2)):
        receiver = 0x100000 + 0x40 * state
        sp, fp, ret = 0x201000, 0x201040 + 4 * state, 0x300000
        obj = bytes([0x51 + state]) * 4096
        stack = b'\xa5' * 4096
        uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        for page in [ADDRESS & ~0xfff, 0x100000, 0x200000, ret]:
            uc.mem_map(page, 4096)
        uc.mem_write(ADDRESS, body)
        uc.mem_write(0x100000, obj)
        uc.mem_write(0x200000, stack)
        args = {UC_ARM_REG_R0: receiver, UC_ARM_REG_R1: flag,
                UC_ARM_REG_SP: sp, UC_ARM_REG_FP: fp, UC_ARM_REG_LR: ret}
        for reg, value in args.items():
            uc.reg_write(reg, value)
        code, accesses = [], []
        uc.hook_add(UC_HOOK_CODE, lambda _, address, size, __: code.append(address))
        uc.hook_add(UC_HOOK_MEM_READ | UC_HOOK_MEM_WRITE,
                    lambda _, access, address, size, value, __:
                    accesses.append([access, address, size, value]))
        uc.emu_start(ADDRESS, ret, count=8)
        assert uc.reg_read(UC_ARM_REG_PC) == ret
        assert all(uc.reg_read(reg) == value for reg, value in args.items())
        assert code == list(range(ADDRESS, ADDRESS + SIZE, 4))
        assert accesses and all(sp - 16 <= address < address + size <= sp
                                for _, address, size, _ in accesses)
        assert bytes(uc.mem_read(0x200000, 4096 - 16)) == stack[:-16]
        cases.append({'state': state, 'flag': flag,
                      'receiver_unchanged': bytes(uc.mem_read(0x100000, 4096)) == obj,
                      'instructions': code, 'memory_accesses': accesses,
                      'stack_pointer': sp, 'frame_pointer': fp,
                      'receiver_pointer': receiver, 'return_pc': ret})
    return {'range': {'elf_sha256': ELF_SHA, 'mangled': MANGLED,
                      'address': ADDRESS, 'size': SIZE, 'section': SECTION,
                      'section_name': '.text', 'file_offset': offset,
                      'range_sha256': BODY_SHA, 'bytes_hex': body.hex(),
                      'firmware': 'RM/RML mixer 13731', 'role': 'server'},
            'cases': cases}
