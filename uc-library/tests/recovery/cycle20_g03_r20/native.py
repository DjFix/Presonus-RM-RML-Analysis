"""Execute the exact two-role DigitalPot D0 and its actual Control D2 offline."""

import argparse
import hashlib
import json
from pathlib import Path
import struct

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UcError, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_ERR_READ_UNMAPPED, __version__
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_SP

D0 = '_ZN8Presonus5Panel17DigitalPotControlD0Ev'
D2 = '_ZN8Presonus5Panel7ControlD2Ev'
TABLE = '_ZTVN8Presonus5Panel17DigitalPotControlE'
CONTROL_TABLE = '_ZTVN8Presonus5Panel7ControlE'
OBSERVERS = '_ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE'
SURFACE = '304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
MIXER = '9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
PINS = {
    SURFACE: ('b7556b444e3aac14b50ac471d469fa325b5c7d90a492aee579e57102510b6daa',
              'caa73c96203be26583527fce60a1abad64ff7e0c85f4f6bc9f0775fe6f26cd65'),
    MIXER: ('88791faac187e67976ba11d82eb6f3877fb757aa4ad84342bf1f921328d555f3',
            'dbacde0d0523bbddad48b5e486dfe0302c4758f5f1977fc76d6e04a259c93c23'),
}


def exact(elf, name):
    [sym] = elf.get_section_by_name('.symtab').get_symbol_by_name(name)
    address, size, section_index = sym['st_value'], sym['st_size'], sym['st_shndx']
    section = elf.get_section(section_index)
    delta = address - section['sh_addr']
    assert size and 0 <= delta <= section['sh_size'] - size
    data = section.data()[delta:delta + size]
    return dict(mangled=name, address=address, size=size, section_index=section_index,
                section=section.name, file_offset=section['sh_offset'] + delta,
                sha256=hashlib.sha256(data).hexdigest()), data


def branch(data, entry, offset):
    instruction, = struct.unpack_from('<I', data, offset)
    assert instruction >> 24 == 0xeb
    displacement = (instruction & 0xffffff) * 4
    if displacement & 0x2000000:
        displacement -= 0x4000000
    return entry + offset + 8 + displacement


def delete_plt(elf, address):
    plt = elf.get_section_by_name('.plt')
    rel = elf.get_section_by_name('.rel.plt')
    syms = elf.get_section(rel['sh_link'])
    # The original ARM linker emits a 20-byte PLT resolver and 12-byte slots.
    assert plt['sh_size'] == 20 + 12 * rel.num_relocations()
    index, remainder = divmod(address - plt['sh_addr'] - 20, 12)
    assert not remainder and 0 <= index < rel.num_relocations()
    relocation = rel.get_relocation(index)
    assert relocation['r_info_type'] == 22
    assert syms.get_symbol(relocation['r_info_sym']).name == '_ZdlPv'
    return dict(address=address, relocation_address=relocation['r_offset'],
                symbol='_ZdlPv', relocation_kind='R_ARM_JUMP_SLOT')


def execute(path, expected):
    with path.open('rb') as inp:
        assert hashlib.file_digest(inp, 'sha256').hexdigest() == expected
        inp.seek(0)
        elf = ELFFile(inp)
        original, code = exact(elf, D0)
        parent, parent_code = exact(elf, D2)
        vtable, vtable_code = exact(elf, TABLE)
        control_vtable, _ = exact(elf, CONTROL_TABLE)
        unbind, _ = exact(elf, OBSERVERS)
        assert (original['sha256'], parent['sha256']) == PINS[expected]
        address = original['address']
        parent_address = parent['address']
        assert branch(code, address, 28) == parent_address
        delete = delete_plt(elf, branch(code, address, 36))
        assert all(branch(parent_code, parent_address, at) == unbind['address'] for at in (124, 144, 164))
    vt, = struct.unpack_from('<I', code, len(code) - 4)
    pvt, timers, _, _ = struct.unpack_from('<IIII', parent_code, len(parent_code) - 16)
    assert vt == vtable['address'] + 8
    assert struct.unpack_from('<I', vtable_code, 20)[0] == address
    assert pvt == control_vtable['address'] + 8
    cases = []
    receiver, stack, stop = 0x42000000, 0x43000000, 0x44000000
    parameters = [0x45000000 + 4096 * i for i in range(3)]
    for count in (0, 1, 3):
        cpu = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        entries = ((address, code), (parent_address, parent_code))
        pages = {a & ~4095 for a in (receiver, stack, stop, timers, unbind['address'], delete['address'], *parameters)}
        for at, data in entries:
            pages.update((at & ~4095, (at + len(data) - 1) & ~4095))
        for page in pages:
            cpu.mem_map(page, 4096)
        for at, data in entries:
            cpu.mem_write(at, data)

        def write(at, val):
            cpu.mem_write(at, struct.pack('<I', val))

        def read(at):
            return struct.unpack('<I', cpu.mem_read(at, 4))[0]

        writes = []
        events = []
        write(receiver, 0x55555555)
        bound = parameters[:count]
        for index, parameter in enumerate(bound):
            write(receiver + 8 + index * 4, parameter)

        def observe(arm, pc, size, ctx):
            this = arm.reg_read(UC_ARM_REG_R0)
            if pc == parent_address:
                assert this == receiver and read(receiver) == vt
                events.append('Control D2')
            elif address <= pc < address + len(code) - 4 or parent_address <= pc < parent_address + len(parent_code) - 16:
                return
            elif pc == unbind['address']:
                assert this in bound and arm.reg_read(UC_ARM_REG_R1) == receiver and read(receiver) == pvt
                events.append(f'removeObserver {parameters.index(this)}')
                bound.remove(this)
                arm.reg_write(UC_ARM_REG_PC, arm.reg_read(UC_ARM_REG_LR))
            elif pc == delete['address']:
                assert this == receiver and read(receiver) == pvt and read(receiver + 8) == 0 and not bound
                arm.mem_unmap(receiver, 4096)
                events.append('delete receiver')
                arm.reg_write(UC_ARM_REG_PC, arm.reg_read(UC_ARM_REG_LR))
            else:
                raise ValueError(f'Unmodeled native site {pc:#x}')

        from unicorn import UC_HOOK_MEM_WRITE
        def capture(cpu, access, at, size, value, ctx):
            if receiver <= at < receiver + 4096:
                writes.append((at - receiver, size, value))

        cpu.hook_add(UC_HOOK_CODE, observe)
        cpu.hook_add(UC_HOOK_MEM_WRITE, capture)
        for reg, value in ((UC_ARM_REG_R0, receiver), (UC_ARM_REG_SP, stack + 2048), (UC_ARM_REG_LR, stop)):
            cpu.reg_write(reg, value)
        cpu.emu_start(address, stop, count=300)
        assert cpu.reg_read(UC_ARM_REG_PC) == stop and cpu.reg_read(UC_ARM_REG_SP) == stack + 2048
        assert events == ['Control D2', *(f'removeObserver {n}' for n in range(count)), 'delete receiver']
        try:
            read(receiver)
        except UcError as error:
            assert error.errno == UC_ERR_READ_UNMAPPED
        else:
            raise AssertionError('Receiver stayed mapped after D0')
        cases.append(dict(bound_count=count, events=events, receiver_unmapped=True,
                          receiver_writes=[list(row) for row in writes]))
    return dict(elf_sha256=expected, original=original, control_d2=parent, original_vtable=vtable,
                remove_observer_boundary=unbind, delete_boundary=delete, native_cases=cases)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--surface', type=Path, required=True)
    parser.add_argument('--mixer', type=Path, required=True)
    parser.add_argument('--verify', type=Path)
    args = parser.parse_args()
    result = dict(unicorn_version=__version__, rows=[execute(args.surface, SURFACE), execute(args.mixer, MIXER)])
    if args.verify is None:
        print(json.dumps(result, indent=2))
    else:
        assert result == json.loads(args.verify.read_text())
        print('Verified six exact original D0 observations')


if __name__ == '__main__':
    main()
