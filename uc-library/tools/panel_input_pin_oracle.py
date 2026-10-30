#!/usr/bin/env python3
"""Execute InputPin app instructions with offline file/observer/log contracts."""
import argparse
import hashlib
import json
from pathlib import Path
import random
import struct
from capstone import Cs, CS_ARCH_ARM, CS_MODE_ARM
from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import arm_const as arm

BASE = '_ZN8Presonus5Panel8InputPin'
NAMES = {'S': BASE + '5setupEiPNS0_16PinStateObserverE', 'R': BASE + '4readEv', 'D': BASE + '13read_debounceEv'}
IMPORTS = ('fopen', 'fprintf', 'fclose', 'sprintf', 'fwrite', 'setvbuf', 'rewind', 'fflush', 'fgetc')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def signed(value):
    return struct.unpack('<i', struct.pack('<I', value))[0]


class Original:
    heap, stack, stop = 0x10000000, 0x20000000, 0x30000000

    def __init__(self, root, role, output):
        directory = root / 'uc-library/recovered-all' / role
        self.manifest = json.loads((directory / 'manifest.json').read_text())
        path = root / self.manifest['path']
        assert sha(path) == self.manifest['sha256']
        raw = path.read_bytes()
        self.all_symbols = json.loads((directory / 'symbols.json').read_text())
        self.symbols = {s['mangled']: s for s in self.all_symbols if s['mangled'] in NAMES.values()}
        self.imports = {name: next(s for s in self.all_symbols if s['mangled'].split('@')[0] == name and s['section'] == 'SHN_UNDEF') for name in IMPORTS}
        self.logger = next(s for s in self.all_symbols if s['mangled'] == '_ZN4Core11DebugPrintfEPKcz')
        assert len(self.symbols) == 3
        self.u = unicorn.Uc(unicorn.UC_ARCH_ARM, unicorn.UC_MODE_ARM)
        with path.open('rb') as stream:
            elf = ELFFile(stream)
            segments = [s for s in elf.iter_segments() if s['p_type'] == 'PT_LOAD']
            ranges = []
            for s in segments:
                start, end = int(s['p_vaddr']) & ~4095, (int(s['p_vaddr']) + int(s['p_memsz']) + 4095) & ~4095
                if ranges and start <= ranges[-1][1]:
                    ranges[-1] = (ranges[-1][0], max(end, ranges[-1][1]))
                else:
                    ranges.append((start, end))
            for start, end in ranges:
                self.u.mem_map(start, end - start)
            for s in segments:
                self.u.mem_write(int(s['p_vaddr']), s.data())
            for symbol in self.symbols.values():
                section = elf.get_section(symbol['section'])
                offset = int(section['sh_offset']) + symbol['address'] - int(section['sh_addr'])
                assert offset == symbol['file_offset']
                assert raw[offset:offset + symbol['size']] == (directory / symbol['export_path']).read_bytes()
        for address, size in [(self.heap, 0x10000), (self.stack, 0x10000), (self.stop, 4096)]:
            self.u.mem_map(address, size)
        self.blocks = set()
        self.u.hook_add(unicorn.UC_HOOK_BLOCK, lambda u, a, s, d: self.blocks.add(a))
        for name, symbol in self.imports.items():
            self.u.hook_add(unicorn.UC_HOOK_CODE, self.hook(name), begin=symbol['address'], end=symbol['address'])
        self.u.hook_add(unicorn.UC_HOOK_CODE, self.hook('logger'), begin=self.logger['address'], end=self.logger['address'])
        self.observer_entry = self.heap + 0xf000
        self.u.mem_write(self.observer_entry, b'\x00\xf0\x20\xe3')
        self.u.hook_add(unicorn.UC_HOOK_CODE, self.hook('observer'), begin=self.observer_entry, end=self.observer_entry)
        cs = Cs(CS_ARCH_ARM, CS_MODE_ARM)
        instructions = {name: [dict(address=i.address, mnemonic=i.mnemonic, operands=i.op_str)
                               for i in cs.disasm((directory / symbol['export_path']).read_bytes(), symbol['address'])]
                        for name, symbol in self.symbols.items()}
        (output / (role + '-instructions.json')).write_text(json.dumps(instructions, indent=2) + '\n')

    def file(self, number):
        return self.heap + 0x9000 + number * 0x100 if number else 0

    def file_id(self, pointer):
        if not pointer:
            return 0
        number = (pointer - self.heap - 0x9000) // 0x100
        assert pointer == self.file(number) and 1 <= number <= 4
        return number

    def observer(self, number):
        return self.heap + 0x5000 + number * 0x100 if number else 0

    def observer_id(self, pointer):
        if not pointer:
            return 0
        number = (pointer - self.heap - 0x5000) // 0x100
        assert pointer == self.observer(number) and number in (1, 2)
        return number

    def word(self, address):
        return struct.unpack('<I', self.u.mem_read(address, 4))[0]

    def state(self):
        obj = self.heap + 0x100
        return [self.word(obj + 4), self.word(obj + 8), self.word(obj + 0x10), self.file_id(self.word(obj + 0xc)), self.observer_id(self.word(obj + 0x14))]

    def string(self, address):
        result = bytearray()
        for i in range(1024):
            value = self.u.mem_read(address + i, 1)[0]
            if not value:
                return bytes(result)
            result.append(value)
        raise AssertionError('unterminated boundary string')

    def event(self, kind, args):
        self.trace.append(kind + '|' + ','.join(map(str, args)) + '|' + ','.join(map(str, self.state())) + '\n')

    def hook(self, name):
        def intercept(u, address, size, data):
            r = [u.reg_read(getattr(arm, f'UC_ARM_REG_R{i}')) for i in range(4)]
            result = 0
            if name == 'fopen':
                self.event('O', [self.string(r[0]).hex(), self.string(r[1]).hex()])
                self.open_count += 1
                result = 0 if self.open_count == self.fail_open else self.file(self.open_count)
            elif name == 'fprintf':
                self.event('F', [self.file_id(r[0]), self.string(r[1]).hex(), r[2]])
                result = -1 if self.errors else 1
            elif name == 'fclose':
                self.event('C', [self.file_id(r[0])])
                result = -1 if self.errors else 0
            elif name == 'sprintf':
                fmt = self.string(r[1])
                self.event('S', [fmt.hex(), r[2]])
                text = (fmt.decode() % signed(r[2])).encode()
                assert len(text) < 256
                u.mem_write(r[0], text + b'\0')
                result = len(text)
            elif name == 'fwrite':
                assert r[1] * r[2] <= 256
                self.event('W', [self.file_id(r[3]), bytes(u.mem_read(r[0], r[1] * r[2])).hex(), r[1], r[2]])
                result = 0 if self.errors else r[2]
            elif name == 'setvbuf':
                self.event('B', [self.file_id(r[0]), int(r[1] == 0), r[2], r[3]])
                result = -1 if self.errors else 0
            elif name == 'rewind':
                self.event('A', [self.file_id(r[0])])
            elif name == 'fflush':
                self.event('U', [self.file_id(r[0])])
                result = -1 if self.errors else 0
            elif name == 'fgetc':
                assert self.next_sample < len(self.samples)
                result = self.samples[self.next_sample]
                self.next_sample += 1
                self.event('G', [self.file_id(r[0]), result & 0xffffffff])
            elif name == 'logger':
                message = self.string(r[0])
                assert b'%' not in message
                self.event('L', [message.hex()])
            elif name == 'observer':
                self.event('N', [self.observer_id(r[0]), r[1], r[2]])
                result = 0x13579bdf
            else:
                raise AssertionError(name)
            lr = u.reg_read(arm.UC_ARM_REG_LR)
            for reg, value in [(arm.UC_ARM_REG_R0, result & 0xffffffff), (arm.UC_ARM_REG_R1, 0x2468ace0),
                               (arm.UC_ARM_REG_R2, 0x11223344), (arm.UC_ARM_REG_R3, 0x55667788), (arm.UC_ARM_REG_R12, 0xabcdef01)]:
                u.reg_write(reg, value)
            u.reg_write(arm.UC_ARM_REG_PC, lr)
        return intercept

    def run(self, op, before_state, requested_pin, requested_observer, fail_open, errors, samples):
        u = self.u
        self.fail_open, self.errors, self.samples = fail_open, errors, samples
        self.open_count, self.next_sample, self.trace = 0, 0, []
        obj = self.heap + 0x100
        before = bytearray(b'\xa5' * 0x80)
        for offset, value in [(4, before_state[0]), (8, before_state[1]), (0x10, before_state[2]),
                              (0xc, self.file(before_state[3])), (0x14, self.observer(before_state[4]))]:
            struct.pack_into('<I', before, offset, value)
        u.mem_write(self.heap, b'\x5a' * 0x200)
        u.mem_write(obj, bytes(before))
        for number in (1, 2):
            u.mem_write(self.observer(number), struct.pack('<2I', self.heap + 0x7000, 0xdeadbeef))
        u.mem_write(self.heap + 0x7000, struct.pack('<I', self.observer_entry))
        status = 0
        for _ in range(1 if op == 'S' else len(samples)):
            for i in range(13):
                u.reg_write(getattr(arm, f'UC_ARM_REG_R{i}'), 0)
            u.reg_write(arm.UC_ARM_REG_CPSR, 0x10)
            u.reg_write(arm.UC_ARM_REG_SP, self.stack + 0xff00)
            u.reg_write(arm.UC_ARM_REG_LR, self.stop)
            u.reg_write(arm.UC_ARM_REG_R0, obj)
            u.reg_write(arm.UC_ARM_REG_R1, requested_pin)
            u.reg_write(arm.UC_ARM_REG_R2, self.observer(requested_observer))
            u.emu_start(self.symbols[NAMES[op]]['address'], self.stop, count=20000)
            assert u.reg_read(arm.UC_ARM_REG_PC) == self.stop
            assert u.reg_read(arm.UC_ARM_REG_SP) == self.stack + 0xff00
            status = u.reg_read(arm.UC_ARM_REG_R0) if op == 'S' else 0
        after = bytes(u.mem_read(obj, 0x80))
        allowed = bytearray(before)
        for offset in (4, 8, 0xc, 0x10, 0x14):
            allowed[offset:offset + 4] = after[offset:offset + 4]
        assert after == bytes(allowed)
        assert bytes(u.mem_read(self.heap, 0x100)) == b'\x5a' * 0x100
        assert bytes(u.mem_read(obj + 0x80, 0x80)) == b'\x5a' * 0x80
        for number in (1, 2):
            assert bytes(u.mem_read(self.observer(number), 8)) == struct.pack('<2I', self.heap + 0x7000, 0xdeadbeef)
        return status, self.state(), ''.join(self.trace).encode().hex()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('repository', type=Path)
    args = p.parse_args()
    dest = args.repository / 'uc-library/validation/panel-input-pin'
    dest.mkdir(parents=True, exist_ok=False)
    rng = random.Random(0x50494e53)
    cases = []
    pins = list(range(-128, 128)) + [-2147483648, -2147483647, 2147483646, 2147483647]
    pins.extend(rng.randrange(-2147483648, 2147483648) for _ in range(128))
    for pin in pins:
        for fail in range(4):
            for present in (0, 2):
                before = [rng.getrandbits(32), rng.getrandbits(32), rng.getrandbits(32), rng.choice([0, 4]), rng.randrange(2)]
                cases.append(('S', before, pin & 0xffffffff, present, fail, rng.randrange(2), []))
    for character in range(-1, 256):
        sample = (character - 48) & 0xffffffff
        for state in (sample, sample ^ 1, 0x80000000):
            for present in (0, 1, 2):
                before = [rng.getrandbits(32), state, rng.getrandbits(32), 4, present]
                cases.append(('R', before, 0, 0, 0, rng.randrange(2), [character, character]))
                for last in (sample, sample ^ 1):
                    before = [rng.getrandbits(32), state, last, 4, present]
                    cases.append(('D', before, 0, 0, 0, rng.randrange(2), [character, character, character]))
    counts = {key: 0 for key in NAMES}
    invocations = {key: 0 for key in NAMES}
    originals = {}
    with (dest / 'arm-vectors.txt').open('w') as output:
        for role_index, role in enumerate(('client', 'server')):
            original = Original(args.repository, role, dest)
            for op, before, requested_pin, requested_observer, fail, errors, samples in cases:
                status, after, trace = original.run(op, before, requested_pin, requested_observer, fail, errors, samples)
                output.write(' '.join(map(str, [op, role_index, *before, requested_pin, requested_observer, fail, errors,
                                               len(samples), *samples, status, *after, trace])) + '\n')
                counts[op] += 1
                invocations[op] += 1 if op == 'S' else len(samples)
            boundaries = {s['address'] for s in original.imports.values()} | {original.logger['address'], original.observer_entry}
            assert all(block in boundaries or any(s['address'] <= block < s['address'] + s['size'] for s in original.symbols.values()) for block in original.blocks)
            originals[role] = dict(sha256=original.manifest['sha256'], source=original.manifest['path'], functions=list(original.symbols.values()),
                                   libc_boundary_symbols=original.imports, intercepted_logger=dict(mangled=original.logger['mangled'], address=original.logger['address'], body_executed=False),
                                   observer_boundary='Synthetic first virtual slot captures opaque observer identity and signed32 pin/value; no observer class/API body supplied',
                                   basic_blocks=sorted(original.blocks))
            print(json.dumps(dict(role=role, cases=len(cases))), flush=True)
    report = dict(originals=originals, counts=counts, method_invocations=invocations, total_cases=sum(counts.values()), vectors_sha256=sha(dest / 'arm-vectors.txt'),
                  domain='Offline injected file handles; all standard fgetc returns EOF or0..255; repeated polls/debounce transitions; observer absent/old/new identities; signed8/int32 boundary/random pin numbers; open failures at each stage; ignored write/close/flush/buffering errors; explicit prior state and no actual sysfs/observer/logger effects.',
                  dependency_model='Nine libc entries modeled by bounded file/format contracts; actual sysfs path/mode/write bytes and call order/state snapshots recorded. Core::DebugPrintf is intercepted at entry as an opaque log request only, never executed or implemented. Observer first-slot call is record-only, with opaque class pointer. No hardware/sysfs access.',
                  setup_r0_compared=True, setup_r0_values=[0, 4294967295], poll_r0_ignored=True,
                  original_return_declarations_verified=False, original_full_verification=False, original_arm_abi_compatible=False, hardware_verified=False)
    (dest / 'arm-oracle.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(total_cases=report['total_cases'], counts=counts, method_invocations=invocations)), flush=True)


if __name__ == '__main__':
    main()
