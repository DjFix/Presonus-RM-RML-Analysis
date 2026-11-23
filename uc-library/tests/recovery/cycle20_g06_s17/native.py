"""Replay sealed ARM instructions for the assigned offline Panel entry point."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import struct

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UcError, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import *


CYCLE = Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/control10x20-after-4fed70d11')
PACKET = CYCLE / 'packeting/actual04-next-batch01/packets' / Path(__file__).parent.name
MAP = CYCLE / 'packeting/READ_INPUTS-actual04-next-batch01-cycle20_g06-actual04-next20-scoped02.json'
ENTRY = re.compile(r'ELF `([a-f0-9]+)`; version `([^`]+)`; `([^`]+)`; original `([^`]+)`; address `(0x[0-9a-f]+)`; size (\d+); section (\S+); SHA256 `([a-f0-9]+)`\nOriginal ELF path: `([^`]+)`; file offset `(0x[0-9a-f]+)`')
RECEIVER, STACK, STOP = 0x50000000, 0x60000000, 0x70000000
COORDS = [(0, 0), (4, 7), (-1, 27), (2147483647, -2147483648)]
ACTIVATIONS = [(0, 0, 0), (0, 0, 7), (0, 1, 7), (1, 0, 0), (1, 1, 3), (2, -1, 0), (2, 2, 44)]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def run(elf, address, mangled, role):
    activation = 'activate' in mangled
    constructor = 'C1Eii' in mangled or 'C2Eii' in mangled
    offscreen = 'Offscreen' in mangled
    deleting = 'D0Ev' in mangled
    args = ACTIVATIONS if activation else COORDS if constructor else [(0, 0)]
    results = []
    for case in args:
        uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        for segment in elf.iter_segments():
            if segment['p_type'] != 'PT_LOAD':
                continue
            va = segment['p_vaddr']
            start, limit = va & ~4095, (va + segment['p_memsz'] + 4095) & ~4095
            for page in range(start, limit, 4096):
                try:
                    uc.mem_map(page, 4096)
                except UcError as error:
                    if error.errno != 11:
                        raise
            uc.mem_write(va, segment.data())
        for addr in (RECEIVER, STACK, STOP):
            uc.mem_map(addr, 4096)
        uc.mem_write(RECEIVER, b'\xb7' * 256)
        if activation:
            prior, mode, dirty = case
            uc.mem_write(RECEIVER + 116, struct.pack('<Ii', dirty, prior))
            regs = [RECEIVER, mode, 0]
        else:
            regs = [RECEIVER, *case]
        for reg, val in zip((UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2), regs):
            uc.reg_write(reg, val & 0xffffffff)
        uc.reg_write(UC_ARM_REG_SP, STACK + 4096)
        uc.reg_write(UC_ARM_REG_LR, STOP)
        events = []
        memset, delete, base = ((0xaba0, 0xad5c, 0x1fa38) if role == 'client'
                                else (0xaa60, 0xac10, 0x98ea8))

        def hook(machine, pc, size, _):
            a, b, n = [machine.reg_read(reg) for reg in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2)]
            if constructor and offscreen and pc == base:
                events.append(['ElementC2', a, b, n])
            if constructor and pc == memset:
                events.append(['memset', a, b, n])
                machine.mem_write(a, bytes([b & 255]) * n)
                machine.reg_write(UC_ARM_REG_PC, machine.reg_read(UC_ARM_REG_LR))
            if deleting and pc == delete:
                assert a == RECEIVER and not events
                assert machine.mem_read(a, 4) != b'\xb7' * 4
                events.append(['unsized_delete', a])
                machine.mem_unmap(a, 4096)
                machine.reg_write(UC_ARM_REG_PC, machine.reg_read(UC_ARM_REG_LR))

        if constructor or deleting:
            uc.hook_add(UC_HOOK_CODE, hook)
        uc.emu_start(address, STOP, count=180)
        assert uc.reg_read(UC_ARM_REG_PC) == STOP
        assert uc.reg_read(UC_ARM_REG_SP) == STACK + 4096
        if deleting:
            try:
                uc.mem_read(RECEIVER, 4)
            except UcError:
                assert events == [['unsized_delete', RECEIVER]]
                expected = 'freed'
            else:
                raise AssertionError('D0 left its receiver mapped')
        else:
            data = bytes(uc.mem_read(RECEIVER, 256))
            if constructor:
                x, y = struct.unpack_from('<ii', data, 8)
                dirty, mode = struct.unpack_from('<Ii', data, 116)
                assert data[4:8] == bytes(4) and data[16:116] == bytes(100)
                assert data[124:] == b'\xb7' * 132 and data[:4] != b'\xb7' * 4
                assert [event[0] for event in events] == (['ElementC2', 'memset'] if offscreen else ['memset'])
                expected = f'{x} {y} {dirty} {mode}'
            elif activation:
                dirty, mode = struct.unpack_from('<Ii', data, 116)
                assert data[:116] == b'\xb7' * 116 and data[124:] == b'\xb7' * 132
                expected = f'{dirty} {mode}'
            else:
                assert data[:4] != b'\xb7' * 4 and data[4:] == b'\xb7' * 252
                expected = 'retained'
        results.append({'input': case, 'expected': expected, 'events': events})
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', type=Path)
    parser.add_argument('--write', type=Path)
    args = parser.parse_args()
    read_map = json.loads(MAP.read_text())
    context = (PACKET / 'ELF_CONTEXT.md').read_text().split('## Typed relationships')[0]
    originals = []
    for match in ENTRY.finditer(context):
        sha, firmware, role, mangled, addr_hex, size_str, section, content, path, off_hex = match.groups()
        address, size, offset = int(addr_hex, 16), int(size_str), int(off_hex, 16)
        binding = read_map[path]
        data = Path(binding['frozen_read_path']).read_bytes()
        assert digest(data) == sha == binding['sha256']
        elf = ELFFile(io.BytesIO(data))
        text = elf.get_section_by_name(section)
        assert offset == text['sh_offset'] + address - text['sh_addr']
        assert address >= text['sh_addr'] and address + size <= text['sh_addr'] + text['sh_size']
        assert digest(data[offset:offset + size]) == content
        originals.append({'elf_sha256': sha, 'firmware': firmware, 'role': role, 'mangled': mangled,
                          'address': address, 'size': size, 'section': section, 'file_offset': offset,
                          'body_sha256': content, 'cases': run(elf, address, mangled, role)})
    assert originals
    result = json.loads(json.dumps({'originals': originals}))
    if args.check:
        assert result == json.loads(args.check.read_text())
    if args.write:
        args.write.write_text(json.dumps(result, indent=2) + '\n')
    print(f"{len(originals)} exact ELF ranges, {sum(len(row['cases']) for row in originals)} native executions")


if __name__ == '__main__':
    main()
