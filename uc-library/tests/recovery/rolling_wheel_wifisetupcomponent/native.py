"""Run original wheel/scroll application instructions with modeled providers."""

import argparse
import hashlib
import itertools
import json
import struct
from pathlib import Path

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import (
    UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3,
    UC_ARM_REG_SP, UC_ARM_REG_PC, UC_ARM_REG_LR,
)

ELF = Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling-c001-20261124/packeting/next100-opportunistic02/snapshot/rootfs/CS18_v13840/home/root/surface')
SHA = '304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
NAME = '_ZN8Presonus7Surface18WifiSetupComponent12onWheelInputERKN4Core8Portable10WheelEventE'
SYMBOLS = {
    NAME: (0x9fc80, 24),
    '_ZN8Presonus7Surface18WifiSetupComponent13addListOffsetEi': (0x9fc34, 76),
    '_ZNK8Presonus7Surface18WifiSetupComponent16getMaxListOffsetEv': (0x9f1d0, 124),
    '_ZN8Presonus7Surface18WifiSetupComponent17updateDisplayListEv': (0x9faac, 392),
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def signed(value):
    return struct.unpack('<i', struct.pack('<I', value))[0]


def generate():
    data = ELF.read_bytes()
    assert sha(data) == SHA
    with ELF.open('rb') as file:
        elf = ELFFile(file)
        symbols = {s.name: s for s in elf.get_section_by_name('.symtab').iter_symbols()
                   if s.name in SYMBOLS}
        ranges = []
        for name, (address, size) in SYMBOLS.items():
            symbol = symbols[name]
            index = symbol['st_shndx']
            section = elf.get_section(index)
            assert (symbol['st_value'], symbol['st_size'], index) == (address, size, 12)
            assert section.name == '.text'
            offset = section['sh_offset'] + address - section['sh_addr']
            ranges.append(dict(mangled=name, address=address, size=size, section=section.name,
                               section_index=index, file_offset=offset,
                               range_sha256=sha(data[offset:offset + size])))
    assert ranges[0]['range_sha256'] == 'c543770e8ad2ce3722e585441de30813eeb0c563236d775c584cdd0a5f580795'
    cases = itertools.product([0, 3, 5, 11], [-20, -2, 0, 2, 20], [1, 7, 12], [0, 1], [0, 1])
    return dict(elf_sha256=SHA, ranges=ranges,
                cases=[run(case, ranges) for case in cases])


def run(case, ranges):
    offset, delta, count, visible, axis = case
    vm = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    vm.mem_map(0x1000, 0x800000)
    # Load the ELF image for passive data/literal reads. The code hook admits
    # only the four exact app ranges and returns directly from modeled providers.
    with ELF.open('rb') as file:
        for segment in ELFFile(file).iter_segments():
            if segment['p_type'] == 'PT_LOAD':
                vm.mem_write(segment['p_vaddr'], segment.data())
    receiver, event, stack, stop = 0x500000, 0x510000, 0x7f0000, 0x7ff000
    parameters = {tag: 0x540000 + i * 0x100
                  for i, tag in enumerate([0, *range(100, 110)])}
    tags = {pointer: tag for tag, pointer in parameters.items()}

    def word(address, value):
        vm.mem_write(address, struct.pack('<I', value & 0xffffffff))

    def read(address):
        return struct.unpack('<I', vm.mem_read(address, 4))[0]

    def floating(value):
        return struct.unpack('<f', struct.pack('<I', value))[0]

    def bits(value):
        return struct.unpack('<I', struct.pack('<f', value))[0]

    def ret(value=None):
        if value is not None:
            vm.reg_write(UC_ARM_REG_R0, value & 0xffffffff)
        vm.reg_write(UC_ARM_REG_PC, vm.reg_read(UC_ARM_REG_LR))

    word(receiver + 0x118, offset)
    word(receiver + 0x11c, 3)
    word(event, delta)
    word(event + 4, axis)
    for pointer, tag in tags.items():
        word(pointer, 0x400000)
        word(pointer + 12, pointer + 64)
        word(pointer + 68, tag)
    for slot in (0x24, 0x3c, 0x58, 0x74):
        word(0x400000 + slot, 0x410000 + slot)
    output, calls, writes, forwarded = [], [], [], []

    def hook(uc, pc, _size, _):
        if pc == stop:
            vm.emu_stop()
            return
        a, b, c, d = (vm.reg_read(reg) for reg in
                      (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3))
        if pc == 0x9fc34:
            assert a == receiver and vm.reg_read(UC_ARM_REG_SP) == stack
            assert vm.reg_read(UC_ARM_REG_LR) == stop
            forwarded.append(signed(b))
        if any(row['address'] <= pc < row['address'] + row['size'] for row in ranges):
            return
        calls.append(pc)
        if pc in (0x11acf0, 0x11f24c):
            ret(parameters.get(signed(b), 0))
        elif pc == 0xae58:
            assert a == parameters[0]
            ret(a)
        elif pc == 0x41003c:
            ret(bits(count - 1))
        elif pc == 0x410074:
            label = bytes(vm.mem_read(b, 32)).split(b'\0', 1)[0].decode() or '-'
            output.append(f'T {tags[a]} {c} {label}')
            ret()
        elif pc == 0x410058:
            output.append(f'V {tags[a]} {int(floating(b))} {c}')
            ret()
        elif pc == 0x410024:
            output.append(f'E {tags[a]} {b}')
            ret()
        elif pc == 0x1877f8:
            ret(int(floating(a)))
        elif pc == 0x681d4:
            ret(visible)
        elif pc in (0x24268, 0x11e78):
            vm.mem_write(a, b'\0')
            ret(a)
        elif pc == 0x12142c:
            index = signed(d)
            vm.mem_write(b, (f'net{index}' if 0 <= index < count else '').encode() + b'\0')
            ret()
        else:
            raise AssertionError(f'unmodeled provider {pc:#x}')

    def write(uc, _access, address, size, value, _):
        if receiver <= address < receiver + 0x200:
            writes.append([address - receiver, size, value])

    vm.hook_add(UC_HOOK_CODE, hook)
    vm.hook_add(UC_HOOK_MEM_WRITE, write)
    for reg, value in ((UC_ARM_REG_R0, receiver), (UC_ARM_REG_R1, event),
                       (UC_ARM_REG_SP, stack), (UC_ARM_REG_LR, stop)):
        vm.reg_write(reg, value)
    vm.emu_start(ranges[0]['address'], stop, count=2000)
    assert vm.reg_read(UC_ARM_REG_PC) == stop and forwarded == [delta]
    assert vm.reg_read(UC_ARM_REG_SP) == stack and signed(read(event)) == delta
    assert read(event + 4) == axis
    output.append(f'S {signed(read(receiver + 0x118))} {signed(read(receiver + 0x11c))} {delta} {axis}')
    return dict(input=case, output=output, forwarded=forwarded, provider_calls=calls,
                receiver_writes=writes)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('fixture', type=Path)
    parser.add_argument('--record', action='store_true')
    args = parser.parse_args()
    current = generate()
    encoded = json.dumps(current, indent=2) + '\n'
    if args.record:
        args.fixture.write_text(encoded)
    else:
        assert args.fixture.read_text() == encoded, 'fresh ARM replay mismatch'
    print(f"{len(current['cases'])} original ARM cases")


if __name__ == '__main__':
    main()
