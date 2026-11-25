"""Trace the exact original VU draw wrapper around its verified base entry."""
import hashlib
import io
import json
from pathlib import Path

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import (
    UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_SP,
)

TASK = Path(__file__).resolve().parent.name
PACKET = Path('temp/recovery-work/sqlite-issued/packet') / TASK / 'CONTEXT.json'
PROJECT = Path('/home/rs/projects/opencs/ai-line-analysis')
BASE = '_ZN8Presonus10PotControl4drawERKN4Core8Portable9DrawEventE'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def extract(elf, symbols, name):
    sym, = symbols.get_symbol_by_name(name)
    assert sym['st_info']['type'] == 'STT_FUNC'
    section = elf.get_section(sym['st_shndx'])
    start = sym['st_value'] - section['sh_addr']
    size = sym['st_size']
    assert 0 <= start < start + size <= section['sh_size']
    data = section.data()[start:start + size]
    return dict(mangled=name, address=sym['st_value'], size=size,
                section=sym['st_shndx'], section_name=section.name,
                file_offset=section['sh_offset'] + start, range_sha256=digest(data),
                range_hex=data.hex())


def execute(original, base, seed, dirty):
    address, callee = original['address'], base['address']
    receiver, event = 0x10000100 + 0x100 * seed, 0x20000080 + 0x40 * seed
    stack, finish = 0x30000800, 0x40000000
    dirty_address = receiver + 0x84
    machine = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    for page in {address & ~0xfff, callee & ~0xfff, receiver & ~0xfff,
                 event & ~0xfff, stack & ~0xfff, finish}:
        machine.mem_map(page, 0x1000)
    machine.mem_write(address, bytes.fromhex(original['range_hex']))
    # Trace the native wrapper at the verified callee address. This boundary
    # immediately returns without executing the native base rendering body.
    machine.mem_write(callee, bytes.fromhex('1eff2fe1'))  # bx lr
    before = bytearray([0xCA + seed] * 0x90)
    before[0x84] = dirty
    machine.mem_write(receiver, bytes(before))
    event_bytes = bytes([0x3B + seed] * 16)
    machine.mem_write(event, event_bytes)
    machine.reg_write(UC_ARM_REG_R0, receiver)
    machine.reg_write(UC_ARM_REG_R1, event)
    machine.reg_write(UC_ARM_REG_LR, finish)
    machine.reg_write(UC_ARM_REG_SP, stack)
    trace = []
    resume = None

    def instruction(_, pc, size, __):
        nonlocal resume
        assert size == 4
        if pc == callee:
            assert machine.reg_read(UC_ARM_REG_R0) == receiver
            assert machine.reg_read(UC_ARM_REG_R1) == event
            resume = machine.reg_read(UC_ARM_REG_LR)
            trace.append(['base_entry', pc, receiver, event,
                          machine.mem_read(dirty_address, 1)[0]])
        elif pc == resume:
            trace.append(['base_return', pc, machine.mem_read(dirty_address, 1)[0]])

    def write(_, __, location, size, value, ___):
        if stack - 24 <= location and location + size <= stack:
            return
        assert location == dirty_address and size == 1
        trace.append(['dirty_write', location - receiver, size, value])

    machine.hook_add(UC_HOOK_CODE, instruction)
    machine.hook_add(UC_HOOK_MEM_WRITE, write)
    machine.emu_start(address, finish, count=32)
    assert machine.reg_read(UC_ARM_REG_PC) == finish
    assert machine.reg_read(UC_ARM_REG_SP) == stack
    assert trace == [['base_entry', callee, receiver, event, dirty],
                     ['base_return', address + 24, dirty],
                     ['dirty_write', 0x84, 1, 0]]
    expected = bytearray(before)
    expected[0x84] = 0
    assert machine.mem_read(receiver, len(expected)) == expected
    assert machine.mem_read(event, len(event_bytes)) == event_bytes
    return dict(dirty=dirty, receiver=receiver, event=event, trace=trace,
                final_dirty=machine.mem_read(dirty_address, 1)[0])


def observe():
    packet = json.loads(PACKET.read_text())
    target = packet['originals'][0]['original']
    binary = Path(target['elf_path'])
    if not binary.is_file():
        binary = PROJECT / binary
    image = binary.read_bytes()
    assert digest(image) == target['elf']
    elf = ELFFile(io.BytesIO(image))
    assert elf['e_machine'] == 'EM_ARM' and elf.little_endian
    symbols = elf.get_section_by_name('.symtab')
    native = extract(elf, symbols, target['mangled'])
    base = extract(elf, symbols, BASE)
    for found in (native, base):
        offset, size = found['file_offset'], found['size']
        assert image[offset:offset + size].hex() == found['range_hex']
    assert all(target[key] == value for key, value in native.items())
    cases = [execute(native, base, seed, dirty)
             for seed, dirty in enumerate((0, 1, 0xA5))]
    return dict(original=target, provider=base, cases=cases)


if __name__ == '__main__':
    print(json.dumps(observe(), indent=2))
