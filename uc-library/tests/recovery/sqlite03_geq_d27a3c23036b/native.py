"""Verify and execute the exact GEQLinkHandler ARM constructor or callback."""
from hashlib import sha256
from io import BytesIO
from itertools import product
import json
from pathlib import Path

from elftools.elf.elffile import ELFFile
from unicorn import UC_ARCH_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UC_MODE_ARM, Uc
from unicorn.arm_const import (UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0,
                               UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_SP)

TASK = Path(__file__).parent.name
ROOT = Path('/home/rs/projects/opencs/ai-line-analysis')
PACKET = (ROOT / 'temp/recovery-work/rolling-c001-20261124/packeting'
          / 'sqlite-cycle02/geqlink_worker06/packet/tasks' / TASK / 'CONTEXT.json')
STACK, STOP = 0x4000800, 0x4001000
VTABLE, GET, SET = 0x5000000, 0x5001000, 0x5002000
DEST, SOURCE, PASSED = 0x5003000, 0x5004000, 0x5005000
PORTS = {'destination': DEST, 'source': SOURCE, 'distinct': PASSED, 'null': 0}
COMPONENT = '_ZN4Core8Portable9ComponentC2EPKc'
ADD = '_ZN4Core8Portable9Parameter11addObserverEPNS0_14IParamObserverE'
REMOVE = '_ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE'
BITS = (0, 0x80000000, 0x3f000000, 0x3f800000, 0x7f7fffff, 0xff7fffff,
        0x7fc00011, 0x7f800000, 0xff800000)


def digest(data):
    return sha256(data).hexdigest()


def cases(ctor):
    if ctor:
        for receiver, dest, source in product(('first', 'second'),
                ('destination', 'null'), ('source', 'string', 'null', 'destination')):
            if dest == 'null' and source == 'destination':
                continue
            yield dict(receiver=receiver, destination=dest, source=source)
        return
    for message, dest in product((-2147483648, -1, 0, 2, 3, 4, 5, 2147483647),
                                 ('destination', 'null')):
        passed = 'distinct' if message == 5 or (message == 3 and dest != 'null') else 'null'
        yield dict(receiver='first', destination=dest, passed=passed, msg=message, bits=0)
    for bits, passed in product(BITS, ('distinct', 'source', 'destination')):
        if passed == 'destination' and (bits not in (0x3f000000, 0x3f800000)):
            continue
        yield dict(receiver='second', destination='destination', passed=passed, msg=3, bits=bits)


def run():
    row = json.loads(PACKET.read_text())['originals'][0]['original']
    blob = (ROOT / row['elf_path']).read_bytes()
    assert digest(blob) == row['elf']
    elffile = ELFFile(BytesIO(blob))
    symbols = elffile.get_section_by_name('.symtab')
    sym, = symbols.get_symbol_by_name(row['mangled'])
    entry, size, index = row['address'], row['size'], row['section']
    assert (sym['st_value'], sym['st_size'], sym['st_shndx']) == (entry, size, index)
    section = elffile.get_section(index)
    delta = entry - section['sh_addr']
    offset = section['sh_offset'] + delta
    assert section.name == '.text' and 0 <= delta <= section['sh_size'] - size
    body = blob[offset:offset + size]
    assert offset == row['file_offset'] and digest(body) == row['range_sha256']
    ctor = row['mangled'].endswith('ES5_')
    bindings = {name: symbols.get_symbol_by_name(name)[0]['st_value']
                for name in ((COMPONENT, ADD) if ctor else (REMOVE,))}
    string_addr = int.from_bytes(body[-8:-4], 'little') if ctor else 0
    if ctor:
        offset, = elffile.address_offsets(string_addr)
        assert blob[offset:offset + 1] == b'\0'
    return dict(original=row, bindings=bindings, string_address=string_addr,
                cases=[execute(body, entry, bindings, string_addr, ctor, case)
                       for case in cases(ctor)])


def execute(body, entry, bindings, string_addr, ctor, case):
    u = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    receiver = 0x3000000 if case['receiver'] == 'first' else 0x3001000
    sentinel = 0xa5 if case['receiver'] == 'first' else 0x5a
    for page in {entry & ~0xfff, (entry + len(body) - 1) & ~0xfff, receiver,
                 STACK & ~0xfff, STOP, VTABLE, GET, SET, DEST, SOURCE, PASSED,
                 *(target & ~0xfff for target in bindings.values())}:
        u.mem_map(page, 0x1000)
    u.mem_write(entry, body)
    u.mem_write(receiver, bytes([sentinel]) * 256)

    def store(address, value):
        u.mem_write(address, value.to_bytes(4, 'little'))

    def read(address):
        return int.from_bytes(u.mem_read(address, 4), 'little')

    dest = PORTS[case['destination']]
    u.reg_write(UC_ARM_REG_R0, receiver)
    u.reg_write(UC_ARM_REG_SP, STACK)
    u.reg_write(UC_ARM_REG_LR, STOP)
    if ctor:
        source = PORTS.get(case['source'], SOURCE)
        u.reg_write(UC_ARM_REG_R1, dest)
        u.reg_write(UC_ARM_REG_R2, source)
    else:
        store(receiver + 0x84, SOURCE)
        store(receiver + 0x88, dest)
        for p in (DEST, SOURCE, PASSED):
            store(p, VTABLE)
        store(VTABLE + 0x44, GET)
        store(VTABLE + 0x58, SET)
        passed = PORTS[case['passed']]
        u.reg_write(UC_ARM_REG_R1, passed)
        u.reg_write(UC_ARM_REG_R2, case['msg'] & 0xffffffff)
    calls, writes, pcs = [], [], []

    def on_code(cpu, address, width, _):
        r0, r1, r2 = (cpu.reg_read(reg) for reg in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2))
        if ctor and address == bindings[COMPONENT]:
            assert r0 == receiver and r1 == string_addr
            calls.append(['component', ''])
        elif ctor and address == bindings[ADD]:
            assert r0 == source and r1 == receiver + 4 and source
            assert read(receiver + 0x84) == source and read(receiver + 0x88) == dest
            calls.append(['add', case['source']])
        elif not ctor and address == bindings[REMOVE]:
            assert r0 == passed and r1 == receiver + 4 and passed
            calls.append(['remove', case['passed']])
        elif not ctor and address == GET:
            assert r0 == passed and passed
            cpu.reg_write(UC_ARM_REG_R0, case['bits'])
            calls.append(['get', case['passed'], case['bits']])
        elif not ctor and address == SET:
            assert r0 == dest and r1 == case['bits'] and r2 == 1 and dest
            calls.append(['set', case['destination'], r1, r2])
        else:
            assert width == 4 and entry <= address < entry + len(body)
            pcs.append(address)
            return
        cpu.reg_write(UC_ARM_REG_PC, cpu.reg_read(UC_ARM_REG_LR))

    def on_write(_, __, address, width, value, ___):
        if receiver <= address < receiver + 256:
            writes.append([address - receiver, width, value])
        else:
            assert STACK - 40 <= address < STACK

    u.hook_add(UC_HOOK_CODE, on_code)
    u.hook_add(UC_HOOK_MEM_WRITE, on_write)
    u.emu_start(entry, STOP, count=80)
    assert u.reg_read(UC_ARM_REG_SP) == STACK and u.reg_read(UC_ARM_REG_PC) == STOP
    if ctor:
        assert u.reg_read(UC_ARM_REG_R0) == receiver
        assert sorted(w[0] for w in writes) == [0, 4, 0x84, 0x88]
        assert read(receiver + 4) == read(receiver) + 0x34
        assert read(receiver + 0x84) == source and read(receiver + 0x88) == dest
    else:
        assert not writes and read(receiver + 0x84) == SOURCE and read(receiver + 0x88) == dest
    return dict(input=case, calls=calls, writes=writes, instructions=pcs)


if __name__ == '__main__':
    print(json.dumps(run(), indent=2))
