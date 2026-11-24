"""Replay the sealed ARM body offline; no device or external stubs."""
import hashlib
import io
import json
import pathlib
import struct
import sys

import capstone
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_SP

TASK = 'sqlite01_frontpanel_geq_range'
PACKET = pathlib.Path('temp/recovery-work/sqlite-issued/prepared-eight') / TASK / 'CONTEXT.json'
PROJECT = pathlib.Path('/home/rs/projects/opencs/ai-line-analysis')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def symbol_bytes(elf, entry):
    section = elf.get_section(entry['st_shndx'])
    start = entry['st_value'] - section['sh_addr']
    assert 0 <= start < start + entry['st_size'] <= section['sh_size']
    return section, section['sh_offset'] + start, section.data()[start:start + entry['st_size']]


def inspect_slot(elf, symbols):
    peers = {}
    for owner in ('19FrontPanelComponent', '24BeastFrontPanelComponent',
                  '24RogueFrontPanelComponent'):
        scope = 'N8Presonus5Panel' + owner
        table = symbols.get_symbol_by_name('_ZTV' + scope + 'E')[0]
        method = symbols.get_symbol_by_name('_Z' + scope + '17checkGeqViewRangeEv')[0]
        _, _, data = symbol_bytes(elf, table)
        target, = struct.unpack_from('<I', data, 8 + 0x98)
        assert target == method['st_value']
        peers[owner] = dict(vtable=table['st_value'], slot=0x98, target=target)

    decoder = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_ARM)
    callers = {}
    for spelling in ('19updateGeqBandSelect', '11doGeqUpdate'):
        name = '_ZN8Presonus5Panel19FrontPanelComponent' + spelling + 'Ev'
        entry = symbols.get_symbol_by_name(name)[0]
        _, _, data = symbol_bytes(elf, entry)
        instructions = list(decoder.disasm_lite(data, entry['st_value']))
        index, = [i for i, row in enumerate(instructions)
                  if row[2:] == ('ldr', 'pc, [r3, #0x98]')]
        callers[name] = [list(row) for row in instructions[index - 3:index + 3]]

    return peers, callers


def execute(address, code, vptr, offset, selected):
    machine = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    machine.mem_map(address & ~0xfff, 0x1000)
    machine.mem_write(address, code)
    receiver, stack, sentinel = 0x100100, 0x200800, 0x300000
    for base in (0x100000, 0x200000, sentinel):
        machine.mem_map(base, 0x1000)
    seeded = bytearray([0xA7] * 0x1000)
    struct.pack_into('<I', seeded, 0x100, vptr)
    # Distinct synthetic state markers. Neither is interpreted as a native field.
    struct.pack_into('<II', seeded, 0x260, offset, selected)
    machine.mem_write(0x100000, bytes(seeded))
    machine.mem_write(0x200000, bytes([0x5C]) * 0x1000)
    accesses = []
    machine.hook_add(
        UC_HOOK_MEM_READ | UC_HOOK_MEM_WRITE,
        lambda _, kind, addr, size, value, __: accesses.append([kind, addr, size]),
    )
    machine.reg_write(UC_ARM_REG_R0, receiver)
    machine.reg_write(UC_ARM_REG_LR, sentinel)
    machine.reg_write(UC_ARM_REG_SP, stack)
    machine.emu_start(address, sentinel, count=16)
    assert machine.reg_read(UC_ARM_REG_PC) == sentinel
    assert machine.reg_read(UC_ARM_REG_SP) == stack
    assert all(stack - 16 <= addr and addr + size <= stack for _, addr, size in accesses)
    assert machine.mem_read(stack, 16) == bytes([0x5C]) * 16
    assert machine.mem_read(stack - 32, 16) == bytes([0x5C]) * 16
    return dict(offset=offset, selected=selected,
                result=machine.reg_read(UC_ARM_REG_R0),
                receiver_preserved=machine.mem_read(0x100000, 0x1000) == seeded,
                stack_accesses=accesses)


def observe():
    packet = json.loads(PACKET.read_text())
    target = packet['originals'][0]['original']
    binary = pathlib.Path(target['elf_path'])
    if not binary.is_file():
        binary = PROJECT / binary
    image = binary.read_bytes()
    assert digest(image) == target['elf']
    elf = ELFFile(io.BytesIO(image))
    assert elf['e_machine'] == 'EM_ARM' and elf.little_endian
    symbols = elf.get_section_by_name('.symtab')
    entry, = symbols.get_symbol_by_name(target['mangled'])
    section, offset, code = symbol_bytes(elf, entry)
    assert entry['st_info']['type'] == 'STT_FUNC'
    assert entry['st_value'] == target['address']
    assert entry['st_size'] == target['size']
    assert entry['st_shndx'] == target['section']
    assert section.name == target['section_name']
    assert offset == target['file_offset'] and image[offset:offset + len(code)] == code
    assert digest(code) == target['range_sha256']
    assert code.hex() == target['range_hex']
    peers, callers = inspect_slot(elf, symbols)
    vptr = peers['19FrontPanelComponent']['vtable'] + 8
    cases = [execute(target['address'], code, vptr, *state)
             for state in ((0, 0), (15, 30))]
    return dict(original=target, vtables=peers, callers=callers, cases=cases)


if __name__ == '__main__':
    json.dump(observe(), sys.stdout, indent=2)
    print()
