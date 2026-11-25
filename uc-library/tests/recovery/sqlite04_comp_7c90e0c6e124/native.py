"""Execute original ARM controller methods with explicit host boundaries."""

import argparse
from collections import deque
import ctypes
import hashlib
import json
import struct
import subprocess
from pathlib import Path

import unicorn
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UC_MODE_ARM
from unicorn.arm_const import (
    UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1,
    UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_SP,
)

HERE = Path(__file__).resolve().parent
PACKETS = Path('temp/recovery-work/sqlite-issued/packet')
ELF = Path('rootfs/RML16AI_Rack_13731/home/root/mixer')
ELF_HASH = '9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
PREFIX = '_ZN8Presonus3Dsp14CompController'
GET = '_ZNK8Presonus3Dsp14CompController8getValueEi'
LIBM = ctypes.CDLL('libm.so.6')
MATH = {0xae5c: ('powf', 2), 0xac28: ('logf', 1), 0xacac: ('log10f', 1),
        0xae2c: ('expf', 1)}
for name, arity in MATH.values():
    fun = getattr(LIBM, name)
    fun.argtypes = [ctypes.c_float] * arity
    fun.restype = ctypes.c_float

SELF = 0x600000
TARGET = 0x601000
TARGET_VTABLE = 0x602000
ARRAY = 0x603000
HEAP = 0x610000
STOP = 0x1000
CALLBACK = 0x1010
RELEASE = 0x1020
GUARD = 0x493e7c
LIST = 0x497f94


def sha(data):
    return hashlib.sha256(data).hexdigest()


def bits(value):
    return struct.unpack('<I', struct.pack('<f', value))[0]


def number(word):
    return struct.unpack('<f', struct.pack('<I', word))[0]


class Original:
    def __init__(self, elf_path, contracts):
        self.ranges = {}
        self.segments = []
        blob = elf_path.read_bytes()
        assert sha(blob) == ELF_HASH
        with elf_path.open('rb') as handle:
            elf = ELFFile(handle)
            symbols = {}
            for sym in elf.get_section_by_name('.symtab').iter_symbols():
                if sym.name != '_ZN3DSPL10SinglePoleEff' or sym['st_value'] == 0xb492c:
                    symbols[sym.name] = sym
            support = (
                '_ZN3DSPL10SinglePoleEff',
                '_ZN8Presonus3Dsp10Controller12sendPropertyERNS0_15ChannelPropertyEb',
                '_ZN8Presonus3Dsp10ControllerC2EiPKNS0_19ParamDescriptorListE',
                '_ZN8Presonus3Dsp10ControllerD2Ev',
                '_ZN8Presonus3Dsp10Controller9setTargetEPN4Core16IPropertyHandlerE',
                '_ZN8Presonus3Dsp10Controller16setDefaultValuesEv',
                '_ZNK8Presonus3Dsp10Controller10boundValueEif',
                '_ZN8Presonus3Dsp19CompressorParamListC1Ev',
            )
            for name in [*contracts, *support]:
                sym = symbols[name]
                address, size, index = (sym[k] for k in ('st_value', 'st_size', 'st_shndx'))
                section = elf.get_section(index)
                offset = section['sh_offset'] + address - section['sh_addr']
                raw = blob[offset:offset + size]
                assert size and section.name == '.text'
                info = dict(address=address, size=size, section=index,
                            section_name=section.name, file_offset=offset,
                            range_sha256=sha(raw))
                if name in contracts:
                    assert all(contracts[name][k] == v for k, v in info.items())
                    assert raw == bytes.fromhex(contracts[name]['range_hex'])
                self.ranges[name] = info
            self.segments = [(s['p_vaddr'], s.data()) for s in elf.iter_segments()
                             if s['p_type'] == 'PT_LOAD']


def provider(*argv):
    PROVIDER.stdin.write(' '.join(map(str, argv)) + '\n')
    PROVIDER.stdin.flush()
    output = PROVIDER.stdout.readline()
    assert output, argv
    return [int(value) for value in output.split()]


class Execution:
    def __init__(self, original):
        self.original = original
        self.u = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        self.u.mem_map(0, 0x500000)
        for address, segment in original.segments:
            self.u.mem_write(address, segment)
        self.u.mem_map(SELF, 0x40000)
        self.u.hook_add(UC_HOOK_CODE, self.code)
        self.u.hook_add(UC_HOOK_MEM_WRITE, self.write)
        self.word(TARGET, TARGET_VTABLE)
        self.word(TARGET_VTABLE, CALLBACK)
        self.word(TARGET_VTABLE + 8, RELEASE)
        self.cursor = HEAP
        self.live = {SELF, TARGET}
        self.trace = []
        self.writes = []
        self.recent = deque(maxlen=8)

    def word(self, address, value=None):
        if value is None:
            return struct.unpack('<I', self.u.mem_read(address, 4))[0]
        self.u.mem_write(address, struct.pack('<I', value & 0xffffffff))

    def put(self, fields):
        for offset, value in fields.items():
            self.word(SELF + offset, bits(value) if isinstance(value, float) else value)

    def alloc(self, size):
        address = self.cursor
        self.cursor += (size + 15) & ~15
        self.live.add(address)
        return address

    def free(self, address):
        self.live.remove(address)
        self.u.mem_write(address, b'\xdd' * (0x168 if address == SELF else 4))

    def write(self, u, access, address, size, value, _):
        if SELF <= address < SELF + 0x168:
            self.writes.append([address - SELF, size, value & ((1 << (size * 8)) - 1)])

    def code(self, u, pc, size, _):
        self.recent.append(hex(pc))
        a, b, c = (u.reg_read(r) for r in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2))
        result = None
        if pc == STOP:
            self.stopped = True
            u.emu_stop()
            return
        if pc in MATH:
            name, arity = MATH[pc]
            inputs = [a, b][:arity]
            result = bits(getattr(LIBM, name)(*map(number, inputs)))
            self.trace.append([name, inputs, result])
        elif pc == 0xae68:
            u.mem_write(a, bytes(u.mem_read(b, c)))
            result = a
        elif pc == CALLBACK:
            assert a == TARGET and a in self.live
            self.trace.append(['property', bytes(u.mem_read(b, 304)).hex()])
        elif pc == RELEASE:
            assert a == TARGET
            self.free(a)
            self.trace.append(['release'])
        elif pc == 0xac10:
            assert a == SELF
            self.free(a)
            self.trace.append(['delete'])
        elif pc == 0xb030:
            assert a == GUARD and self.word(a) == 0
            self.trace.append(['guard_acquire'])
            result = 1
        elif pc == 0xaa3c:
            assert a == GUARD
            self.word(a, 1)
            self.trace.append(['guard_release'])
        elif pc == 0xadb4:
            assert a == LIST
            self.trace.append(['register_exit', b, c])
            result = 0
        elif pc == 0xb6d7c:
            assert a == LIST and 0 <= b <= 15, (hex(a), b)
            capacity, = provider('resize', b, self.word(a + 16))
            assert capacity >= self.word(a + 8)
            self.word(a + 4, ARRAY if capacity else 0)
            self.word(a + 12, capacity)
            self.trace.append(['pinned_vector_resize', b, capacity])
            result = int(capacity >= 0)
        elif pc == 0xa7e4:
            result = self.alloc(a)
        elif pc == 0x110810:
            name = bytes(u.mem_read(a, 24)).split(b'\0')[0].decode()
            found, = provider('formatter', name or '-')
            result = self.alloc(4) if found else 0
            self.trace.append(['pinned_formatter', name, found])
        elif pc == 0x112844:
            name = bytes(u.mem_read(a, 16)).split(b'\0')[0].decode()
            found, = provider('create', name or '-')
            result = self.alloc(16) if found else 0
            if found:
                vtable = self.alloc(12)
                self.word(result, vtable)
                self.word(vtable + 8, 0x1048)
            self.trace.append(['pinned_factory', name, found])
        elif pc == 0x1048:
            midpoint = u.reg_read(UC_ARM_REG_R3)
            lo, hi = provider('range', b, c, midpoint)
            self.word(a + 4, lo)
            self.word(a + 8, hi)
            self.trace.append(['pinned_set_range', b, c, midpoint, lo, hi])
        elif pc == 0x111a78:
            lo, hi = provider('linear', b, c)
            vtable = self.alloc(12)
            self.word(a, vtable)
            self.word(vtable + 8, 0x1048)
            self.word(a + 4, lo)
            self.word(a + 8, hi)
            self.trace.append(['pinned_linear_constructor', b, c, lo, hi])
        elif 0x157200 <= pc < 0x157b00 or any(
            r['address'] <= pc < r['address'] + r['size']
            for r in self.original.ranges.values()
        ):
            if pc == 0xb4df0 and self.in_constructor:
                self.trace.append(['default', b, c])
            if pc in (0xb492c, 0xb251c, 0xb29d8, 0xb27e8):
                self.trace.append(['application', pc, a, b, c])
            return
        else:
            raise RuntimeError(f'unexpected native execution at {pc:#x}, {list(self.recent)}, {self.trace[-8:]}')
        if result is not None:
            u.reg_write(UC_ARM_REG_R0, result)
        u.reg_write(UC_ARM_REG_PC, u.reg_read(UC_ARM_REG_LR))

    def call(self, name, b=0, c=0):
        self.trace.clear()
        self.writes.clear()
        self.stopped = False
        self.in_constructor = name.endswith(('C1Ei', 'C2Ei'))
        for reg, value in ((UC_ARM_REG_SP, 0x63ff00), (UC_ARM_REG_LR, STOP),
                           (UC_ARM_REG_R0, SELF), (UC_ARM_REG_R1, b), (UC_ARM_REG_R2, c)):
            self.u.reg_write(reg, value & 0xffffffff)
        target = self.original.ranges[name]['address']
        self.u.emu_start(target, 0x500000, count=200000)
        assert self.stopped, name
        return self.u.reg_read(UC_ARM_REG_R0)


def fixtures(original):
    cases = []
    constructor = PREFIX + 'C1Ei'
    for name in (constructor, PREFIX + 'C2Ei'):
        e = Execution(original)
        for id_value in (-2147483648, 2147483647):
            e.call(name, id_value)
            trace = e.trace.copy()
            writes = e.writes.copy()
            assert [x[1] for x in trace if x[0] == 'default'] == list(range(10))
            assert e.word(SELF + 0x18) == id_value & 0xffffffff
            results = [e.call(GET, i) for i in range(10)]
            cases.append(dict(name=name, kind='construct', inputs=[id_value],
                              expected=[e.word(SELF + 8), e.word(SELF + 0x18),
                                        e.word(SELF + 0x1c), e.word(SELF + 0x20), *results],
                              trace=trace, writes=writes))
    for name in (PREFIX + 'D0Ev', PREFIX + 'D1Ev'):
        for owns in range(2):
            for attached in range(2):
                e = Execution(original)
                e.put({0x14: TARGET if attached else 0, 0x1c: owns << 8})
                e.call(name)
                events = [x[0] for x in e.trace if x[0] in ('release', 'delete')]
                cases.append(dict(name=name, kind='destroy', inputs=[owns, attached],
                                  expected=events, trace=e.trace, writes=e.writes))
    e = Execution(original)
    e.call(constructor)
    for tag in (-2147483648, -1, *range(11), 2147483647):
        for raw in (bits(0.), bits(-0.), bits(-144.), bits(-.001), bits(.001),
                    bits(.1), bits(2.), bits(25.), 0x7fc00000, 0x7f800000, 0xff800000):
            for enabled, dirty in ((0, 0), (1, 0), (0, 7)):
                e.call(constructor)
                e.call(PREFIX + '8setValueEif', 0, bits(float(enabled)))
                e.put({0x1c: dirty, 0x20: 0})
                e.call(PREFIX + '8setValueEif', tag, raw)
                trace = e.trace.copy()
                writes = e.writes.copy()
                results = [e.call(GET, i) for i in range(10)]
                cases.append(dict(name=PREFIX + '8setValueEif', kind='set',
                                  inputs=[tag, raw, enabled, dirty], trace=trace,
                                  writes=writes, expected=[
                                      e.word(SELF + 0x1c), e.word(SELF + 0x20), *results,
                                  ]))
    for tag in (-2147483648, -1, *range(11), 2147483647):
        for raw in (bits(0.), bits(-0.), bits(-145.), bits(-144.), bits(-143.),
                    bits(-.001), bits(.001), bits(2.), bits(25.), 0x7fc00000,
                    0x7f800000, 0xff800000):
            e.call(constructor)
            set_tag = 1 if tag == 9 else tag
            e.call(PREFIX + '8setValueEif', set_tag, raw)
            value = e.call(GET, tag)
            assert not e.writes
            cases.append(dict(name=GET, kind='get', inputs=[tag, set_tag, raw],
                              expected=[value], trace=e.trace))
    for tag, offset in ((3, 0x28), (4, 0x34), (5, 0x30), (6, 0x2c),
                        (7, 0x140), (8, 0x160)):
        for raw in (0, 0x80000000, 0x33877f3e, 0x33877f3f, 0x33877f40,
                    bits(-1.), bits(.25), 0x7f800000, 0x7fc00000):
            e = Execution(original)
            e.put({offset: raw})
            value = e.call(GET, tag)
            assert not e.writes
            cases.append(dict(name=GET, kind='get_raw', inputs=[tag, raw],
                              expected=[value], trace=e.trace))
    for enabled, soft, auto, threshold, ratio, rate, attach in (
        (0, 0, 0, 0, 2, 48000, 1), (1, 0, 0, -20, 4, 44100, 1),
        (1, 1, 1, -18, 6, 96000, 1), (0, 1, 0, -2, 1, 32000, 1),
        (1, 1, 0, -1, 10, 88200, 1), (1, 1, 1, -48, 20, 192000, 0),
        (0, 0, 1, -8, 0, 48000, 0), (1, 1, 1, 0, 2, 48000, 1),
    ):
        e = Execution(original)
        e.call(constructor)
        for tag, value in enumerate([enabled, soft, auto, threshold, ratio, .02, .6, 7]):
            e.call(PREFIX + '8setValueEif', tag, bits(value))
        e.put({0x24: float(rate), 4: 0x89abcdef, 0x14: TARGET if attach else 0})
        e.call(PREFIX + '9doUpdatesEv')
        properties = [x[1] for x in e.trace if x[0] == 'property']
        assert len(properties) == attach
        outputs = list(struct.unpack('<73I', e.u.mem_read(SELF + 0x3c, 292)))
        cases.append(dict(name=PREFIX + '9doUpdatesEv', kind='update',
                          inputs=[enabled, soft, auto, threshold, ratio, rate, attach],
                          expected=properties, outputs=outputs, trace=e.trace,
                          writes=e.writes))
    return cases


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--elf', type=Path, default=ELF)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--provider', type=Path, required=True)
    args = parser.parse_args()
    contracts = {}
    for path in PACKETS.glob('sqlite04_comp_*/CONTEXT.json'):
        original = json.loads(path.read_text())['originals'][0]['original']
        contracts[original['mangled']] = original
    assert len(contracts) == 7
    original = Original(args.elf, contracts)
    global PROVIDER
    with subprocess.Popen([args.provider], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                          text=True) as PROVIDER:
        try:
            cases = fixtures(original)
        finally:
            PROVIDER.stdin.close()
    assert PROVIDER.returncode == 0
    args.out.write_text(json.dumps(dict(
        version=1, elf_sha256=ELF_HASH, native_ranges=original.ranges, cases=cases,
        unicorn_version=unicorn.__version__, producer_sha256=sha(Path(__file__).read_bytes()),
    ), separators=(',', ':')) + '\n')
    print(f'{len(cases)} native executions recorded')


if __name__ == '__main__':
    main()
