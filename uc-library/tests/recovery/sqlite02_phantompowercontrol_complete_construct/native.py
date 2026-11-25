"""Execute the exact packet bodies offline and record their observations."""
import hashlib
import io
import json
from pathlib import Path
import struct
import sys

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_MEM_WRITE
from unicorn.arm_const import (
    UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1,
    UC_ARM_REG_R2, UC_ARM_REG_SP,
)

TASK = Path(__file__).resolve().parent.name
PACKET = Path('temp/recovery-work/sqlite-issued/packet') / TASK / 'CONTEXT.json'
PROJECT = Path('/home/rs/projects/opencs/ai-line-analysis')
WHEEL = TASK.endswith('_wheel')
LCD = '_lcddisplaycontrol_' in TASK


def digest(data):
    return hashlib.sha256(data).hexdigest()


def extract(elf, symbols, name):
    sym, = symbols.get_symbol_by_name(name)
    section = elf.get_section(sym['st_shndx'])
    start = sym['st_value'] - section['sh_addr']
    size = sym['st_size']
    assert 0 <= start < start + size <= section['sh_size']
    return sym, section, section['sh_offset'] + start, section.data()[start:start + size]


def execute(address, code, finish, tag, argument, seed):
    machine = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    code_page = address & ~0xfff
    code_end = (address + len(code) + 0xfff) & ~0xfff
    machine.mem_map(code_page, code_end - code_page)
    machine.mem_write(address, code)
    for page in (0x10000000, 0x20000000):
        machine.mem_map(page, 0x1000)
    receiver = 0x10000080 + 32 * seed
    event = 0x10000300 + 32 * seed
    stack = 0x20000800
    sentinel = 0x30000000
    if not WHEEL:
        machine.mem_map(sentinel, 0x1000)
    original = bytes([0xA0 + seed]) * 64
    event_bytes = struct.pack('<II', argument & 0xffffffff, 0xC0120000 + seed)
    machine.mem_write(receiver, original)
    machine.mem_write(event, event_bytes)
    machine.reg_write(UC_ARM_REG_R0, receiver)
    machine.reg_write(UC_ARM_REG_R1, event if WHEEL else tag & 0xffffffff)
    machine.reg_write(UC_ARM_REG_R2, argument & 0xffffffff)
    machine.reg_write(UC_ARM_REG_LR, sentinel)
    machine.reg_write(UC_ARM_REG_SP, stack)
    writes = []

    def capture(_, __, addr, size, value, ___):
        assert receiver <= addr and addr + size <= receiver + 64 or stack - 16 <= addr < stack
        if receiver <= addr < receiver + 64:
            writes.append([addr - receiver, size, value & ((1 << (8 * size)) - 1)])

    machine.hook_add(UC_HOOK_MEM_WRITE, capture)
    machine.emu_start(address, finish if WHEEL else sentinel, count=32)
    assert machine.reg_read(UC_ARM_REG_PC) == (finish if WHEEL else sentinel)
    assert machine.reg_read(UC_ARM_REG_SP) == stack
    assert machine.reg_read(UC_ARM_REG_R0) == receiver
    after = bytes(machine.mem_read(receiver, 64))
    assert bytes(machine.mem_read(event, 8)) == event_bytes
    replay = bytearray(original)
    for offset, size, value in writes:
        replay[offset:offset + size] = value.to_bytes(size, 'little')
    assert after == replay
    if WHEEL:
        assert not writes and after == original
        delta, = struct.unpack('<i', struct.pack('<I', machine.reg_read(UC_ARM_REG_R1)))
        return dict(delta=delta, branch=finish, receiver=receiver, event=event,
                    event_preserved=True, writes=writes)
    tag_after, = struct.unpack_from('<i', after, 24)
    return dict(input_tag=tag, input_argument=argument, receiver=receiver,
                returned_receiver=True, tag=tag_after, words=list(struct.unpack('<8I', after[:32])),
                writes=writes)


def observe():
    packet = json.loads(PACKET.read_text())
    scopes = packet['task']['namespace'].split('::')
    prefix = 'N' + ''.join(f'{len(scope)}{scope}' for scope in scopes)
    reports = []
    for entry in packet['originals']:
        original = entry['original']
        binary = Path(original['elf_path'])
        if not binary.is_file():
            binary = PROJECT / binary
        image = binary.read_bytes()
        assert digest(image) == original['elf']
        elf = ELFFile(io.BytesIO(image))
        assert elf['e_machine'] == 'EM_ARM' and elf.little_endian
        symbols = elf.get_section_by_name('.symtab')
        sym, section, offset, code = extract(elf, symbols, original['mangled'])
        assert sym['st_info']['type'] == 'STT_FUNC'
        assert sym['st_value'] == original['address'] and sym['st_size'] == original['size']
        assert sym['st_shndx'] == original['section'] and section.name == original['section_name']
        assert offset == original['file_offset'] and image[offset:offset + len(code)] == code
        assert digest(code) == original['range_sha256'] and code.hex() == original['range_hex']
        if WHEEL:
            provider_name = '_Z' + prefix + '13addListOffsetEi'
            provider, _, _, _ = extract(elf, symbols, provider_name)
            branch = provider['st_value']
            cases = [execute(sym['st_value'], code, branch, 0, delta, index)
                     for index, delta in enumerate((5, -3, 0, 2**31 - 1, -2**31))]
            assert [case['delta'] for case in cases] == [5, -3, 0, 2**31 - 1, -2**31]
            reports.append(dict(original=original, provider_mangled=provider_name,
                                provider_address=branch, cases=cases))
            continue
        class_vtable, _, _, _ = extract(elf, symbols, '_ZTV' + prefix + 'E')
        control, _, control_offset, control_code = extract(
            elf, symbols, '_ZN8Presonus5Panel7ControlC2Ei')
        control_table, _, _, _ = extract(elf, symbols, '_ZTVN8Presonus5Panel7ControlE')
        peer_name = original['mangled'].replace('C1E', 'C2E') if 'C1E' in original['mangled'] else original['mangled'].replace('C2E', 'C1E')
        peer, _, peer_offset, peer_code = extract(elf, symbols, peer_name)
        assert peer['st_value'] != sym['st_value'] and peer_code == code
        cases = []
        for index, (tag, argument) in enumerate(
                ((0, 0), (-1, 1), (-2**31, 0xabcdef03), (2**31 - 1, 0xffffffff))):
            base = execute(control['st_value'], control_code, 0, tag, argument, index)
            case = execute(sym['st_value'], code, 0, tag, argument, index)
            assert base['words'][:7] == [control_table['st_value'] + 8, 0xffffffff,
                                        0, 0, 0, 0, tag & 0xffffffff]
            assert case['words'][:7] == [class_vtable['st_value'] + 8, *base['words'][1:7]]
            assert case['tag'] == base['tag'] == tag
            owned_width = 4 if LCD else 1
            owned_value = argument if LCD else 0
            assert [28, owned_width, owned_value] in case['writes']
            assert set((start, size) for start, size, _ in case['writes']) == {
                (start, 4) for start in range(0, 28, 4)} | {(28, owned_width)}
            cases.append(dict(**case, base_words=base['words'], base_writes=base['writes'],
                              owned_value=owned_value))
        reports.append(dict(original=original, class_vtable=class_vtable['st_value'],
                            control_range=dict(address=control['st_value'], file_offset=control_offset,
                                               size=len(control_code), sha256=digest(control_code)),
                            peer_range=dict(mangled=peer_name, address=peer['st_value'],
                                            file_offset=peer_offset, size=len(peer_code),
                                            sha256=digest(peer_code)), cases=cases))
    return reports


if __name__ == '__main__':
    json.dump(observe(), sys.stdout, indent=2)
    print()
