"""Replay an exact native constructor and trace its provider calls."""
import hashlib
import io
import json
from pathlib import Path
import struct

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import (
    UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_SP,
)

TASK = Path(__file__).resolve().parent.name
PACKET = Path('temp/recovery-work/sqlite-issued/packet') / TASK / 'CONTEXT.json'
PROJECT = Path('/home/rs/projects/opencs/ai-line-analysis')
TARGETED = '_targeted_' in TASK
SERVER = '_ZN8Presonus2UC15ServerComponentC2EPKc'
COMPONENT = '_ZN4Core8Portable9ComponentC2EPKc'
VECTOR = '_ZN4Core6VectorIPNS_8Portable9ComponentEE6resizeEi'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def extract(elf, image, name, kind='STT_FUNC'):
    sym, = elf.get_section_by_name('.symtab').get_symbol_by_name(name)
    assert sym['st_info']['type'] == kind
    section = elf.get_section(sym['st_shndx'])
    start = sym['st_value'] - section['sh_addr']
    size = sym['st_size']
    assert 0 <= start < start + size <= section['sh_size']
    data = section.data()[start:start + size]
    offset = section['sh_offset'] + start
    assert image[offset:offset + size] == data
    return dict(mangled=name, address=sym['st_value'], size=size,
                section=sym['st_shndx'], section_name=section.name,
                file_offset=offset, range_sha256=digest(data), range_hex=data.hex())


def execute(original, provider, core, tables, name, seed):
    machine = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    receiver, name_address = 0x10000100 + 0x100 * seed, 0x20000100 + 0x40 * seed
    stack, finish = 0x30000800, 0x40000000
    ranges = [original, provider] + ([core] if core else [])
    code_pages = {address & ~0xfff for entry in ranges
                  for address in (entry['address'], entry['address'] + entry['size'] - 1)}
    for page in code_pages | {receiver & ~0xfff, name_address & ~0xfff,
                              stack & ~0xfff, finish}:
        machine.mem_map(page, 0x1000)
    for entry in (original, provider):
        machine.mem_write(entry['address'], bytes.fromhex(entry['range_hex']))
    if core:
        # Stop at the verified CCL constructor entry; no Core body is recovered
        # or executed in the TargetedComponent native replay.
        machine.mem_write(core['address'], bytes.fromhex('1eff2fe1'))
    before = bytes([0xCA + seed]) * 0x98
    c_string = name.encode('ascii') + b'\0'
    machine.mem_write(receiver, before)
    machine.mem_write(name_address, c_string)
    machine.reg_write(UC_ARM_REG_R0, receiver)
    machine.reg_write(UC_ARM_REG_R1, name_address if TARGETED else -1 & 0xffffffff)
    machine.reg_write(UC_ARM_REG_LR, finish)
    machine.reg_write(UC_ARM_REG_SP, stack)
    trace, writes = [], []
    provider_return = None

    def words():
        return list(struct.unpack('<7I', machine.mem_read(receiver, 28)))

    def instruction(_, pc, size, __):
        nonlocal provider_return
        if pc == provider['address']:
            r0 = receiver if TARGETED else receiver + 8
            r1 = name_address if TARGETED else 0
            assert machine.reg_read(UC_ARM_REG_R0) == r0
            assert machine.reg_read(UC_ARM_REG_R1) == r1
            provider_return = machine.reg_read(UC_ARM_REG_LR)
            trace.append(['provider_entry', pc, r0, r1, words()])
        elif core and pc == core['address']:
            assert machine.reg_read(UC_ARM_REG_R0) == receiver
            assert machine.reg_read(UC_ARM_REG_R1) == name_address
            assert machine.mem_read(name_address, len(c_string)) == c_string
            trace.append(['core_boundary', pc, receiver, name_address])
        elif pc == provider_return:
            trace.append(['provider_return', pc, words()])

    def write(_, __, addr, size, value, ___):
        if receiver <= addr and addr + size <= receiver + len(before):
            writes.append([addr - receiver, size, value & ((1 << (8 * size)) - 1)])
        else:
            assert stack - 128 <= addr and addr + size <= stack

    machine.hook_add(UC_HOOK_CODE, instruction)
    machine.hook_add(UC_HOOK_MEM_WRITE, write)
    machine.emu_start(original['address'], finish, count=140)
    assert machine.reg_read(UC_ARM_REG_PC) == finish
    assert machine.reg_read(UC_ARM_REG_SP) == stack
    assert machine.reg_read(UC_ARM_REG_R0) == receiver
    assert machine.mem_read(name_address, len(c_string)) == c_string
    replay = bytearray(before)
    for offset, size, value in writes:
        replay[offset:offset + size] = value.to_bytes(size, 'little')
    assert machine.mem_read(receiver, len(before)) == replay
    if TARGETED:
        assert [call[0] for call in trace] == [
            'provider_entry', 'core_boundary', 'provider_return']
        server_vptr = tables['server']['address'] + 8
        own_vptr = tables['targeted']['address'] + 8
        assert trace[-1][2][:2] == [server_vptr, server_vptr + 0x3c]
        assert words()[:2] == [own_vptr, own_vptr + 0x44]
        assert writes == [[4, 4, server_vptr + 0x3c], [0x84, 1, 0],
                          [0x28, 1, 1], [0, 4, server_vptr],
                          [4, 4, own_vptr + 0x44], [0x85, 1, 0], [0, 4, own_vptr]]
        result = dict(name=name, name_address=name_address, pending=replay[0x85])
    else:
        assert [call[0] for call in trace] == ['provider_entry', 'provider_return']
        vptr = tables['vector']['address'] + 8
        assert words() == [0, 0, vptr, 0, 0, 0, 5]
        assert trace[0][4] == words() == trace[-1][2]
        assert writes == [[8, 4, vptr], [24, 4, 5], [0, 4, 0], [4, 4, 0],
                          [12, 4, 0], [16, 4, 0], [20, 4, 0]]
        result = dict(owner=words()[0], source=words()[1], items=words()[3],
                      count=words()[4], capacity=words()[5], delta=words()[6])
    return dict(receiver=receiver, trace=trace, writes=writes, result=result)


def observe():
    packet = json.loads(PACKET.read_text())
    original = packet['originals'][0]['original']
    binary = Path(original['elf_path'])
    if not binary.is_file():
        binary = PROJECT / binary
    image = binary.read_bytes()
    assert digest(image) == original['elf']
    elf = ELFFile(io.BytesIO(image))
    assert elf['e_machine'] == 'EM_ARM' and elf.little_endian

    def read(name, kind='STT_FUNC'):
        return extract(elf, image, name, kind)

    verified = read(original['mangled'])
    assert all(original[key] == value for key, value in verified.items())
    variant, other = ('C1E', 'C2E') if TASK.endswith('_c1') else ('C2E', 'C1E')
    peer = read(original['mangled'].replace(variant, other))
    assert verified['address'] != peer['address']
    core = read(COMPONENT) if TARGETED else None
    provider = read(SERVER if TARGETED else VECTOR)
    if TARGETED:
        table_symbols = dict(server='_ZTVN8Presonus2UC15ServerComponentE',
                             targeted='_ZTVN8Presonus17TargetedComponentE')
        sibling_methods = {}
    else:
        table_symbols = dict(vector='_ZTVN4Core6VectorIPNS_8Portable9ComponentEEE')
        prefix = '_ZN8Presonus7Surface19FatChannelClipboard'
        sibling_methods = {label: read(prefix + symbol) for label, symbol in [
            ('clipboard_owner', '4initEPN4Core8Portable9ComponentE'),
            ('clipboard_source', '4copyEPN4Core8Portable9ComponentE'),
            ('stack_vector', '5pasteEv')]}
    tables = {label: read(symbol, 'STT_OBJECT') for label, symbol in table_symbols.items()}
    inputs = ('', 'main', 'Monitor A') if TARGETED else ('', '', '')
    cases = [execute(original, provider, core, tables, name, index)
             for index, name in enumerate(inputs)]
    return dict(original=original, peer=peer, provider=provider, core_boundary=core,
                tables=tables, sibling_methods=sibling_methods, cases=cases)


if __name__ == '__main__':
    print(json.dumps(observe(), indent=2))
