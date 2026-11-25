"""Verify and execute the exact DAWChannelGroup ARM ranges in both roles."""

from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
from struct import iter_unpack
import sys

from elftools.elf.elffile import ELFFile
from unicorn import UC_ARCH_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UC_MODE_ARM, Uc
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_SP

CAST_IDS = {0x44774347, 0x436c436f, 0x436f6d70}
PREFILLS = ((0x3000000, 0xa5), (0x3001000, 0x5a))


def digest(data):
    return sha256(data).hexdigest()


def read_virtual(elf, blob, address, count):
    for segment in elf.iter_segments(type='PT_LOAD'):
        delta = address - segment['p_vaddr']
        if 0 <= delta <= segment['p_filesz'] - count:
            offset = segment['p_offset'] + delta
            return blob[offset:offset + count]
    raise ValueError(f'No ELF file bytes at {address:#x}')


def observe(row):
    blob = Path(row['elf_path']).read_bytes()
    assert digest(blob) == row['elf']
    elf = ELFFile(BytesIO(blob))
    symbols = elf.get_section_by_name('.symtab')
    symbol, = symbols.get_symbol_by_name(row['mangled'])
    entry, size, index = row['address'], row['size'], row['section']
    assert (symbol['st_value'], symbol['st_size'], symbol['st_shndx']) == (entry, size, index)
    section = elf.get_section(index)
    delta = entry - section['sh_addr']
    offset = section['sh_offset'] + delta
    assert section.name == row['section_name'] and 0 <= delta <= section['sh_size'] - size
    body = blob[offset:offset + size]
    assert offset == row['file_offset'] and body.hex() == row['range_hex']
    assert digest(body) == row['range_sha256'] and read_virtual(elf, blob, entry, size) == body

    variant = 'cast' if row['mangled'].endswith('castToEi') else row['mangled'][-4:-2]
    ctor, d0 = variant.startswith('C'), variant == 'D0'
    targets = []
    vtable = name_address = None
    if variant != 'cast':
        # The last words are literals, outside the executed instruction range.
        words = [word for word, in iter_unpack('<I', body)]
        for index, word in enumerate(words[:-(2 if ctor else 1)]):
            if word >> 24 == 0xeb:
                displacement = (word & 0xffffff) - (0x1000000 if word & 0x800000 else 0)
                targets.append(entry + 4 * index + 8 + 4 * displacement)
        provider = ('_ZN8Presonus2UC15ClientComponentC2EPKc' if ctor
                    else '_ZN4Core8Portable9ComponentD2Ev')
        assert len(targets) == (2 if d0 else 1)
        assert any(s['st_value'] == targets[0] for s in symbols.get_symbol_by_name(provider))
        vtable = words[-1]
        vtable_name = ('_ZTVN8Presonus15DAWChannelGroupE' if ctor
                       else '_ZTVN8Presonus2UC15ClientComponentE')
        vtable_symbol, = symbols.get_symbol_by_name(vtable_name)
        assert vtable == vtable_symbol['st_value'] + 8
        if ctor:
            name_address = words[-2]
            assert read_virtual(elf, blob, name_address, 1) == bytes(1)
    relocation = None
    if d0:
        plt = elf.get_section_by_name('.plt')
        relocations = elf.get_section_by_name('.rel.plt')
        dynsym = elf.get_section(relocations['sh_link'])
        slot, alignment = divmod(targets[1] - plt['sh_addr'] - 20, 12)
        assert alignment == 0 and slot >= 0
        relocation_row = relocations.get_relocation(slot)
        assert dynsym.get_symbol(relocation_row['r_info_sym']).name == '_ZdlPv'
        relocation = dict(entry=targets[1], slot=slot, got=relocation_row['r_offset'],
                          name='_ZdlPv')

    def execute(receiver, sentinel, type_id):
        stack, stop = 0x4000800, 0x4001000
        cpu = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        pages = {receiver, stack & ~0xfff, stop, entry & ~0xfff,
                 (entry + size - 1) & ~0xfff, *(target & ~0xfff for target in targets)}
        if ctor:
            pages.add(name_address & ~0xfff)
        for page in pages:
            cpu.mem_map(page, 0x1000)
        cpu.mem_write(entry, body)
        if ctor:
            cpu.mem_write(name_address, read_virtual(elf, blob, name_address, 1))
        cpu.mem_write(receiver, bytes([sentinel]) * 256)
        cpu.reg_write(UC_ARM_REG_R0, receiver)
        cpu.reg_write(UC_ARM_REG_R1, type_id & 0xffffffff)
        cpu.reg_write(UC_ARM_REG_SP, stack)
        cpu.reg_write(UC_ARM_REG_LR, stop)
        calls, writes, pcs = [], [], []

        def on_code(u, address, width, _):
            if address in targets:
                assert u.reg_read(UC_ARM_REG_R0) == receiver
                if address == targets[0]:
                    if ctor:
                        assert u.reg_read(UC_ARM_REG_R1) == name_address
                        assert bytes(u.mem_read(name_address, 1)) == bytes(1)
                    else:
                        assert int.from_bytes(u.mem_read(receiver, 4), 'little') == vtable
                    calls.append(['client_construct' if ctor else 'component_destroy', address])
                else:
                    assert d0 and len(calls) == 1
                    u.mem_unmap(receiver, 0x1000)
                    calls.append(['delete', address])
                u.reg_write(UC_ARM_REG_PC, u.reg_read(UC_ARM_REG_LR))
            else:
                assert width == 4 and entry <= address < entry + size
                pcs.append(address)

        def on_write(_, __, address, width, value, ___):
            if receiver <= address < receiver + 256:
                writes.append([address - receiver, width, value])
            else:
                assert stack - 32 <= address < stack

        cpu.hook_add(UC_HOOK_CODE, on_code)
        cpu.hook_add(UC_HOOK_MEM_WRITE, on_write)
        cpu.emu_start(entry, stop, count=40)
        assert cpu.reg_read(UC_ARM_REG_PC) == stop and cpu.reg_read(UC_ARM_REG_SP) == stack
        result = cpu.reg_read(UC_ARM_REG_R0)
        if ctor:
            assert calls == [['client_construct', targets[0]]]
            assert writes == [[4, 4, vtable + 0x3c], [0x84, 4, 0], [0, 4, vtable]]
            assert bytes(cpu.mem_read(receiver + 0x80, 12)) == bytes([sentinel]) * 4 + bytes(4) + bytes([sentinel]) * 4
            assert result == receiver
            expected = 'client_construct empty cached_null'
        elif variant == 'cast':
            assert not calls and not writes
            assert result == (receiver if type_id in CAST_IDS else 0)
            expected = 'receiver' if result == receiver else 'null'
        else:
            assert writes == [[0, 4, vtable], [4, 4, vtable + 0x3c]]
            assert calls == [['component_destroy', targets[0]]] + ([['delete', targets[1]]] if d0 else [])
            assert result == receiver
            expected = ' '.join(call[0] for call in calls)
        mapped = any(start <= receiver <= end for start, end, _ in cpu.mem_regions())
        assert mapped != d0
        return dict(receiver=receiver, prefill=sentinel, type_id=type_id, result=result,
                    calls=calls, writes=writes, pcs=pcs, deallocated=not mapped,
                    expected=expected)

    ids = (sorted({-(2**31), -1, 0, 1, 2**31 - 1} |
                  {type_id + shift for type_id in CAST_IDS for shift in (-1, 0, 1)})
           if variant == 'cast' else [0])
    cases = [execute(receiver, sentinel, type_id)
             for receiver, sentinel in PREFILLS for type_id in ids]
    return dict(original=row, variant=variant, cases=cases, address_point=vtable,
                provider=dict(entry=targets[0], name=provider) if targets else None,
                name_address=name_address, delete_relocation=relocation)


def run(packet):
    return [observe(item['original']) for item in json.loads(Path(packet).read_text())['originals']]


if __name__ == '__main__':
    print(json.dumps(run(sys.argv[1]), indent=2))
