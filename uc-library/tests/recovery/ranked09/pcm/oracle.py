#!/usr/bin/env python3
"""Execute exact original constructors until unresolved open entry (not a replay)."""
import hashlib
import json
from pathlib import Path
import unicorn
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_SP, UC_ARM_REG_LR
from elftools.elf.elffile import ELFFile

ELF = Path('rootfs/CS18_v13840/home/root/surface')
DIGEST = '304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
TARGETS = [
    ('C1', 0xdb798, 0xd3798, '718cde9dbefdc5468ada8d010fb3f8fa4fb45f99c93d98e5bddc7de6afdf9b25'),
    ('C2', 0xdb7d4, 0xd37d4, '4a8c7c2eec36e51c1934a08bdc3a50ad83b98adf64cf15e0170c5919d7adddc0'),
]

def observe():
    raw = ELF.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == DIGEST
    with ELF.open('rb') as stream:
        section = ELFFile(stream).get_section(12)
        assert section.name == '.text'
        mapping = (section['sh_addr'], section['sh_offset'], section['sh_size'])
    cases = []
    for variant, address, offset, expected_hash in TARGETS:
        assert mapping[1] + address - mapping[0] == offset
        body = raw[offset:offset + 60]
        assert hashlib.sha256(body).hexdigest() == expected_hash
        for poison in [0, 0x55, 0xaa, 0xff]:
            for name in [None, '', '/dev/NOT_OPENED']:
                machine = Uc(UC_ARCH_ARM, UC_MODE_ARM)
                machine.mem_map(0xdb000, 0x1000)
                machine.mem_write(address, body)
                machine.mem_map(0x100000, 0x3000)
                machine.mem_write(0x100000, bytes([poison]) * 32)
                if name is not None:
                    machine.mem_write(0x101000, name.encode() + b'\0')
                machine.reg_write(UC_ARM_REG_R0, 0x100000)
                machine.reg_write(UC_ARM_REG_R1, 0 if name is None else 0x101000)
                machine.reg_write(UC_ARM_REG_SP, 0x102ff0)
                machine.reg_write(UC_ARM_REG_LR, 0xdead000)
                calls = []
                def boundary(uc, pc, size, _):
                    if pc == 0xdb6bc:
                        calls.append({'target': pc, 'this': uc.reg_read(UC_ARM_REG_R0),
                                      'name_pointer': uc.reg_read(UC_ARM_REG_R1),
                                      'object_hex': bytes(uc.mem_read(0x100000, 32)).hex()})
                        uc.emu_stop()
                machine.hook_add(UC_HOOK_CODE, boundary)
                machine.emu_start(address, 0xdead000, count=100)
                assert len(calls) == 1
                cases.append({'variant': variant, 'address': address, 'file_offset': offset,
                              'size': 60, 'body_sha256': expected_hash, 'poison': poison,
                              'name': name, 'observed': calls[0]})
    return {'elf_path': str(ELF), 'elf_sha256': DIGEST, 'section': 12,
            'unicorn_version': unicorn.__version__, 'case_count': len(cases),
            'scope': 'Original ARM execution stops at open entry. No open execution, return, lifecycle, C++ replay or readiness established.',
            'cases': cases}

if __name__ == '__main__':
    import sys
    Path(sys.argv[1]).write_text(json.dumps(observe(), indent=2) + '\n')
