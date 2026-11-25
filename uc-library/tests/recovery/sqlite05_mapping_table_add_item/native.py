"""Run original addItem, Item C1 and both teardown bodies with explicit provider hooks."""
import argparse
import hashlib
import json
import struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import (UC_ARM_REG_PC, UC_ARM_REG_LR, UC_ARM_REG_R0,
                              UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_SP)

PACKET = Path('temp/recovery-work/sqlite-issued/packet/sqlite05_mapping_table_add_item/CONTEXT.json')
ELF = Path('rootfs/CS18_v13840/home/root/surface')
DIGEST = '304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
assert hashlib.sha256(ELF.read_bytes()).hexdigest() == DIGEST
ADD, ITEM, D1, D2 = (0x76564, 0x76148, 0x75a10, 0x759a8)
# D1/D2 assignment is verified by the symbol table below.
CSTRING, NEW, ALIAS_CTOR, CMP, COPY, ALIAS_D0 = (0x24268, 0xa90c, 0x1205ac, 0xb0f8, 0xaffc, 0x400000)
TABLE, ITEMS, ALIASES, VTABLE, INPUT, STACK, STOP = (0x500000, 0x510000, 0x540000, 0x560000, 0x561000, 0x562000, 0x563000)
STRIDE, CAPACITY = 72, 1024

with ELF.open('rb') as stream:
    ef = ELFFile(stream)
    sections = list(ef.iter_sections())
    all_symbols = list(ef.get_section_by_name('.symtab').iter_symbols())
    def source(address, length):
        section = next(s for s in sections if s['sh_addr'] <= address
                       and address+length <= s['sh_addr']+s['sh_size']
                       and s['sh_type'] != 'SHT_NOBITS')
        offset = address-section['sh_addr']
        return section.data()[offset:offset+length]
    targets = {}
    ranges = {}
    assert ef['e_machine'] == 'EM_ARM' and ef.little_endian
    for address in (ADD, ITEM, D1, D2):
        syms = [s for s in all_symbols if s['st_value'] == address and s.name.startswith('_ZN8Presonus12MappingTable')]
        sizes = {s['st_size'] for s in syms}
        assert len(sizes) == 1 and syms
        length, = sizes
        if address in (D1, D2):
            assert syms[0].name.endswith("D1Ev" if address == D1 else "D2Ev")
        body = source(address, length)
        targets[address] = (body, [s.name for s in syms])
        for sym in syms:
            index = sym['st_shndx']
            section = ef.get_section(index)
            ranges[sym.name] = dict(address=address, size=length, section=index,
                section_name=section.name, file_offset=section['sh_offset'] + address - section['sh_addr'],
                range_sha256=hashlib.sha256(body).hexdigest())
    assert source(0x19cb84, 11) == b'sel_ch_48V\0'
    info = source(0x19ccc0, 84)
    assert info == b'\x05' + b'\0'*7 + b'hwparam' + b'\0'*69

def fixture(labels, input_name, *, failed=False, dtor=None):
    uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    hooks = {CSTRING, NEW, ALIAS_CTOR, CMP, COPY, ALIAS_D0}
    for page in {site & ~4095 for site in hooks | targets.keys()} | {TABLE, VTABLE, INPUT, STACK, STOP, 0x19c000}:
        uc.mem_map(page, 4096)
    uc.mem_map(ITEMS, 0x13000)
    uc.mem_map(ALIASES, 0x12000)
    def wr(addr, value):
        uc.mem_write(addr, struct.pack('<I', value))
    def rd(addr):
        return struct.unpack('<I', uc.mem_read(addr, 4))[0]
    def str_at(address):
        if not address:
            return b''
        buf = bytearray()
        while (val := uc.mem_read(address+len(buf), 1)) != b'\0':
            buf.extend(val)
            assert len(buf) < 128
        return bytes(buf)
    for address, (body, _) in targets.items():
        uc.mem_write(address, body)
    uc.mem_write(0x19ccc0, info)
    uc.mem_write(0x19cb84, b'sel_ch_48V\0')
    wr(TABLE+4, ITEMS)
    wr(TABLE+8, len(labels))
    wr(VTABLE+8, ALIAS_D0)
    allocations = []
    events = []
    for index, label in enumerate(labels):
        record = ITEMS + index*STRIDE
        alias = ALIASES + index*64
        uc.mem_write(record+4, label.encode()+b'\0')
        wr(record+36, alias)
        wr(alias, VTABLE)
    if input_name is not None:
        uc.mem_write(INPUT, input_name.encode()+b'\0')

    def trace(engine, address, size, user):
        a, b, c = [engine.reg_read(reg) for reg in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2)]
        result = a
        if address == CSTRING:
            text = str_at(b)
            events.append(['cstring', text.decode()])
            engine.mem_write(a, text[:31].ljust(32, b'\0'))
        elif address == NEW:
            events.append(['new', a])
            if failed:
                engine.emu_stop()
                return
            result = ALIASES + CAPACITY*64
            allocations.append(result)
        elif address == ALIAS_CTOR:
            assert b == 0x19ccc0 and c == 0
            assert bytes(engine.mem_read(b, 84)) == info
            events.append(['alias_ctor', a, b, c])
            wr(a, VTABLE)
        elif address == CMP:
            lhs, rhs = str_at(a), str_at(b)
            events.append(['strcmp', lhs.decode(), rhs.decode()])
            result = (lhs > rhs) - (lhs < rhs)
        elif address == COPY:
            assert c == STRIDE
            events.append(['memcpy_record', (a-ITEMS)//STRIDE, b >= ITEMS and b < ITEMS+0x13000])
            engine.mem_write(a, bytes(engine.mem_read(b, c)))
        elif address == ALIAS_D0:
            events.append(['alias_D0_dispatch', a])
        elif address == ITEM:
            events.append(['item_ctor', str_at(b).decode(), c])
            return
        elif any(start <= address < start+len(body) for start,(body,_) in targets.items()):
            return
        else:
            raise AssertionError(hex(address))
        engine.reg_write(UC_ARM_REG_R0, result & 0xffffffff)
        engine.reg_write(UC_ARM_REG_PC, engine.reg_read(UC_ARM_REG_LR))

    def run(entry):
        for reg, value in ((UC_ARM_REG_R0, TABLE), (UC_ARM_REG_R1, INPUT if input_name is not None else 0),
                           (UC_ARM_REG_SP, STACK+0x800), (UC_ARM_REG_LR, STOP)):
            uc.reg_write(reg, value)
        uc.emu_start(entry, STOP, count=40000)
    uc.hook_add(UC_HOOK_CODE, trace)
    run(ADD)
    assert uc.reg_read(UC_ARM_REG_PC) == (NEW if failed else STOP)
    count = rd(TABLE+8)
    post = [(str_at(ITEMS+i*STRIDE+4).decode(), rd(ITEMS+i*STRIDE+36)) for i in range(count)]
    if dtor:
        run(dtor)
        assert uc.reg_read(UC_ARM_REG_PC) == STOP
    assert [label for label,_ in post] == (labels if failed or len(labels)==CAPACITY
        else sorted(labels + [(input_name or '')[:31]]))
    new_position = next((i for i,(_, alias) in enumerate(post) if alias in allocations), None)
    assert (new_position is None) == (failed or len(labels)==CAPACITY)
    if new_position is not None and input_name is not None:
        assert new_position == sum(label <= input_name[:31] for label in labels)
    if not failed:
        assert [x[0] for x in events[:3]] == ['cstring', 'new', 'alias_ctor']
    if dtor:
        assert [x[1] for x in events if x[0]=='alias_D0_dispatch'] == [x[1] for x in post]
    if len(labels) == CAPACITY:
        assert not any(x[0]=='memcpy_record' for x in events)
    if failed:
        assert [x[0] for x in events] == ['cstring', 'new']
    assert all(str_at(ITEMS + i * STRIDE + 40) == b'' for i in range(count))
    return dict(initial=labels, count_before=len(labels), count_after=count, input=input_name,
                new_position=new_position, labels_after=[label for label,_ in post] if count<20 else None,
                failure_boundary_only=failed, destructor=hex(dtor) if dtor else None, events=events)

def observe(packet=PACKET):
    original = json.loads(packet.read_text())['originals'][0]['original']
    assert original['elf'] == DIGEST and original['elf_path'] == str(ELF)
    assert original['range_hex'] == targets[ADD][0].hex()
    assert all(original[key] == value for key, value in ranges[original['mangled']].items())
    cases = [
        fixture([], 'first', dtor=D1),
        fixture(['alpha', 'gamma'], 'beta', dtor=D2),
        fixture(['alpha', 'beta', 'beta', 'omega'], 'beta'),
        fixture(['zulu'], ''),
        fixture([], None),
        fixture([], 'x' * 40),
        fixture(['x' * 31, 'x' * 31, 'z'], 'x' * 31 + 'suffix'),
        fixture([f'm{i:04d}' for i in range(CAPACITY)], 'a', dtor=D1),
        fixture([f'm{i:04d}' for i in range(CAPACITY)], 'z', dtor=D2),
        fixture(['alpha'], 'beta', failed=True),
    ]
    return dict(
        original=original, descriptor_address=hex(0x19ccc0), descriptor_hex=info.hex(),
        ranges=ranges, cases=cases,
        scope='ARM addItem and Item C1 run against modeled fixed-string, allocator, Core alias constructor and libc boundaries. '
              'ARM D1/D2 run to record actual virtual alias D0 dispatch. Native alias cleanup/free and forced-failure unwinding remain unexecuted.',
    )


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('fixture', type=Path)
    parser.add_argument('--write', action='store_true')
    parser.add_argument('--packet', type=Path, default=PACKET)
    args = parser.parse_args()
    result = observe(args.packet)
    if args.write:
        args.fixture.write_text(json.dumps(result, indent=2) + '\n')
    else:
        assert result == json.loads(args.fixture.read_text())
    print(f"{len(result['cases'])} native addItem cases with observed call/cleanup boundaries")
