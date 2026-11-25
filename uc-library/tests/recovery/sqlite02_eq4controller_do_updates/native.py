#!/usr/bin/env python3
"""Execute the ARM EQ4 methods and their native application dependencies offline."""
from hashlib import sha256
from io import BytesIO
import json
import math
from pathlib import Path
import struct

from elftools.elf.elffile import ELFFile
from unicorn import UC_ARCH_ARM, UC_HOOK_CODE, UC_MODE_ARM, Uc
from unicorn import arm_const as arm

ROOT = Path.cwd()
PACKETS = ROOT / 'temp/recovery-work/sqlite-issued/packet'
PREFIX = 'sqlite02_eq4controller_'
TASKS = ('complete_construct', 'base_construct', 'complete_destroy',
         'deleting_destroy', 'do_updates')
ELF = 'rootfs/RML16AI_Rack_13731/home/root/mixer'
CONTROLLER = '_ZN8Presonus3Dsp10Controller'
EQ = '_ZN8Presonus3Dsp12EQController'
BIQUAD = '_ZN3DSP10BiquadCalcIdLb0EE'
OBSERVED = {
    'base': EQ + 'C2EiiPKNS0_19ParamDescriptorListE',
    'descriptor': '_ZN8Presonus3Dsp11EqParamListC1Ev',
    'controller_constructor': CONTROLLER + 'C2EiPKNS0_19ParamDescriptorListE',
    'controller_destructor': CONTROLLER + 'D2Ev',
    'defaults': CONTROLLER + '16setDefaultValuesEv',
    'setup': EQ + '12setupProcessERKNS0_13SetupPropertyE',
    'set_params': BIQUAD + '9setParamsEifff',
    'calculator_flush': BIQUAD + '5flushEv',
    'flush': CONTROLLER + '21flushParameterChangesEv',
    'send': CONTROLLER + '12sendPropertyERNS0_15ChannelPropertyEb',
    'bypass_literal': '_ZZN8Presonus3Dsp13EQ4Controller9doUpdatesEvE5C.217',
    'vtable': '_ZTVN8Presonus3Dsp13EQ4ControllerE',
    'descriptor_storage': '_ZZN8Presonus3Dsp11EqParamList8instanceEvE11theInstance',
}
REGS = [getattr(arm, f'UC_ARM_REG_R{i}') for i in range(13)]
STACK, STOP, OBJECT, HEAP = 0x1000ff00, 0x20000000, 0x30000000, 0x40000000
TARGET, TABLE, SET_PROPERTY, RELEASE, SETUP = [0x50000000 + i * 0x100 for i in range(5)]


def digest(data):
    return sha256(data).hexdigest()


def fbits(value):
    return struct.unpack('<I', struct.pack('<f', value))[0]


class Oracle:
    def __init__(self):
        raw = (ROOT / ELF).read_bytes()
        self.elf = ELFFile(BytesIO(raw))
        self.symtab = self.elf.get_section_by_name('.symtab')
        self.dynsym = self.elf.get_section_by_name('.dynsym')
        self.originals = {}
        for task in TASKS:
            packet = PACKETS / (PREFIX + task) / 'CONTEXT.json'
            original = json.loads(packet.read_text())['originals'][0]['original']
            identity = self.identity(original['mangled'])
            assert f'{digest(raw)}' == original['elf']
            for key in ('address', 'section', 'size', 'range_sha256', 'file_offset'):
                assert original[key] == identity[key], (task, key)
            assert bytes.fromhex(original['range_hex']) == raw[
                identity['file_offset']:identity['file_offset'] + identity['size']]
            self.originals[task] = identity
        self.providers = {kind: self.identity(name) for kind, name in OBSERVED.items()}
        self.plt = {s['st_value']: s.name for s in self.dynsym.iter_symbols()
                    if s['st_shndx'] == 'SHN_UNDEF' and s['st_value']}
        self.trace_addresses = {row['address']: name for name, row in
                                {**self.providers, **self.originals}.items()}
        self.plt_by_name = {name: address for address, name in self.plt.items()}
        self.raw = raw
        self.u = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        self.u.mem_map(0x8000, 0x4b0000)
        for segment in self.elf.iter_segments():
            if segment['p_type'] == 'PT_LOAD':
                self.u.mem_write(segment['p_vaddr'], segment.data())
        for address, size in ((STACK & ~0xffff, 0x10000), (STOP, 0x1000),
                              (OBJECT, 0x2000), (HEAP, 0x80000),
                              (TARGET, 0x1000)):
            self.u.mem_map(address, size)
        self.u.hook_add(UC_HOOK_CODE, self.on_code)
        self.u.mem_write(TARGET, struct.pack('<I', TABLE))
        self.u.mem_write(TABLE, struct.pack('<3I', SET_PROPERTY, 0, RELEASE))
        self.next_heap = HEAP
        self.live = {}
        self.trace, self.payloads, self.releases = [], [], 0
        self.imports_used = set()

    def identity(self, name):
        sym, = self.symtab.get_symbol_by_name(name)
        address, size, index = (sym[key] for key in ('st_value', 'st_size', 'st_shndx'))
        section = self.elf.get_section(index)
        delta = address - section['sh_addr']
        assert 0 <= delta <= section['sh_size'] - size
        data = section.data()[delta:delta + size]
        return dict(mangled=name, address=address, size=size, section=index,
                    section_name=section.name, file_offset=section['sh_offset'] + delta,
                    range_sha256=digest(data))

    def read(self, address, fmt='I'):
        return struct.unpack('<' + fmt, self.u.mem_read(address, struct.calcsize('<' + fmt)))

    def write(self, address, fmt, *values):
        self.u.mem_write(address, struct.pack('<' + fmt, *values))

    def allocate(self, size):
        addr = self.next_heap
        self.next_heap += (max(1, size) + 15) & ~15
        assert self.next_heap < HEAP + 0x80000
        self.live[addr] = size
        return addr

    def imported(self, name, a, b, c, d):
        self.imports_used.add(name)
        if name in ('_Znwj', '_Znaj', 'malloc'):
            return self.allocate(a)
        if name in ('_ZdlPv', '_ZdaPv', 'free'):
            if a:
                size = self.live.pop(a)
                self.trace.append(['deallocate', a, size, name])
                self.u.mem_write(a, b'\xdd' * size)
            return a
        if name in ('memcpy', 'memmove'):
            if c:
                self.u.mem_write(a, bytes(self.u.mem_read(b, c)))
            return a
        if name == 'memset':
            self.u.mem_write(a, bytes([b & 255]) * c)
            return a
        if name == "strchr":
            data = bytes(self.u.mem_read(a, 256)).split(b"\0", 1)[0] + b"\0"
            index = data.find(bytes([b & 255]))
            return 0 if index < 0 else a + index
        if name in ('strlen', 'strcpy', 'strcmp', 'strncpy'):
            end = lambda p: bytes(self.u.mem_read(p, 256)).split(b'\0', 1)[0]
            s = end(a)
            if name == 'strlen':
                return len(s)
            t = end(b)
            if name == 'strcmp':
                return (s > t) - (s < t)
            self.u.mem_write(a, (t + b'\0') if name == 'strcpy' else t[:c].ljust(c, b'\0'))
            return a
        if name == '__cxa_guard_acquire':
            return int(not self.read(a)[0] & 1)
        if name == '__cxa_guard_release':
            self.write(a, 'I', 1)
            return 0
        if name == '__aeabi_atexit':
            return 0
        if name in ('sin', 'cos', 'pow', 'exp', 'log', 'sqrt', 'tan', 'log10'):
            x, y = struct.unpack('<2d', struct.pack('<4I', a, b, c, d))
            value = math.pow(x, y) if name == 'pow' else getattr(math, name)(x)
            lo, hi = struct.unpack('<2I', struct.pack('<d', value))
            self.u.reg_write(REGS[1], hi)
            return lo
        raise AssertionError(f'unhandled native import {name} {a:#x} {b:#x} {c:#x} {d:#x}')

    def on_code(self, u, address, width, _):
        a, b, c, d = (u.reg_read(r) for r in REGS[:4])
        if address in self.trace_addresses:
            name = self.trace_addresses[address]
            if name == 'base':
                self.trace.append([name, b, c, d])
            elif name == 'set_params':
                sp = u.reg_read(arm.UC_ARM_REG_SP)
                self.trace.append([name, a, b, c, d, self.read(sp)[0]])
            else:
                self.trace.append([name, a])
        if address in self.plt:
            ret = self.imported(self.plt[address], a, b, c, d)
        elif address == SET_PROPERTY:
            assert a == TARGET
            prop_type, size = self.read(b, '2I')
            assert prop_type == 0x69697234 and size == 0x50
            self.payloads.append(list(self.read(b, '20I')))
            ret = 0
        elif address == RELEASE:
            assert a == TARGET
            self.releases += 1
            self.trace.append(['release', a])
            ret = 0
        else:
            return
        u.reg_write(REGS[0], ret & 0xffffffff)
        u.reg_write(arm.UC_ARM_REG_PC, u.reg_read(arm.UC_ARM_REG_LR))

    def invoke(self, name, address, *args):
        entry = {**self.originals, **self.providers}[name]['address']
        for reg in REGS:
            self.u.reg_write(reg, 0)
        self.u.reg_write(arm.UC_ARM_REG_CPSR, 0x10)
        self.u.reg_write(arm.UC_ARM_REG_SP, STACK)
        self.u.reg_write(arm.UC_ARM_REG_LR, STOP)
        for i, value in enumerate((address, *args)):
            self.u.reg_write(REGS[i], value & 0xffffffff)
        self.u.emu_start(entry, STOP, count=1000000)
        assert self.u.reg_read(arm.UC_ARM_REG_PC) == STOP, name
        assert self.u.reg_read(arm.UC_ARM_REG_SP) == STACK, name
        return self.u.reg_read(REGS[0])

    def bands(self, obj):
        storage, count = self.read(obj + 0x28, '2I')
        assert storage == obj + 0x30 and count == 4
        return [storage + 0x140 * i for i in range(count)]

    def scalars(self, obj):
        return [*self.read(obj + 0x08), *self.read(obj + 0x18),
                *self.read(obj + 0x1c, 'B'), *self.read(obj + 0xa30, 'B')]

    def lifecycle(self, task, obj_id):
        self.trace.clear()
        receiver = self.allocate(0xa38)
        if task.endswith('construct'):
            self.invoke(task, receiver, obj_id)
            bands = [list(self.read(p, '4I')) + list(self.read(p + 0x138, '3B')) +
                     list(self.read(p + 0x58, 'B')) for p in self.bands(receiver)]
            descriptor = self.providers['descriptor_storage']['address']
            assert self.read(receiver + 0x0c)[0] == descriptor
            details = dict(scalars=self.scalars(receiver), bands=bands, trace=self.trace[:])
        else:
            self.invoke('complete_construct', receiver, obj_id)
            self.trace.clear()
            self.write(receiver + 0x14, 'I', TARGET)
            self.write(receiver + 0x1d, 'B', 1)
            self.releases = 0
            self.invoke(task, receiver)
            details = dict(released=self.releases, deallocated=receiver not in self.live,
                           trace=self.trace[:])
        return dict(id=obj_id, **details)

    def update(self, through_flush, enabled, mask, dirty, process_dirty, target, rate):
        self.invoke('complete_construct', OBJECT, 9)
        self.write(SETUP + 8, 'f', 48000.)
        self.invoke('setup', OBJECT, SETUP)
        self.write(OBJECT + 0x04, 'i', -49)
        self.write(OBJECT + 0x14, 'I', TARGET if target else 0)
        self.write(OBJECT + 0x1c, 'B', process_dirty)
        self.write(OBJECT + 0x24, 'f', rate)
        self.write(OBJECT + 0xa30, 'B', enabled)
        for i, band in enumerate(self.bands(OBJECT)):
            self.write(band, 'ifff', 6, 1000. + 250. * i, .75 + .125 * i, 3. + i)
            self.write(band + 0x139, '2B', (dirty >> i) & 1, (mask >> i) & 1)
            self.write(band + 0x88, '5d', 2. + i, -3. - i, .5 + i, -.125 - i, 4. + i)
        self.payloads.clear()
        self.trace.clear()
        result = self.invoke('flush' if through_flush else 'do_updates', OBJECT)
        bands = self.bands(OBJECT)
        return dict(input=[through_flush, enabled, mask, dirty, process_dirty, target, rate],
                    flush_result=result if through_flush else None,
                    process_dirty=self.read(OBJECT + 0x1c, 'B')[0],
                    dirty=[self.read(b + 0x139, 'B')[0] for b in bands],
                    payloads=self.payloads[:], trace=self.trace[:],
                    final_coefficients=[list(self.read(b + 0x88, '5d')) for b in bands])


def run(task):
    o = Oracle()
    if task == 'do_updates':
        cases = [o.update(*case) for case in (
            (0, 1, 15, 0, 0, 1, 48000), (1, 1, 15, 0, 0, 1, 48000),
            (1, 1, 15, 0, 1, 1, 48000), (0, 1, 15, 15, 0, 1, 48000),
            (0, 1, 5, 10, 0, 1, 48000), (0, 0, 15, 15, 1, 1, 48000),
            (0, 1, 15, 0, 0, 0, 48000), (1, 1, 15, 15, 1, 0, 48000),
            (1, 1, 15, 15, 1, 1, 0), (1, 1, 13, 5, 1, 1, 48000),
        )]
    else:
        cases = [o.lifecycle(task, obj_id) for obj_id in (0, 9, -8)]
    return dict(original=o.originals[task], providers=o.providers, cases=cases,
                elf=ELF, elf_sha256=digest(o.raw),
                bypass_literal=list(o.read(o.providers['bypass_literal']['address'], '5d')),
                import_boundaries={name: o.plt_by_name[name] for name in sorted(o.imports_used)})


if __name__ == '__main__':
    import sys

    print(json.dumps(run(sys.argv[1]), indent=2))
