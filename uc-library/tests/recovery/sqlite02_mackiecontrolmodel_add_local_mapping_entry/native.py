"""Execute verified ARM ranges for five local MackieControlModel methods."""
from functools import cmp_to_key
from hashlib import sha256
import io
import json
from pathlib import Path
import struct

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import (
    UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3,
    UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC,
)

PACKETS = Path('temp/recovery-work/sqlite-issued/packet')
PREFIX = 'sqlite02_mackiecontrolmodel_'
SUFFIX = {
    'mapping': 'add_local_mapping_entry', 'meter': 'update_local_meter',
    'ring': 'update_local_vpot_ring', 'reset': 'reset_local_faders',
    'display': 'update_local_display_data',
}
REGS = [UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3]
MODEL, PANEL, PANEL_TABLE = 0x50000000, 0x50002000, 0x50002200
TAG_TABLE, NOTE_TABLE, STATES, ENTRY = (0x50003000, 0x50004000, 0x50005000, 0x50006000)
STACK, END = 0x5000f000, 0x5000ff00
TOUCH, FADER = 0xc0624, 0xc0398
TARGETS = {8: ('L', 0xbf868), 16: ('F', 0xbf8b8), 20: ('M', 0xbfd10),
           24: ('V', 0xbfdd4), 28: ('T', 0xbf824)}
SORT = {0xc0174, 0xc01a0}


def packet(kind):
    return PACKETS / (PREFIX + SUFFIX[kind]) / 'CONTEXT.json'


def signed(value):
    return value - 2**32 if value >= 2**31 else value


def packed(*values):
    return struct.pack('<' + 'I' * len(values), *(v & 0xffffffff for v in values))


def digest(value):
    return sha256(value).hexdigest()


def case_inputs(kind):
    if kind == 'mapping':
        return [f'{n} {a} {b} {s}' for n in (0, 3, 109, 110) for a,b,s in
                [(1000, 999, -1), (9, -1, 35), (-1, 100, 9), (-1, -1, -1), (7, 88, -4)]]
    if kind == 'meter':
        return ['-1 13', '8 13', '0 1 0 2 0 1 0 2 0 14 0 15',
                '7 15 7 13 7 14 7 15 7 0', '3 -2 3 0 3 12 3 13',
                '6 14 6 14 6 15 6 15 6 10']
    if kind == 'ring':
        return [f'{i} {value}' for i,value in
                [(-1, 9), (8, 9), (0, 0), (7, 1), (3, 11), (4, 22),
                 (5, 38), (6, 54), (0, 64), (1, 86), (2, 105), (7, 123), (8, 64)]]
    if kind == 'reset':
        return [f'{omit} {mask}' for omit in (0, 1) for mask in (0, 1, 257, 510, 511)]
    patterns = [bytes(112), bytes(65 + i % 26 for i in range(112)),
                bytes(0 if i % 3 == 0 else 33 + i % 90 for i in range(112)),
                bytes(0 if i < 56 else 128 + i % 40 for i in range(112))]
    return [p.hex() for p in patterns]


class Arm:
    def __init__(self, elf):
        self.uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        self.uc.mem_map(0x8000, 0x400000)
        self.uc.mem_map(MODEL, 0x10000)
        self.uc.mem_map(0x60000000, 0x1000)
        for segment in elf.iter_segments():
            if segment['p_type'] == 'PT_LOAD':
                self.uc.mem_write(segment['p_vaddr'], segment.data())
        self.uc.reg_write(UC_ARM_REG_SP, STACK)

    def read(self, addr, size):
        return bytes(self.uc.mem_read(addr, size))

    def word(self, addr):
        return int.from_bytes(self.read(addr, 4), 'little')

    def write(self, addr, *values):
        self.uc.mem_write(addr, packed(*values))

    def string(self, addr):
        data = bytearray()
        while byte := self.read(addr + len(data), 1)[0]:
            data.append(byte)
            assert len(data) <= 32
        return bytes(data)

    def call(self, addr, *args):
        for reg, value in zip(REGS, args):
            self.uc.reg_write(reg, value & 0xffffffff)
        self.uc.reg_write(UC_ARM_REG_LR, END)
        self.uc.emu_start(addr, END, count=1_000_000)
        assert self.uc.reg_read(UC_ARM_REG_PC) == END
        return self.uc.reg_read(UC_ARM_REG_R0)


def select(data):
    return data['originals'][0]['original']


def make(kind):
    orig = select(json.loads(packet(kind).read_text()))
    blob = Path(orig['elf_path']).read_bytes()
    assert digest(blob) == orig['elf']
    elf = ELFFile(io.BytesIO(blob))
    symbols = {s.name: s for s in elf.get_section_by_name('.symtab').iter_symbols() if s.name}

    def verify(name):
        sym = symbols[name]
        sec = elf.get_section(sym['st_shndx'])
        off = sec['sh_offset'] + sym['st_value'] - sec['sh_addr']
        content = blob[off:off + sym['st_size']]
        assert content == sec.data()[off - sec['sh_offset']:off - sec['sh_offset'] + sym['st_size']]
        return dict(mangled=name, address=sym['st_value'], section=sym['st_shndx'],
                    section_name=sec.name, file_offset=off, size=sym['st_size'],
                    range_sha256=digest(content))

    target = verify(orig['mangled'])
    assert all(target[k] == orig[k] for k in target)
    assert blob[target['file_offset']:target['file_offset'] + target['size']].hex() == orig['range_hex']
    scope = {
        'mapping': 'Initialized unique local mapping rows, negative keys/state, capacity and both native comparators.',
        'meter': 'Bounded local interpreted channels and signed levels, monotonic peaks, clip LED transitions.',
        'ring': 'Local interpreted VPot values, style branches, float bits and enabled flag.',
        'reset': 'Native concrete reset and touch release, touched state/cache and fader callbacks with unbound MIDI sink.',
        'display': 'Initialized 112-byte local display, embedded NUL and high-bit bytes, independent seven-byte row segments and output ordering.',
    }[kind]
    known = {'mapping': SORT, 'reset': {TOUCH, FADER, 0xc0480, 0x1f06e0, 0x1eaa88},
             'meter': {0x187314, 0x1873f0, 0x187798, 0x1eaa88},
             'ring': {0x187314, 0x187588, 0x1eaa88},
             'display': {0x1eaa88}}
    selected = []
    for a in sorted(known[kind]):
        names = sorted(name for name, s in symbols.items() if s['st_value'] == a and s['st_size'])
        assert names, hex(a)
        selected.append(verify(names[0]))
    cases = []
    for payload in case_inputs(kind):
        initial = [int(x) for x in payload.split()] if kind != 'display' else []
        arm = Arm(elf)
        assert all(arm.word(0x1eaa88 + 108 + offset) == address for offset, (_, address) in TARGETS.items())
        assert arm.word(0x1f06e0 + 8 + 0x1c) == TOUCH
        arm.write(MODEL, 0x1f06e8)
        arm.write(MODEL + 0xae4, PANEL)
        arm.write(PANEL, PANEL_TABLE)
        event_lines, touch_calls, sort_calls = [], [], []
        hooks = dict(TARGETS)
        for offset in hooks:
            arm.write(PANEL_TABLE + offset, 0x60000000 + offset)
        comparator = Arm(elf) if kind == 'mapping' else None

        def hook(uc, addr, size, _):
            r0, r1, r2, r3 = (uc.reg_read(r) for r in REGS)
            if addr == TOUCH:
                touch_calls.append([r1, r2])
                return
            if 0x60000000 <= addr < 0x60001000:
                op, _ = hooks[addr - 0x60000000]
                assert r0 == PANEL
                if op == 'T':
                    line = f'{op} {r1} {r3} {arm.string(r2).hex()}'
                elif op == 'V':
                    enable = arm.word(uc.reg_read(UC_ARM_REG_SP))
                    line = f'{op} {r1} {r2} {r3} {enable}'
                else:
                    line = f'{op} {r1} {r2}'
                event_lines.append(line)
            elif addr == 0x24268 and kind == 'display':
                # Pinned CStringBuffer initialization with null text sets byte 0.
                # Old Core ELF implementation excluded per project policy.
                assert r1 == 0
                uc.mem_write(r0, b'\0')
            elif addr == 0xb02c and kind == 'display':
                uc.reg_write(UC_ARM_REG_R0, len(arm.string(r0)))
            elif addr == 0xaf84 and kind == 'display':
                uc.mem_write(r0, arm.string(r0) + arm.string(r1)[:r2] + b'\0')
            elif addr == 0xaa44 and kind == 'mapping':
                assert r2 == 12 and r3 in SORT and r1 <= 110
                sort_calls.append([r3, r1])
                rows = [arm.read(r0 + i * 12, 12) for i in range(r1)]

                def compare(left, right):
                    comparator.uc.mem_write(ENTRY, left + right)
                    return signed(comparator.call(r3, ENTRY, ENTRY + 12))

                rows.sort(key=cmp_to_key(compare))
                uc.mem_write(r0, b''.join(rows))
            else:
                return
            uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))

        arm.uc.hook_add(UC_HOOK_CODE, hook)
        if kind == 'mapping':
            n, tag, note, index = initial
            for table, offset in ((TAG_TABLE, 4), (NOTE_TABLE, 0x534)):
                arm.write(MODEL + offset, table, n)
                for i in range(n):
                    arm.write(table + i * 12, 2 * i, 2 * i + 1, i)
            arm.write(MODEL + 0xa64, STATES, n)
            arm.uc.mem_write(STATES, bytes([1]) * n)
            arm.write(ENTRY, tag, note, index)
            arm.call(target['address'], MODEL, ENTRY)
            for table, offset in ((TAG_TABLE, 8), (NOTE_TABLE, 0x538)):
                count = arm.word(MODEL + offset)
                event_lines.append('A ' + str(count))
                for i in range(count):
                    row = [signed(arm.word(table + i * 12 + j * 4)) for j in range(3)]
                    event_lines.append(' '.join(map(str, row)))
            n = arm.word(MODEL + 0xa68)
            event_lines.append('B ' + arm.read(STATES, n).hex())
            assert [signed(arm.word(ENTRY + i * 4)) for i in range(3)] == initial[1:]
        elif kind in ('meter', 'ring'):
            for channel, val in zip(initial[::2], initial[1::2]):
                arm.call(target['address'], MODEL, channel, val)
            if kind == 'meter':
                event_lines.append('P ' + ' '.join(str(arm.word(MODEL + 0xba4 + 4 * i)) for i in range(8)))
        elif kind == 'reset':
            omit, mask = initial
            arm.uc.mem_write(MODEL + 0xadc, bytes([omit]))
            arm.uc.mem_write(MODEL + 0xb76, bytes(mask >> i & 1 for i in range(9)))
            arm.write(MODEL + 0xb80, *range(9))
            arm.call(target['address'], MODEL)
            event_lines.append('C ' + arm.read(MODEL + 0xb76, 9).hex() + ' ' +
                               ' '.join(str(signed(arm.word(MODEL + 0xb80 + 4 * i))) for i in range(9)))
        else:
            arm.uc.mem_write(MODEL + 0xaf8, bytes.fromhex(payload))
            arm.call(target['address'], MODEL)
            assert arm.read(MODEL + 0xaf8, 112) == bytes.fromhex(payload)
        cases.append(dict(input=f'{kind} {payload}', expected=[line.rstrip() for line in event_lines],
                          native_touch_calls=touch_calls, native_sort_calls=sort_calls))
    return dict(scope=scope, cases=cases, elf=orig['elf'], target=target, supporting_ranges=selected)
