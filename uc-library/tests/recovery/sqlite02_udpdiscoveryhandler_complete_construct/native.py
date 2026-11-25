"""Exact original UDPDiscoveryHandler ARM lifetime targets."""
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
from struct import iter_unpack

from elftools.elf.elffile import ELFFile
from unicorn import UC_ARCH_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UC_MODE_ARM, Uc
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_SP

TASK = Path(__file__).parent.name
ROOT = Path('/home/rs/projects/opencs/ai-line-analysis')
PACKET = (ROOT / 'temp/recovery-work/rolling-c001-20261124/packeting'
          / 'sqlite-cycle02/discoveryshm02/packet/tasks' / TASK / 'CONTEXT.json')


def digest(data):
    return sha256(data).hexdigest()


def execute(body, entry, target, ctor, receiver, sentinel, allocated):
    stack, stop, backing, pointee = 0x4000800, 0x4001000, 0x5000000, 0x5001000
    cpu = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    for page in {receiver, backing, pointee, stack & ~0xfff, stop, entry & ~0xfff,
                 (entry + len(body) - 1) & ~0xfff, target & ~0xfff}:
        cpu.mem_map(page, 0x1000)
    cpu.mem_write(entry, body)
    cpu.mem_write(receiver, bytes([sentinel]) * 256)

    def store(address, value):
        cpu.mem_write(address, value.to_bytes(4, 'little'))

    def word(address):
        return int.from_bytes(cpu.mem_read(address, 4), 'little')

    if not ctor:
        for offset, value in ((0x14, backing if allocated else 0), (0x18, int(allocated)),
                              (0x1c, 5 if allocated else 0), (0x20, 5)):
            store(receiver + offset, value)
        store(backing, pointee)
        store(pointee, 280)
    cpu.reg_write(UC_ARM_REG_R0, receiver)
    cpu.reg_write(UC_ARM_REG_SP, stack)
    cpu.reg_write(UC_ARM_REG_LR, stop)
    calls, writes, pcs = [], [], []

    def on_code(u, address, width, _):
        if address != target:
            assert width == 4 and entry <= address < entry + len(body)
            pcs.append(address)
            return
        assert u.reg_read(UC_ARM_REG_R0) == receiver + 0x10
        if ctor:
            assert u.reg_read(UC_ARM_REG_R1) == 0
            assert [word(receiver + o) for o in (0x14, 0x18, 0x1c, 0x20)] == [0, 0, 0, 5]
            calls.append('resize 0')
        else:
            if allocated:
                assert word(receiver + 0x14) == backing and word(backing) == pointee
                cpu.mem_unmap(backing, 0x1000)
                calls.append('destroy release')
            else:
                assert word(receiver + 0x14) == 0
                calls.append('destroy')
        u.reg_write(UC_ARM_REG_PC, u.reg_read(UC_ARM_REG_LR))

    def on_write(_, __, address, width, value, ___):
        if receiver <= address < receiver + 256:
            writes.append([address - receiver, width, value])
        else:
            assert stack - 40 <= address < stack

    cpu.hook_add(UC_HOOK_CODE, on_code)
    cpu.hook_add(UC_HOOK_MEM_WRITE, on_write)
    cpu.emu_start(entry, stop, count=64)
    assert cpu.reg_read(UC_ARM_REG_PC) == stop and cpu.reg_read(UC_ARM_REG_SP) == stack
    assert cpu.reg_read(UC_ARM_REG_R0) == receiver
    assert word(receiver + 4) == word(receiver) + 0x34
    if ctor:
        assert sorted(w[:2] for w in writes) == [[i, 4] for i in
               (0, 4, 8, 12, 16, 20, 24, 28, 32, 40, 44)] + [[48, 1]]
        assert [word(receiver + o) for o in (8, 12, 20, 24, 28, 40, 44)] == [0] * 7
        assert bytes(cpu.mem_read(receiver + 48, 4)) == bytes((0, sentinel, sentinel, sentinel))
    else:
        assert [w[:2] for w in writes] == [[0, 4], [4, 4]]
        assert word(pointee) == 280
    mapped = any(start <= backing <= end for start, end, _ in cpu.mem_regions())
    assert mapped != allocated
    assert calls == ['resize 0' if ctor else 'destroy release' if allocated else 'destroy']
    return dict(receiver=receiver, sentinel=sentinel, writes=writes, calls=calls,
                instructions=pcs, guest_vector_allocation_released=allocated)

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
    ctor = row['mangled'][-4] == 'C'
    targets = []
    for i, (word,) in enumerate(iter_unpack('<I', body)):
        if word >> 24 == 0xeb:
            disp = (word & 0xffffff) - (0x1000000 if word & 0x800000 else 0)
            targets.append(entry + 4 * i + 8 + 4 * disp)
    target, = targets
    name = '_ZN4Core6VectorIPN8Presonus2UC17UDPDiscoveryEntryEE' + (
        '6resizeEi' if ctor else 'D1Ev')
    assert any(s['st_value'] == target for s in symbol_table.get_symbol_by_name(name))
    cases = [execute(body, entry, target, ctor, receiver, sentinel, i == 1 and not ctor)
             for i, (receiver, sentinel) in enumerate(((0x3000000, 0xa5), (0x3001000, 0x5a)))]
    return dict(original=row, vector_target=dict(entry=target, name=name), cases=cases)


def run():
    packet = json.loads(PACKET.read_text())
    return [observe(item['original']) for item in packet['originals']]


if __name__ == '__main__':
    print(json.dumps(run(), indent=2))
