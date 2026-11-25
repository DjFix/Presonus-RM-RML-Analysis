"""Exact original SharedMemoryComm ARM lifetime targets."""
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
from struct import iter_unpack

from elftools.elf.elffile import ELFFile
from unicorn import UC_ARCH_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UC_MODE_ARM, Uc
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_SP

TASK = Path(__file__).parent.name
ROOT = Path('/home/rs/projects/opencs/ai-line-analysis')
PACKET = (ROOT / 'temp/recovery-work/rolling-c001-20261124/packeting'
          / 'sqlite-cycle02/discoveryshm02/packet/tasks' / TASK / 'CONTEXT.json')


def digest(data):
    return sha256(data).hexdigest()


def execute(body, entry, targets, ctor, d0, receiver, sentinel):
    stack, stop = 0x4000800, 0x4001000
    cpu = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    for page in {receiver, stack & ~0xfff, stop, entry & ~0xfff,
                 (entry + len(body) - 1) & ~0xfff, *(target & ~0xfff for target in targets)}:
        cpu.mem_map(page, 0x1000)
    cpu.mem_write(entry, body)
    cpu.mem_write(receiver, bytes([sentinel]) * 256)
    cpu.reg_write(UC_ARM_REG_R0, receiver)
    cpu.reg_write(UC_ARM_REG_SP, stack)
    cpu.reg_write(UC_ARM_REG_LR, stop)
    calls, writes, pcs = [], [], []

    def on_code(u, address, width, _):
        if address == targets[0]:
            assert u.reg_read(UC_ARM_REG_R0) == receiver + 0x24
            calls.append(['lock_construct' if ctor else 'lock_destroy', 0x24])
        elif d0 and address == targets[1]:
            assert u.reg_read(UC_ARM_REG_R0) == receiver and calls == [['lock_destroy', 0x24]]
            u.mem_unmap(receiver, 0x1000)
            calls.append(['delete', 0])
        else:
            assert width == 4 and entry <= address < entry + len(body)
            pcs.append(address)
            return
        u.reg_write(UC_ARM_REG_PC, u.reg_read(UC_ARM_REG_LR))

    def on_write(_, __, address, width, value, ___):
        if receiver <= address < receiver + 256:
            writes.append([address - receiver, width, value])
        else:
            assert stack - 32 <= address < stack

    cpu.hook_add(UC_HOOK_CODE, on_code)
    cpu.hook_add(UC_HOOK_MEM_WRITE, on_write)
    cpu.emu_start(entry, stop, count=40)
    assert cpu.reg_read(UC_ARM_REG_PC) == stop and cpu.reg_read(UC_ARM_REG_SP) == stack
    assert cpu.reg_read(UC_ARM_REG_R0) == receiver
    fields = [[0, 4], [4, 1], [0, 4]] if ctor else [[0, 4]]
    assert [w[:2] for w in writes] == fields
    if ctor:
        assert writes[1][2] == 0 and writes[0][2] != writes[2][2]
        assert bytes(cpu.mem_read(receiver + 4, 4)) == bytes((0, sentinel, sentinel, sentinel))
    mapped = any(start <= receiver <= stop for start, stop, _ in cpu.mem_regions())
    assert mapped != d0
    expected = [['lock_construct' if ctor else 'lock_destroy', 0x24]]
    assert calls == expected + ([['delete', 0]] if d0 else [])
    return dict(receiver=receiver, sentinel=sentinel, writes=writes, calls=calls,
                pcs=pcs, deallocated=not mapped)


def observe(row):
    blob = (ROOT / row['elf_path']).read_bytes()
    assert digest(blob) == row['elf']
    elf = ELFFile(BytesIO(blob))
    symbol_table = elf.get_section_by_name('.symtab')
    symbol, = symbol_table.get_symbol_by_name(row['mangled'])
    entry, size, index = row['address'], row['size'], row['section']
    assert (symbol['st_value'], symbol['st_size'], symbol['st_shndx']) == (entry, size, index)
    section = elf.get_section(index)
    delta = entry - section['sh_addr']
    offset = section['sh_offset'] + delta
    assert section.name == '.text' and 0 <= delta <= section['sh_size'] - size
    body = blob[offset:offset + size]
    assert offset == row['file_offset'] and digest(body) == row['range_sha256']
    variant = row['mangled'][-4:-2]
    ctor, d0 = variant.startswith('C'), variant == 'D0'
    targets = []
    for i, (word,) in enumerate(iter_unpack('<I', body)):
        if word >> 24 == 0xeb:
            disp = (word & 0xffffff) - (0x1000000 if word & 0x800000 else 0)
            targets.append(entry + 4 * i + 8 + 4 * disp)
    assert len(targets) == (2 if d0 else 1)
    lock = '_ZN4Core7Threads8CoreLock' + ('C1' if ctor else 'D1') + 'Ev'
    assert any(s['st_value'] == targets[0] for s in symbol_table.get_symbol_by_name(lock))
    relocation = None
    if d0:
        plt = elf.get_section_by_name('.plt')
        relocs = elf.get_section_by_name('.rel.plt')
        symbols = elf.get_section(relocs['sh_link'])
        slot, alignment = divmod(targets[1] - plt['sh_addr'] - 20, 12)
        assert alignment == 0 and slot >= 0
        rel = relocs.get_relocation(slot)
        assert symbols.get_symbol(rel['r_info_sym']).name == '_ZdlPv'
        relocation = dict(entry=targets[1], slot=slot, got=rel['r_offset'], name='_ZdlPv')
    cases = [execute(body, entry, targets, ctor, d0, receiver, sentinel)
             for receiver, sentinel in ((0x3000000, 0xa5), (0x3001000, 0x5a))]
    return dict(original=row, lock_target=dict(entry=targets[0], name=lock),
                delete_relocation=relocation, cases=cases)


def run():
    packet = json.loads(PACKET.read_text())
    return [observe(item['original']) for item in packet['originals']]


if __name__ == '__main__':
    print(json.dumps(run(), indent=2))
