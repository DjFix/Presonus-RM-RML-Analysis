"""Execute the exact StartPage and Page application ranges on ARM."""
import hashlib
from pathlib import Path
import struct

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import (
    UC_ARM_REG_R0 as R0, UC_ARM_REG_R1 as R1, UC_ARM_REG_R2 as R2, UC_ARM_REG_R3 as R3,
    UC_ARM_REG_SP as SP, UC_ARM_REG_LR as LR, UC_ARM_REG_PC as PC,
)

ELF_HASH = '304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
TARGET = '_ZN8Presonus7Surface18StartPageComponent{}EPKcS3_i'
RANGES = {
    'C1': '5fd0f15ecb7773214ff18e348e8d39a286eda2f377ff42d7e09b92ca40a8da63',
    'C2': '31f03af88f8caf661c7c582de55fb07b38cf7678f250cab38aa2811ac2b1c444',
}
PAGE = '_ZN8Presonus13PageComponentC2EPKcS2_i'
DESCRIPTOR = '_ZZN8Presonus7Surface18StartPageComponentC1EPKcS3_iE9ParamList'
ADD = '_ZN4Core8Portable9ParamList3addEPKNS0_9ParamInfoEib'


def symbol(elf, name):
    [entry] = elf.get_section_by_name('.symtab').get_symbol_by_name(name)
    address, size, index = (entry[k] for k in ('st_value', 'st_size', 'st_shndx'))
    section = elf.get_section(index)
    relative = address - section['sh_addr']
    assert 0 <= relative <= section['sh_size'] - size and size
    data = section.data()[relative:relative + size]
    return {
        'mangled': name, 'address': address, 'size': size, 'section_index': index,
        'section': section.name, 'file_offset': section['sh_offset'] + relative,
        'sha256': hashlib.sha256(data).hexdigest(),
    }, data


def run(target, page, descriptor, add, name, form, tag):
    receiver, name_ptr, form_ptr, stack, stop = range(0x25000000, 0x25500000, 0x100000)
    core_ctor, string_ctor = 0x11af30, 0x24268
    cpu = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    entries = [(item[0]['address'], item[1]) for item in (target, page, descriptor)]
    entries += [(name_ptr, name.encode() + b'\0'), (form_ptr, form.encode() + b'\0')]
    pages = {x & ~4095 for x in (receiver, stack, core_ctor, string_ctor, add, stop)}
    for address, data in entries:
        pages.update(range(address & ~4095, ((address + len(data) - 1) & ~4095) + 4096, 4096))
    for address in pages:
        cpu.mem_map(address, 4096)
    for address, data in entries:
        cpu.mem_write(address, data)
    cpu.mem_write(receiver, bytes([0x93]) * 256)

    calls, writes = [], []
    def hook(m, address, size, _):
        args = [m.reg_read(r) for r in (R0, R1, R2, R3)]
        if address == page[0]['address']:
            assert args == [receiver, name_ptr, form_ptr, tag & 0xffffffff]
            calls.append(PAGE)
            return
        if address == core_ctor:
            assert args[:2] == [receiver, name_ptr]
            calls.append('CCL Component constructor')
        elif address == string_ctor:
            assert args[:2] == [receiver + 0x90, form_ptr]
            calls.append('CCL CString32 constructor')
        elif address == add:
            assert args == [receiver + 0x28, descriptor[0]['address'], 2, 0]
            assert bytes(m.mem_read(args[1], len(descriptor[1]))) == descriptor[1]
            assert bytes(m.mem_read(args[0], 1)) == b'\x01'
            calls.append(ADD)
        else:
            assert any(item[0]['address'] <= address < item[0]['address'] + item[0]['size']
                       for item in (target, page)), hex(address)
            return
        m.reg_write(PC, m.reg_read(LR))

    def observe_write(_cpu, _access, address, size, value, _):
        if receiver <= address < receiver + 256:
            writes.append([address - receiver, size, value & ((1 << (8 * size)) - 1)])

    cpu.hook_add(UC_HOOK_CODE, hook)
    cpu.hook_add(UC_HOOK_MEM_WRITE, observe_write)
    for reg, value in zip((R0, R1, R2, R3, SP, LR),
                          (receiver, name_ptr, form_ptr, tag & 0xffffffff, stack + 2048, stop)):
        cpu.reg_write(reg, value)
    cpu.emu_start(target[0]['address'], stop, count=200)
    assert (cpu.reg_read(PC), cpu.reg_read(SP), cpu.reg_read(R0)) == (stop, stack + 2048, receiver)
    assert calls == [PAGE, 'CCL Component constructor', 'CCL CString32 constructor', ADD]
    assert struct.unpack('<i', cpu.mem_read(receiver + 0x8c, 4))[0] == tag
    return dict(name=name, form=form, tag=tag, calls=calls, writes=writes)


def generate(variant):
    path = Path('rootfs/CS18_v13840/home/root/surface')
    with path.open('rb') as stream:
        assert hashlib.file_digest(stream, 'sha256').hexdigest() == ELF_HASH
        stream.seek(0)
        elf = ELFFile(stream)
        target, page, descriptor = (symbol(elf, n) for n in (TARGET.format(variant), PAGE, DESCRIPTOR))
        assert target[0]['sha256'] == RANGES[variant]
        assert page[0]['sha256'] == '1c2691d428d80ff128981fc02501a5063dc7783acdb9e4fb0ecceaf483745914'
        [add] = elf.get_section_by_name('.symtab').get_symbol_by_name(ADD)
        block = descriptor[1]
        assert len(block) == 168
        rows = []
        for kind, tag, name, lo, hi, mid, default, delta, flags, *extra in struct.iter_unpack('<ii32s5fi5I', block):
            rows.append(dict(type=kind, tag=tag, name=name.rstrip(b'\0').decode(), min=lo,
                             max=hi, mid=mid, default=default, delta=delta, flags=flags, extra=extra))
        cases = [run(target, page, descriptor, add['st_value'], *case) for case in [
            ('', '', 0), ('Start', 'Start Form', 199),
            ('Long page', '0123456789abcdefghijklmnopqrstuvwxyz', -17),
        ]]
    return dict(elf_sha256=ELF_HASH, original=target[0], page=page[0], descriptor=descriptor[0],
                add_address=add['st_value'], rows=rows, cases=cases)
