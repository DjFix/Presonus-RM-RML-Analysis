"""Exercise the verified RM ARM app ranges with an isolated synthetic descriptor list."""
import hashlib
import io
import json
from pathlib import Path
import struct
import sys

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_HOOK_CODE, UC_MODE_ARM
from unicorn.arm_const import (
    UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0,
    UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_SP,
)

ROOT = Path('/home/rs/projects/opencs/ai-line-analysis')
SEALED = (ROOT / 'temp/recovery-work/rolling-c001-20261124/packeting/sqlite-cycle02'
          / 'simple_controller01/packet/tasks')
HERE = Path(__file__).parent
RECEIVER = 0x60000000
LIST = 0x60001000
DESCRIPTORS = 0x60002000
ARRAY = 0x60010000
TARGET = 0x60011000
VTABLE = 0x60012000
PROPERTY = 0x60013000
STACK = 0x6001f000
STOP = 0x6001f100
RELEASE = 0x6001f200
SEND = 0x6001f300
FILTER = 0x6001f400
HEAP = 0x61000000

def sha(data):
    return hashlib.sha256(data).hexdigest()

def word(value):
    return struct.unpack('<I', struct.pack('<f', value))[0]

def unpack(data):
    return list(struct.unpack('<' + 'I' * (len(data) // 4), data))

class Original:
    def __init__(self, packet):
        self.row = json.loads(packet.read_text())['originals'][0]['original']
        self.blob = (ROOT / self.row['elf_path']).read_bytes()
        assert sha(self.blob) == self.row['elf']
        self.elf = ELFFile(io.BytesIO(self.blob))
        self.symbols = self.elf.get_section_by_name('.symtab')
        section = self.elf.get_section(self.row['section'])
        symbol, = self.symbols.get_symbol_by_name(self.row['mangled'])
        self.entry = self.row['address']
        delta = self.entry - section['sh_addr']
        size = self.row['size']
        offset = section['sh_offset'] + delta
        body = self.blob[offset:offset + size]
        assert (symbol['st_value'], symbol['st_size'], symbol['st_shndx']) == (
            self.entry, size, self.row['section'])
        assert section.name == self.row['section_name'] and 0 <= delta <= section['sh_size'] - size
        assert offset == self.row['file_offset'] and sha(body) == self.row['range_sha256']
        assert body.hex() == self.row['range_hex']
        plt = self.elf.get_section_by_name('.plt')
        relocations = self.elf.get_section_by_name('.rel.plt')
        names = self.elf.get_section(relocations['sh_link'])
        self.runtime = {
            plt['sh_addr'] + 20 + 12 * index: names.get_symbol(rel['r_info_sym']).name
            for index, rel in enumerate(relocations.iter_relocations())
        }

class Machine:
    def __init__(self, original, count, lookup, skip, has_target, null_list):
        self.cpu = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        self.runtime = original.runtime
        self.messages = []
        self.live = {RECEIVER: 'self'}
        self.events = []
        self.next = HEAP
        self.skip = skip
        self.steps = 0
        self.cpu.mem_map(0x8000, 0x500000)
        for seg in original.elf.iter_segments():
            if seg['p_type'] == 'PT_LOAD':
                self.cpu.mem_write(seg['p_vaddr'], seg.data())
        self.cpu.mem_map(RECEIVER, 0x20000)
        self.cpu.mem_map(HEAP, 0x100000)
        self.cpu.hook_add(UC_HOOK_CODE, self.hook)
        self.put(LIST + 4, ARRAY, count, count, 5, lookup)
        for i in range(count):
            tag = i - 100 if lookup else i
            address = DESCRIPTORS + 0x100 * i
            self.put(ARRAY + 4 * i, address)
            self.put(address, tag, 0, 0, 0, 2 if i % 2 else 0, word((i % 5) - 2.75))
            if i % 2 == 0:
                self.put(address + 0x84, address + 0x90)
                self.put(address + 0x94, word(-4.0), word(4.0))
        self.call(original.entry if 'SimpleControllerC' in original.row['mangled'] else 0xb2d08,
                  RECEIVER, 9, 0 if null_list else LIST)
        if original.entry not in (0xb2d08, 0xb3140):
            self.steps = 0
        if has_target:
            self.put(RECEIVER + 0x14, TARGET)
            self.put(TARGET, VTABLE)
            self.put(VTABLE, SEND, 0, RELEASE)
        if skip is not None:
            vptr, = self.get(RECEIVER)
            self.cpu.mem_write(VTABLE + 0x100, bytes(self.cpu.mem_read(vptr, 0x5c)))
            self.put(VTABLE + 0x158, FILTER)
            self.put(RECEIVER, VTABLE + 0x100)

    def put(self, address, *words):
        self.cpu.mem_write(address, struct.pack('<' + 'I' * len(words),
                                                *(v & 0xffffffff for v in words)))

    def get(self, address, count=1):
        return unpack(self.cpu.mem_read(address, count * 4))

    def call(self, address, *args):
        for reg, arg in zip((UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2), args):
            self.cpu.reg_write(reg, arg & 0xffffffff)
        self.cpu.reg_write(UC_ARM_REG_SP, STACK)
        self.cpu.reg_write(UC_ARM_REG_LR, STOP)
        self.cpu.emu_start(address, STOP, count=500000)
        assert self.cpu.reg_read(UC_ARM_REG_PC) == STOP
        assert self.cpu.reg_read(UC_ARM_REG_SP) == STACK
        return self.cpu.reg_read(UC_ARM_REG_R0)

    def hook(self, cpu, address, _size, _arg):
        self.steps += 1
        reg = cpu.reg_read
        r0, r1 = reg(UC_ARM_REG_R0), reg(UC_ARM_REG_R1)
        result = 0
        if address == SEND:
            size, = self.get(r1 + 4)
            assert r0 == TARGET and size in (20, 496)
            self.messages.append(self.get(r1, size // 4))
        elif address == RELEASE:
            assert r0 == TARGET
            self.events.append('release')
        elif address == FILTER:
            result = int(r1 == (self.skip & 0xffffffff))
        elif address not in self.runtime:
            return
        elif self.runtime[address] == '_Znaj':
            assert r0 and self.next + r0 < HEAP + 0x100000
            result = self.next
            self.live[result] = r0
            self.next += (r0 + 15) & ~15
        elif self.runtime[address] == '_ZdaPv':
            assert r0 in self.live
            integer, = self.get(RECEIVER + 0x40)
            floating, = self.get(RECEIVER + 0x2c)
            self.events.append('free_int' if r0 == integer else 'free_float')
            assert r0 in (integer, floating)
            del self.live[r0]
        elif self.runtime[address] == '_ZdlPv':
            assert r0 == RECEIVER and self.live.pop(r0) == 'self'
            cpu.mem_unmap(RECEIVER, 0x1000)
            self.events.append('delete')
        elif self.runtime[address] == '__cxa_guard_acquire':
            result = int(not self.get(r0)[0] & 1)
        elif self.runtime[address] == '__cxa_guard_release':
            self.put(r0, 1)
        elif self.runtime[address] != '__aeabi_atexit':
            raise AssertionError((hex(address), self.runtime[address]))
        cpu.reg_write(UC_ARM_REG_R0, result)
        cpu.reg_write(UC_ARM_REG_PC, reg(UC_ARM_REG_LR))

    def observe(self, original, count, null_list, operations):
        pending_before_drain = None
        for action, *args in operations:
            if action == 'set':
                self.call(0xb2b68, RECEIVER, *args)
            elif action == 'all':
                self.call(0xb2f50, RECEIVER)
            elif action == 'setup':
                self.put(PROPERTY, 1399157877, 16, *args)
                self.call(0xb30d0, RECEIVER, PROPERTY)
            elif action == 'property':
                self.put(PROPERTY, args[0], 20, *args[1:])
                self.call(0xb3108, RECEIVER, PROPERTY)
            elif action in ('updates', 'drain'):
                if action == 'drain':
                    ptr, size = self.get(RECEIVER + 0x40, 2)
                    pending_before_drain = self.get(ptr, size) if size else []
                self.call(0xb3f48, RECEIVER)
            elif action in ('get', 'internal'):
                address = 0xb2a34 if action == 'get' else 0xb2af0
                self.messages.append([self.call(address, RECEIVER, *args)])
            elif action == 'clear':
                self.cpu.mem_write(RECEIVER + 0x1c, b'\0')
            elif action == 'destroy':
                self.events.clear()
                self.call(original.entry, RECEIVER)
                assert self.live == ({RECEIVER: 'self'} if original.entry == 0xb478c else {})
                return dict(events=self.events, messages=self.messages)
            else:
                raise AssertionError(action)
        ownership = bytes(self.cpu.mem_read(RECEIVER + 0x1c, 2))
        values, = self.get(RECEIVER + 0x2c)
        pending, size = self.get(RECEIVER + 0x40, 2)
        return dict(dirty=ownership[0], owner=ownership[1],
                    rate=self.get(RECEIVER + 0x24)[0], channel=self.get(RECEIVER + 4)[0],
                    identity=self.get(RECEIVER + 0x18)[0],
                    values=self.get(values, count) if count and not null_list else [],
                    pending=self.get(pending, size) if size else [],
                    pending_before_drain=pending_before_drain, messages=self.messages)

def cases(entry):
    set_value, setup, target = 0xb2b68, 0xb30d0, 0xb3108
    lookup = (8, True, None, True, False)
    indexed = (8, False, None, True, False)
    absent = (0, False, None, False, True)
    if entry in (0xb2d08, 0xb3140):
        return [(opts, []) for opts in (lookup, indexed, absent, (0, True, None, True, False))]
    if entry == 0xb2a34:
        keys = [-101, -100, -93, -92, -1, 0, 7, 8, 0x7fffffff, -0x80000000]
        return [(opts, [('get', key) for key in keys]) for opts in (lookup, indexed, absent)]
    if entry == 0xb2af0:
        return [(indexed, [('internal', key) for key in (-0x80000000, -1, 0, 1, 0x7fffffff)])]
    if entry == set_value:
        return [(indexed, [('set', 0, word(-25.0)), ('set', 1, word(25.0)),
                           ('set', 7, word(-0.0)), ('set', 0, word(-8.0)),
                           ('set', -1, word(1.0)), ('set', 8, word(0.5)),
                           ('set', 2, 0x7fc00012), ('set', 2, 0x7fc00012)]),
                (lookup, [('set', -100, word(25.0)), ('set', -93, word(0.25)),
                          ('set', -100, word(0.0)), ('set', -20, word(0.75))]),
                (indexed, [('set', 0, word(-2.75)), ('set', 1, word(-1.75))]),
                (indexed, [('set', 0, word(0.0)), ('clear',), ('set', 0, word(-0.0))]),
                (absent, [('set', 0, word(0.5))])]
    if entry == setup:
        return [(opts, [('setup', rate) for rate in rates]) for opts in (lookup, absent)
                for rates in ((word(-0.0),), (word(44100.0),),
                              (word(48000.0), word(48000.0)),
                              (0x7fc00012, 0x7fc00012))]
    if entry == target:
        return [(lookup, [('property', 0x54617267, 17, 3, 0)]),
                (indexed, [('property', 0x12345678, 17, 3, 0)]),
                (indexed, [('property', 1399157877, word(123.0), 0, 0)]),
                (indexed, [('property', 0x50617261, 0, 0, word(3.0))])]
    if entry == 0xb2f50:
        return [(opts, [('all',)]) for opts in (lookup, indexed, absent)]
    if entry == 0xb3f48:
        return [(lookup, [('updates',)]),
                (lookup, [('set', -100, word(2.0)), ('updates',)]),
                (lookup, [('set', -99, word(0.5)), ('updates',)]),
                ((8, True, -100, True, False),
                 [('set', -100, word(2.0)), ('updates',), ('updates',)]),
                ((126, False, 7, True, False),
                 [('property', 0x54617267, 42, 0, 0), ('updates',), ('updates',)]),
                ((8, False, None, False, False), [('all',), ('updates',)])]
    assert entry in (0xb4728, 0xb478c)
    return [(opts, [('property', 0x54617267, 0, owned, 0), ('destroy',)])
            for opts in (lookup, indexed, absent) for owned in (0, 1)]

def generate(packet):
    original = Original(packet)
    results = []
    for opts, operations in cases(original.entry):
        machine = Machine(original, *opts)
        if opts[3] and not any(op[0] == 'destroy' for op in operations):
            # Compare final queue contents through the real send path, while
            # retaining the unmodified native pending words as evidence.
            operations = [*operations, ('drain',)]
        actual = machine.observe(original, opts[0], opts[-1], operations)
        assert machine.steps > 0
        results.append(dict(options=opts, operations=operations, actual=actual,
                            instruction_count=machine.steps))
    return dict(elf={key: value for key, value in original.row.items() if key != 'range_hex'},
                cases=results)

if __name__ == '__main__':
    task = sys.argv[1] if len(sys.argv) > 1 else HERE.name
    print(json.dumps(generate(SEALED / task / 'CONTEXT.json'), indent=2))
