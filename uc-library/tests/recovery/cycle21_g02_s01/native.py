"""Run exact ARM application ranges with instrumented external boundaries."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import struct

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, __version__
from unicorn.arm_const import (
    UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1,
    UC_ARM_REG_R2, UC_ARM_REG_SP,
)

ADDRESSES = {
    's01': (0xad428, 68), 's02': (0xade80, 84), 's03': (0xad91c, 92),
    's04': (0xaddd0, 176), 's05': (0xad044, 68), 'r06': (0xacfbc, 68),
    's07': (0xad8d4, 72), 's08': (0xadaf4, 76), 's09': (0xadc68, 124),
    's10': (0xad46c, 100),
}
ELF_SHA256 = '304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
ROOT, SCREEN, REGISTRAR, ARGUMENT, CHILD, VTABLE, STACK = range(
    0x400000, 0x407000, 0x1000)
PARAMS = 0x408000
RETURN = 0x40f000
REGISTERS = (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2)


def word(i):
    return struct.pack('<I', i)


def raw_float(value):
    return struct.unpack('<I', struct.pack('<f', value))[0]


def run(image, task, value, registrar, child_mode):
    elf = ELFFile(io.BytesIO(image))
    start, size = ADDRESSES[task]
    section = elf.get_section_by_name('.text')
    file_offset = next(elf.address_offsets(start, size))
    assert file_offset == section['sh_offset'] + start - section['sh_addr']
    symbols = elf.get_section_by_name('.symtab')
    target_rows = [sym for sym in symbols.iter_symbols()
                   if sym['st_value'] == start and sym['st_size'] == size]
    assert len(target_rows) == 1 and target_rows[0]['st_shndx'] == 12
    native_range = image[file_offset:file_offset + size]
    arm = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    arm.mem_map(0x8000, 0x300000)
    for segment in elf.iter_segments():
        if segment['p_type'] == 'PT_LOAD':
            arm.mem_write(segment['p_vaddr'], segment.data())
    arm.mem_map(ROOT, 0x10000)
    arm.mem_write(ROOT, word(0x1e4b28 + 8))
    arm.mem_write(ROOT + 0x114, word(REGISTRAR if registrar else 0))
    arm.mem_write(ROOT + 0x130, bytes([int(value != 0)]))
    arm.mem_write(ARGUMENT, word(0x2051a8 + 8))
    arm.reg_write(UC_ARM_REG_R0, ROOT)
    arm.reg_write(UC_ARM_REG_R1, int(value != 0) if task in ('s02', 's04') else ARGUMENT)
    arm.reg_write(UC_ARM_REG_SP, STACK + 0xff0)
    arm.reg_write(UC_ARM_REG_LR, RETURN)

    def read_word(address):
        return struct.unpack('<I', arm.mem_read(address, 4))[0]

    def read_string(address):
        return bytes(arm.mem_read(address, 90)).split(b'\0')[0].decode()

    assert read_word(0x1e4b28 + 8 + 0x14) == 0x11ac70
    assert read_word(0x2051a8 + 8 + 0x44) == 0x11e48c
    assert read_word(0x2051a8 + 8 + 0x58) == 0x121198

    events = []
    parameters = {}

    def finish(result):
        if result is not None:
            arm.reg_write(UC_ARM_REG_R0, result)
        arm.reg_write(UC_ARM_REG_PC, arm.reg_read(UC_ARM_REG_LR))

    def hook(_, address, _size, _state):
        r0, r1, r2 = (arm.reg_read(reg) for reg in REGISTERS)
        result = None
        if address == 0xad000:
            assert r0 == ROOT
            result = SCREEN
        elif address in (0x11acf0, 0xa5aa8):
            assert r0 in (ROOT, SCREEN, REGISTRAR)
            kind = {ROOT: 'root', SCREEN: 'screen', REGISTRAR: 'registrar'}[r0]
            events.append(f'tag:{kind}:{r1}')
            result = PARAMS + len(parameters) * 16
            parameters[result] = (kind, r1)
            arm.mem_write(result, word(0x2051a8 + 8))
        elif address in (0x11f4f0, 0x11e2e0):
            assert r1 == ROOT + 4
            _, tag = parameters[r0]
            action = 'add' if address == 0x11f4f0 else 'remove'
            events.append(f'{action}:{tag}')
        elif address == 0x121198:
            _, tag = parameters[r0]
            events.append(f'set:{tag}:{r1:08x}:{r2}')
        elif address == 0x11e48c:
            assert r0 == ARGUMENT
            events.append('read')
            result = raw_float(value)
        elif address == 0xa4820:
            assert r0 == REGISTRAR
            events.append('request')
        elif address == 0xa61e0:
            assert r0 == REGISTRAR
            events.append(f'run:{r1}:{r2}')
        elif address == 0x1179d4:
            events.append('debug:' + read_string(r0).strip())
        elif address == 0x11ac70:
            assert r0 == ROOT
            events.append('find:' + read_string(r1))
            result = CHILD if child_mode else 0
        elif address == 0xae58:
            # ABI library boundary. Validate literal identities and dispatch
            # parameters, then return the explicitly modeled cast outcome.
            assert (r0, r1, r2) == (CHILD, 0x204e28,
                                    0x19ee1c if task == 's05' else 0x1a5360)
            events.append(f'cast:{r2:08x}')
            result = CHILD if child_mode == 1 else 0
        else:
            assert (start <= address < start + size
                    or 0xad86c <= address < 0xad8d4
                    or 0x1877f8 <= address < 0x187930), hex(address)
            return
        finish(result)

    arm.hook_add(UC_HOOK_CODE, hook)
    arm.emu_start(start, RETURN, count=1024)
    assert arm.reg_read(UC_ARM_REG_PC) == RETURN
    outcome = {'events': events}
    if task in ('s05', 'r06'):
        outcome['found'] = arm.reg_read(UC_ARM_REG_R0) == CHILD
    if task in ('s03', 's07'):
        outcome['active'] = bool(arm.mem_read(ROOT + 0x130, 1)[0])
    return {
        'input': [value, registrar, child_mode], 'outcome': outcome,
        'range': {'address': start, 'size': size, 'section': '.text',
                  'file_offset': file_offset, 'mangled': target_rows[0].name,
                  'sha256': hashlib.sha256(native_range).hexdigest()},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--elf', type=Path, required=True)
    parser.add_argument('--task', choices=ADDRESSES, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    image = args.elf.read_bytes()
    assert hashlib.sha256(image).hexdigest() == ELF_SHA256
    values = {
        's01': [0], 's02': [0, 1], 's03': [0, 1], 's04': [0, 1],
        's05': [0], 'r06': [0], 's07': [-1.25, -0.5, 0, 0.5, 1.25],
        's08': [-1.25, -0.5, 0, 0.5, 1.25],
        's09': [-1.25, -0.5, 0, 0.5, 1.25],
        's10': [-1.25, 0, 7, 7.75, 8, 9],
    }
    child_modes = [0, 1, 2] if args.task in ('s05', 'r06') else [0]
    registrar_modes = [False, True] if args.task == 's09' else [True]
    rows = [run(image, args.task, value, registrar, child_mode)
            for value in values[args.task] for registrar in registrar_modes
            for child_mode in child_modes]
    args.out.write_text(json.dumps({
        'elf_sha256': ELF_SHA256,
        'unicorn': __version__,
        'boundary': 'Original app target and ARM integer conversion execute. '
                    'CCL, registrar and cast boundaries are instrumented. '
                    'Canonical host providers execute separately.',
        'task': args.task, 'rows': rows,
    }, indent=2) + '\n')


if __name__ == '__main__':
    main()
