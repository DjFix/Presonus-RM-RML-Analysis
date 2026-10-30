#!/usr/bin/env python3
"""Execute original Panel DbTable instructions, retaining true compiler float helpers."""
import argparse
import ctypes
import hashlib
import json
from pathlib import Path
import random
import struct
import unicorn
from unicorn import arm_const as arm
from capstone import Cs, CS_ARCH_ARM, CS_MODE_ARM
from elftools.elf.elffile import ELFFile

PREFIX = '_ZN8Presonus5Panel7DbTable'
NAMES = {
    'A': PREFIX + 'C1EPKfi', 'B': PREFIX + 'C2EPKfi',
    'S': PREFIX + '5setupEPKfi', 'R': PREFIX + '10setDbRangeEff',
    'C': '_ZNK8Presonus5Panel7DbTable8getCountEv',
    'G': '_ZNK8Presonus5Panel7DbTable15getStepFromGainEf',
    'N': '_ZNK8Presonus5Panel7DbTable23getStepFromNormalizedDBEf',
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bits(value):
    return struct.unpack('<I', struct.pack('<f', value))[0]


def fp(value):
    return struct.unpack('<f', struct.pack('<I', value))[0]


class Original:
    heap, stack, stop = 0x10000000, 0x20000000, 0x30000000

    def __init__(self, root, role, evidence):
        directory = root / 'uc-library/recovered-all' / role
        self.manifest = json.loads((directory / 'manifest.json').read_text())
        path = root / self.manifest['path']
        assert sha(path) == self.manifest['sha256']
        raw = path.read_bytes()
        self.all_symbols = json.loads((directory / 'symbols.json').read_text())
        self.symbols = {s['mangled']: s for s in self.all_symbols if s['mangled'] in NAMES.values()}
        assert len(self.symbols) == 7
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
        self.pow_calls = 0
        self.pow_address = next(s['address'] for s in self.all_symbols if s['mangled'] == 'powf@@GLIBC_2.4')
        math = ctypes.CDLL('libm.so.6')
        self.powf = math.powf
        self.powf.argtypes = (ctypes.c_float, ctypes.c_float)
        self.powf.restype = ctypes.c_float

        def imported_powf(u, address, size, data):
            result = self.powf(fp(u.reg_read(arm.UC_ARM_REG_R0)), fp(u.reg_read(arm.UC_ARM_REG_R1)))
            u.reg_write(arm.UC_ARM_REG_R0, bits(result))
            u.reg_write(arm.UC_ARM_REG_PC, u.reg_read(arm.UC_ARM_REG_LR))
            self.pow_calls += 1

        self.u.hook_add(unicorn.UC_HOOK_CODE, imported_powf, begin=self.pow_address, end=self.pow_address)
        cs = Cs(CS_ARCH_ARM, CS_MODE_ARM)
        instructions = {}
        for name, symbol in self.symbols.items():
            instructions[name] = [dict(address=i.address, mnemonic=i.mnemonic, operands=i.op_str)
                                  for i in cs.disasm((directory / symbol['export_path']).read_bytes(), symbol['address'])]
        (evidence / (role + '-instructions.json')).write_text(json.dumps(instructions, indent=2) + '\n')

    def call(self, op, before, a, b, source):
        u = self.u
        for i in range(13):
            u.reg_write(getattr(arm, f'UC_ARM_REG_R{i}'), 0)
        u.reg_write(arm.UC_ARM_REG_CPSR, 0x10)
        u.reg_write(arm.UC_ARM_REG_SP, self.stack + 0xff00)
        u.reg_write(arm.UC_ARM_REG_LR, self.stop)
        u.mem_write(self.heap, b'\x5a' * 512)
        u.mem_write(self.heap + 64, struct.pack('<35I', *before))
        u.mem_write(self.heap + 0x1000, struct.pack('<16I', *source))
        u.reg_write(arm.UC_ARM_REG_R0, self.heap + 64)
        if op in 'ABS':
            u.reg_write(arm.UC_ARM_REG_R1, self.heap + 0x1000 if 0 < a < 17 else 0)
            u.reg_write(arm.UC_ARM_REG_R2, a)
        else:
            u.reg_write(arm.UC_ARM_REG_R1, a)
            u.reg_write(arm.UC_ARM_REG_R2, b)
        u.emu_start(self.symbols[NAMES[op]]['address'], self.stop, count=20000)
        assert u.reg_read(arm.UC_ARM_REG_PC) == self.stop
        assert u.reg_read(arm.UC_ARM_REG_SP) == self.stack + 0xff00
        assert bytes(u.mem_read(self.heap, 64)) == b'\x5a' * 64
        assert bytes(u.mem_read(self.heap + 204, 308)) == b'\x5a' * 308
        assert bytes(u.mem_read(self.heap + 0x1000, 64)) == struct.pack('<16I', *source)
        state = list(struct.unpack('<35I', u.mem_read(self.heap + 64, 140)))
        result = u.reg_read(arm.UC_ARM_REG_R0) if op in 'CGN' else 0
        return result, state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repository', type=Path)
    args = parser.parse_args()
    dest = args.repository / 'uc-library/validation/panel-db-table'
    dest.mkdir(parents=True, exist_ok=False)
    rng = random.Random(0x44425442)
    patterns = [bits(v) for v in [-200, -144, -120, -90, -60, -20, -6, 0, 6, 20, 80, 100, -144, -20, 0, 6]]
    cases = []
    for count in [-2147483648, -1, 0, *range(1, 17)]:
        for iteration in range(8):
            state = [count & 0xffffffff] + [bits(rng.uniform(-20, 20)) for _ in range(32)] + [bits(-144), bits(0)]
            data = patterns[iteration:] + patterns[:iteration]
            for op in 'ABS':
                cases.append((op, state, count & 0xffffffff, 0, data))
            cases.append(('C', state, 0, 0, data))
            for minimum, maximum in [(-144, 0), (6, -144), (0, 0), (-1e30, 1e30)]:
                cases.append(('R', state, bits(minimum), bits(maximum), data))
    specials = [0, 0x80000000, bits(-144), bits(-20), bits(1), bits(16),
                0x7f800000, 0xff800000, 0x7fc00000, 0xffc00000,
                1, 0x80000001, 0x7f7fffff, 0xff7fffff]
    for _ in range(256):
        count = rng.randrange(-1, 17)
        gains = sorted(rng.uniform(-5, 5) for _ in range(16))
        db = sorted(rng.uniform(-150, 20) for _ in range(16))
        if rng.randrange(4) == 0:
            rng.shuffle(gains)
            rng.shuffle(db)
        if rng.randrange(4) == 0:
            gains[4] = gains[3]
            db[4] = db[3]
        state = [count & 0xffffffff] + list(map(bits, gains + db)) + [bits(rng.uniform(-160, 20)), bits(rng.uniform(-160, 20))]
        arguments = specials + [bits(rng.uniform(-200, 200)) for _ in range(8)]
        for index in range(16):
            for value in (bits(gains[index]), bits(db[index])):
                arguments.extend([value, value - 1 if value else 1, value + 1])
        for a in arguments:
            for op in 'GN':
                cases.append((op, state, a, 0, patterns))
    counts = {op: 0 for op in NAMES}
    originals = {}
    with (dest / 'arm-vectors.txt').open('w') as output:
        for role_index, role in enumerate(('client', 'server')):
            original = Original(args.repository, role, dest)
            for op, before, a, b, data in cases:
                result, after = original.call(op, before, a, b, data)
                output.write(' '.join(map(str, [op, role_index, a, b, result, *before, *data, *after])) + '\n')
                counts[op] += 1
            executed = [s for s in original.all_symbols if s['kind'] == 'STT_FUNC' and isinstance(s['section'], int) and any(s['address'] <= block < s['address'] + s['size'] for block in original.blocks)]
            originals[role] = dict(sha256=original.manifest['sha256'], source=original.manifest['path'],
                                   functions=list(original.symbols.values()), basic_blocks=sorted(original.blocks),
                                   executed_function_ranges=executed, modeled_powf_calls=original.pow_calls,
                                   imported_powf_address=original.pow_address)
            print(json.dumps(dict(role=role, completed_cases=len(cases), powf_calls=original.pow_calls)), flush=True)
    report = dict(originals=originals, counts=counts, total_cases=sum(counts.values()),
                  vectors_sha256=sha(dest / 'arm-vectors.txt'), unicorn_version=unicorn.__version__,
                  domain='Signed count <=0 or 1..16; valid nonoverlapping arrays for positive counts; full state/sentinel comparisons; ascending/unsorted/duplicate threshold tables; finite/signedzero/infinity/quietNaN/subnormal query inputs; threshold and neighboring float bit patterns. Setup math inputs are listed in generator, no oversized tables.',
                  dependency_model='Original application instructions and original __aeabi/libgcc soft-float instructions executed. Only imported powf is modeled with native Linux libm powf; this validates application call arguments/state changes, not original ARM libm behavior or exact historical math implementation.',
                  original_full_verification=False, original_arm_abi_compatible=False, hardware_verified=False)
    (dest / 'arm-oracle.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(total_cases=report['total_cases'], counts=counts)), flush=True)


if __name__ == '__main__':
    main()
