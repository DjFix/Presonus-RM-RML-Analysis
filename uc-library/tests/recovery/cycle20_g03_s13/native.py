"""Observe exact application constructors and original typed Page owner query."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, __version__
from unicorn.arm_const import UC_ARM_REG_R0 as R0, UC_ARM_REG_R1 as R1, UC_ARM_REG_R2 as R2
from unicorn.arm_const import UC_ARM_REG_R3 as R3, UC_ARM_REG_SP as SP, UC_ARM_REG_LR as LR, UC_ARM_REG_PC as PC

FADER = True
ORIGINALS = {'_ZN8Presonus7Surface18FaderUtilitiesPageC1EPKci': '6fbb41b272a932735fa173f312b96cb834a277d2821c5391044b793ebc7c99bc', '_ZN8Presonus7Surface18FaderUtilitiesPageC2EPKci': '71ea5406390f29ed4dd1f47c3184ba8aa6230d1236301d951928ae8beadfe4d9'}
ELF_HASH = '304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
PAGE_C2 = '_ZN8Presonus13PageComponentC2EPKcS2_i'


def exact(elf, name):
    [sym] = elf.get_section_by_name('.symtab').get_symbol_by_name(name)
    address, size, idx = sym['st_value'], sym['st_size'], sym['st_shndx']
    section = elf.get_section(idx)
    rel = address - section['sh_addr']
    assert size and 0 <= rel <= section['sh_size'] - size
    data = section.data()[rel:rel + size]
    return dict(mangled=name, address=address, size=size, section_index=idx, section=section.name,
                file_offset=section['sh_offset'] + rel, sha256=hashlib.sha256(data).hexdigest()), data


def read_literal(elf, address):
    for section in elf.iter_sections():
        rel = address - section['sh_addr']
        if section['sh_flags'] & 2 and 0 <= rel < section['sh_size']:
            literal, end, _ = section.data()[rel:rel + 64].partition(b'\0')
            assert end
            return literal
    raise ValueError('Unmapped original descriptor literal')


def call(data, entry, offset):
    opcode, = struct.unpack_from('<I', data, offset)
    assert opcode >> 24 == 0xeb
    delta = (opcode & 0xffffff) << 2
    return entry + offset + 8 + (delta - ((delta & 0x2000000) << 1))


def replay(original, code, parent, parent_code, name, form, tag, lookup, cast, vtable, descriptor):
    receiver, owner, name_address, form_address, stack, stop = [0x25000000 + i * 0x100000 for i in range(6)]
    main_page, main_page_code = lookup
    owner_cast, cast_code = cast
    owner_vtable, owner_vtable_code = vtable
    entry = original['address']
    if FADER:
        base = parent['address']
        assert call(code, entry, 32) == base
        name_address, vptr = struct.unpack_from('<II', code, 68)
        name = descriptor
        dispatch_state = [vptr, vptr + 0x3c, vptr + 0x4c]
    else:
        base, parent_code = entry, code
        primary, secondary, tertiary = struct.unpack_from('<III', code, 84)
        dispatch_state = [primary, secondary, tertiary]
    core = call(parent_code, base, 28)
    form_copy = call(parent_code, base, 80)
    assert (core, form_copy) == (0x11af30, 0x24268)

    m = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    entries = [(entry, code), (main_page['address'], main_page_code),
               (owner_cast['address'], cast_code), (owner_vtable['address'], owner_vtable_code),
               (name_address, name + b'\0'), (form_address, form + b'\0')]
    if FADER:
        entries.append((base, parent_code))
    pages = {a & ~4095 for a in (receiver, owner, stack, stop, core, form_copy)}
    for address, blob in entries:
        pages.update((address & ~4095, (address + len(blob) - 1) & ~4095))
    for page in pages:
        m.mem_map(page, 4096)
    for address, blob in entries:
        m.mem_write(address, blob)
    m.mem_write(receiver, b'\x93' * 256)
    m.mem_write(owner, struct.pack('<I', owner_vtable['address'] + 8))

    events = []
    def probe(cpu, address, size, ctx):
        this, arg = cpu.reg_read(R0), cpu.reg_read(R1)
        if FADER and address == base:
            assert (this, arg, cpu.reg_read(R2), cpu.reg_read(R3)) == (receiver, name_address, form_address, tag)
            events.append('original Page C2')
        elif address == core:
            assert (this, arg) == (receiver, name_address)
            cpu.mem_write(receiver + 0x50, bytes(4))
            events.append('modeled Component constructor boundary')
            cpu.reg_write(PC, cpu.reg_read(LR))
        elif address == form_copy:
            assert (this, arg) == (receiver + 0x90, form_address)
            events.append('modeled CString32 constructor boundary')
            cpu.reg_write(PC, cpu.reg_read(LR))
        elif address == owner_cast['address']:
            assert this == owner and arg == 1296843588
            events.append('real MainLCD cast')
        elif not any(at <= address < at + len(data) for at, data in entries):
            raise ValueError(f'Unreviewed instruction site {address:#x}')

    m.hook_add(UC_HOOK_CODE, probe)
    regs = ((R0, receiver), (R1, form_address if FADER else name_address),
            (R2, tag if FADER else form_address), (R3, tag), (SP, stack + 2048), (LR, stop))
    for reg, value in regs:
        m.reg_write(reg, value)
    m.emu_start(entry, stop, count=150)
    assert (m.reg_read(PC), m.reg_read(SP), m.reg_read(R0)) == (stop, stack + 2048, receiver)
    assert m.mem_read(receiver + 0x88, 2) == bytes(2)
    read = lambda offset: struct.unpack('<I', m.mem_read(receiver + offset, 4))[0]
    assert read(0x8c) == tag and read(0x50) == 0
    writes = {str(offset): read(offset) for offset in (0, 4, 0x84)}
    if FADER:
        assert list(writes.values()) == dispatch_state
    expected_calls = (['original Page C2'] if FADER else []) + [
        'modeled Component constructor boundary', 'modeled CString32 constructor boundary']
    assert events == expected_calls
    queries = []
    for parent_pointer in (0, owner):
        m.mem_write(receiver + 0x50, struct.pack('<I', parent_pointer))
        m.reg_write(R0, receiver)
        m.reg_write(LR, stop)
        m.emu_start(main_page['address'], stop, count=90)
        assert m.reg_read(PC) == stop and m.reg_read(R0) == parent_pointer
        queries.append(bool(parent_pointer))
    assert events == [*expected_calls, 'real MainLCD cast']
    tag_signed = struct.unpack('<i', struct.pack('<I', tag))[0]
    return dict(tag=tag_signed, name=name.decode(), form=form.decode(), calls=events,
                original_vptr_writes=writes, owner_queries=queries)


def run(path):
    with path.open('rb') as stream:
        assert hashlib.file_digest(stream, 'sha256').hexdigest() == ELF_HASH
        stream.seek(0)
        elf = ELFFile(stream)
        lookup = exact(elf, '_ZNK8Presonus13PageComponent13getMainScreenEv')
        cast = exact(elf, '_ZN8Presonus16MainLCDComponent6castToEi')
        vtable = exact(elf, '_ZTVN8Presonus16MainLCDComponentE')
        assert struct.unpack_from('<I', vtable[1], 8)[0] == cast[0]['address']
        parent, parent_code = exact(elf, PAGE_C2)
        rows = []
        for name, pin in ORIGINALS.items():
            original, code = exact(elf, name)
            assert original['sha256'] == pin
            descriptor = read_literal(elf, struct.unpack_from('<I', code, 68)[0]) if FADER else None
            if FADER:
                assert descriptor == b'faderUtilititesPage'
            cases = [(b'Page A', b'Form A', 17), (b'', b'', 0),
                     (b'Page Long', b'01234567890123456789012345678901234', 0xffffffff)]
            observations = [replay(original, code, parent, parent_code, component, form,
                                   tag, lookup, cast, vtable, descriptor) for component, form, tag in cases]
            rows.append(dict(elf_sha256=ELF_HASH, original=original, native_cases=observations))
    assert rows[0]['native_cases'] == rows[1]['native_cases']
    expected = [f"{c['name']}|{c['form'][:31]}|{c['tag']}|owner=attached" for c in rows[0]['native_cases']]
    return dict(rows=rows, unicorn_version=__version__, native_page_c2=parent,
                native_lookup=lookup[0], native_owner_cast=cast[0], native_owner_vtable=vtable[0],
                portable_expected=expected)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--elf', type=Path, required=True)
    parser.add_argument('--verify', type=Path)
    args = parser.parse_args()
    receipt = run(args.elf)
    if args.verify:
        assert receipt == json.loads(args.verify.read_text())
        print('Verified independent original constructors and owner queries')
    else:
        print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
