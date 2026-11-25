"""Execute exact DAWChannel ARM ranges, stopping only at verified Core/allocator boundaries."""
from functools import cache
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
from struct import iter_unpack, pack, unpack
import sys

from elftools.elf.elffile import ELFFile
from unicorn import UC_ARCH_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UC_MODE_ARM, Uc
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_SP

IDS = (0x44617743, 0x436c436f, 0x436f6d70)
CAST_INPUT = (-(2**31), -1, 0, 2**31 - 1, *(v for i in IDS for v in (i - 1, i, i + 1)))
CLIENT_CTOR = '_ZN8Presonus2UC15ClientComponentC2EPKc'
CORE_CTOR = '_ZN4Core8Portable9ComponentC2EPKc'
CORE_DTOR = '_ZN4Core8Portable9ComponentD2Ev'
DAW_VTABLE = '_ZTVN8Presonus10DAWChannelE'
BASE_VTABLE = '_ZTVN8Presonus2UC15ClientComponentE'


@cache
def symbol_table(elf):
    return elf.get_section_by_name('.symtab')


def symbol(elf, name):
    sym, = symbol_table(elf).get_symbol_by_name(name)
    return sym


def branch_targets(body, start):
    for i, (word,) in enumerate(iter_unpack('<I', body)):
        if word >> 24 == 0xeb:
            delta = (word & 0xffffff) - (0x1000000 if word & 0x800000 else 0)
            yield start + i * 4 + 8 + delta * 4


def symbol_range(elf, sym):
    section = elf.get_section(sym['st_shndx'])
    delta = sym['st_value'] - section['sh_addr']
    size = sym['st_size']
    assert section.name == '.text' and 0 <= delta <= section['sh_size'] - size
    return section['sh_offset'] + delta, section.data()[delta:delta + size]


def load_image(cpu, elf):
    mapped = set()
    for segment in elf.iter_segments(type='PT_LOAD'):
        start = segment['p_vaddr']
        for page in range(start & ~0xfff, start + segment['p_memsz'], 0x1000):
            if page not in mapped:
                cpu.mem_map(page, 0x1000)
                mapped.add(page)
        cpu.mem_write(start, segment.data())


def execute(elf, entry, size, ctor, cast, base, core, delete,
            receiver, prefill, input_id):
    stack, stop = 0x4000800, 0x4001000
    cpu = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    load_image(cpu, elf)
    for page in (receiver, stack & ~0xfff, stop):
        cpu.mem_map(page, 0x1000)
    cpu.mem_write(receiver, bytes([prefill]) * 256)
    cpu.reg_write(UC_ARM_REG_R0, receiver)
    cpu.reg_write(UC_ARM_REG_R1, input_id & 0xffffffff)
    cpu.reg_write(UC_ARM_REG_SP, stack)
    cpu.reg_write(UC_ARM_REG_LR, stop)
    events, writes, pcs = [], [], []
    daw_vptr = symbol(elf, DAW_VTABLE)['st_value'] + 8
    base_vptr = symbol(elf, BASE_VTABLE)['st_value'] + 8
    if not ctor and not cast:
        cpu.mem_write(receiver, pack('<II', daw_vptr, daw_vptr + 0x3c))

    def on_code(u, address, width, _):
        assert width == 4
        r0 = u.reg_read(UC_ARM_REG_R0)
        if ctor and address == base[0]:
            assert r0 == receiver
            events.append('client_component_construct')
        if core is not None and address == core:
            assert r0 == receiver
            if ctor:
                name_pointer = u.reg_read(UC_ARM_REG_R1)
                assert u.mem_read(name_pointer, 1) == b'\0'
                events.append('core_component_construct_empty')
            else:
                assert unpack('<II', u.mem_read(receiver, 8)) == (base_vptr, base_vptr + 0x3c)
                events.append('core_component_destroy')
            u.reg_write(UC_ARM_REG_PC, u.reg_read(UC_ARM_REG_LR))
        elif delete is not None and address == delete:
            assert r0 == receiver and events == ['core_component_destroy']
            u.mem_unmap(receiver, 0x1000)
            events.append('unsized_delete')
            u.reg_write(UC_ARM_REG_PC, u.reg_read(UC_ARM_REG_LR))
        else:
            assert entry <= address < entry + size or (
                ctor and base[0] <= address < base[0] + base[1])
            pcs.append(address)

    def on_write(_, __, address, width, value, ___):
        if receiver <= address < receiver + 256:
            writes.append([address - receiver, width, value])
        else:
            assert stack - 128 <= address < stack

    cpu.hook_add(UC_HOOK_CODE, on_code)
    cpu.hook_add(UC_HOOK_MEM_WRITE, on_write)
    cpu.emu_start(entry, stop, count=80)
    assert cpu.reg_read(UC_ARM_REG_PC) == stop and cpu.reg_read(UC_ARM_REG_SP) == stack
    result = cpu.reg_read(UC_ARM_REG_R0)
    mapped = any(lo <= receiver <= hi for lo, hi, _ in cpu.mem_regions())
    assert mapped == (delete is None)
    if ctor:
        assert events == ['client_component_construct', 'core_component_construct_empty']
        assert writes == [[0, 4, base_vptr], [4, 4, base_vptr + 0x3c],
                          [4, 4, daw_vptr + 0x3c], [0x8c, 4, 0], [0, 4, daw_vptr],
                          [0x84, 4, 0], [0x88, 4, 0]]
        assert result == receiver
        portable = 'constructed empty null-caches'
    elif cast:
        assert not events and not writes
        assert result == (receiver if input_id in IDS else 0)
        portable = 'receiver' if result else 'null'
    else:
        assert writes == [[0, 4, base_vptr], [4, 4, base_vptr + 0x3c]]
        assert events == ['core_component_destroy'] + ([] if mapped else ['unsized_delete'])
        assert result == receiver
        portable = 'child parameter ' + ('unsized-delete' if not mapped else 'retained')
    return dict(receiver=receiver, prefill=prefill, input_id=input_id,
                calls=events, writes=writes, pcs=pcs, deallocated=not mapped,
                result=result, portable=portable)


def observe(row):
    blob = Path(row['elf_path']).read_bytes()
    assert sha256(blob).hexdigest() == row['elf']
    elf = ELFFile(BytesIO(blob))
    sym = symbol(elf, row['mangled'])
    entry, size = row['address'], row['size']
    assert (sym['st_value'], sym['st_size'], sym['st_shndx']) == (entry, size, row['section'])
    offset, body = symbol_range(elf, sym)
    assert offset == row['file_offset'] and body.hex() == row['range_hex']
    assert sha256(body).hexdigest() == row['range_sha256']
    variant = row['mangled'].removeprefix('_ZN8Presonus10DAWChannel')
    ctor, cast = variant.startswith('C'), variant == '6castToEi'
    targets = tuple(branch_targets(body, entry))
    base = core = delete = None
    boundaries = []
    if ctor:
        s = symbol(elf, CLIENT_CTOR)
        base = (s['st_value'], s['st_size'])
        base_offset, base_body = symbol_range(elf, s)
        assert targets == (base[0],)
        core = symbol(elf, CORE_CTOR)['st_value']
        assert tuple(branch_targets(base_body, base[0])) == (core,)
        boundaries += [dict(name=CLIENT_CTOR, address=base[0], file_offset=base_offset,
                            size=base[1], sha256=sha256(base_body).hexdigest()),
                       dict(name=CORE_CTOR, address=core)]
    elif not cast:
        core = symbol(elf, CORE_DTOR)['st_value']
        boundaries.append(dict(name=CORE_DTOR, address=core))
        assert len(targets) == (2 if variant == 'D0Ev' else 1) and targets[0] == core
        if variant == 'D0Ev':
            delete = targets[1]
            plt = elf.get_section_by_name('.plt')
            relocs = elf.get_section_by_name('.rel.plt')
            symbols = elf.get_section(relocs['sh_link'])
            slot, align = divmod(delete - plt['sh_addr'] - 20, 12)
            assert not align and slot >= 0
            relocation = relocs.get_relocation(slot)
            assert symbols.get_symbol(relocation['r_info_sym']).name == '_ZdlPv'
            boundaries.append(dict(name='_ZdlPv', address=delete, slot=slot,
                                   got=relocation['r_offset']))
    else:
        assert not targets
    cases = [execute(elf, entry, size, ctor, cast, base, core, delete, receiver, prefill, value)
             for receiver, prefill in ((0x3000000, 0xa5), (0x3001000, 0x5a))
             for value in (CAST_INPUT if cast else (0,))]
    return dict(original=row, boundaries=boundaries, cases=cases)


def run(packet):
    return [observe(item['original']) for item in json.loads(packet.read_text())['originals']]


if __name__ == '__main__':
    print(json.dumps(run(Path(sys.argv[1])), indent=2))
