#!/usr/bin/env python3
"""Execute pure BitmapDisplay methods through the actual original ELF vtable."""
import argparse
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import random
import struct
from capstone import Cs, CS_ARCH_ARM, CS_MODE_ARM
from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import arm_const as arm

BASE = '_ZN8Presonus5Panel13BitmapDisplay'
CONST = '_ZNK8Presonus5Panel13BitmapDisplay'
NAMES = {'W': CONST + '14getScreenWidthEv', 'H': CONST + '15getScreenHeightEv',
         'G': CONST + '8getPixelEii', 'P': BASE + '8setPixelEiib',
         'F': BASE + '9_fillRectEiiiii', 'R': BASE + '9_fillRectERKNS0_9RectangleEi',
         'A': BASE + '8fillRectERKNS0_9RectangleE', 'E': BASE + '9eraseRectERKNS0_9RectangleE',
         'I': BASE + '10invertRectERKNS0_9RectangleE', 'L': BASE + '6setPenEi',
         'T': BASE + '12setTextColorEi', 'M': BASE + '6moveToEii', 'O': CONST + '6getPosERiS2_'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@lru_cache(maxsize=32)
def initial_frame(seed):
    result = bytearray()
    for _ in range(3072):
        seed = (seed * 1664525 + 1013904223) & 0xffffffff
        result.append(seed >> 24)
    return bytes(result)


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
        assert len(self.symbols) == len(NAMES)
        self.vtable = next(s for s in self.all_symbols if s['mangled'] == '_ZTVN8Presonus5Panel13BitmapDisplayE')
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
            for symbol in [*self.symbols.values(), self.vtable]:
                section = elf.get_section(symbol['section'])
                offset = int(section['sh_offset']) + symbol['address'] - int(section['sh_addr'])
                assert offset == symbol['file_offset']
                assert raw[offset:offset + symbol['size']] == (directory / symbol['export_path']).read_bytes()
        for address, size in [(self.heap, 0x10000), (self.stack, 0x10000), (self.stop, 4096)]:
            self.u.mem_map(address, size)
        self.blocks = set()
        self.u.hook_add(unicorn.UC_HOOK_BLOCK, lambda u, a, s, d: self.blocks.add(a))
        words = struct.unpack('<' + 'I' * (self.vtable['size'] // 4), (directory / self.vtable['export_path']).read_bytes())
        for offset, op in [(4, 'W'), (8, 'H'), (0x30, 'P'), (0x34, 'G')]:
            assert words[2 + offset // 4] == self.symbols[NAMES[op]]['address']
        self.vtable_slots = {hex(offset): self.symbols[NAMES[op]]['mangled'] for offset, op in [(4, 'W'), (8, 'H'), (0x30, 'P'), (0x34, 'G')]}
        cs = Cs(CS_ARCH_ARM, CS_MODE_ARM)
        instructions = {name: [dict(address=i.address, mnemonic=i.mnemonic, operands=i.op_str)
                               for i in cs.disasm((directory / s['export_path']).read_bytes(), s['address'])]
                        for name, s in self.symbols.items()}
        (output / (role + '-instructions.json')).write_text(json.dumps(instructions, indent=2) + '\n')

    def call(self, op, seed, state, args, alias):
        u = self.u
        for i in range(13):
            u.reg_write(getattr(arm, f'UC_ARM_REG_R{i}'), 0)
        u.reg_write(arm.UC_ARM_REG_CPSR, 0x10)
        sp = self.stack + 0xff00
        u.reg_write(arm.UC_ARM_REG_SP, sp)
        u.reg_write(arm.UC_ARM_REG_LR, self.stop)
        address = self.heap + 0x100
        before = bytearray(b'\xa5' * 0xc80)
        struct.pack_into('<I', before, 0, self.vtable['address'] + 8)
        before[8:0xc08] = initial_frame(seed)
        for offset, value in zip((0xc10, 0xc14, 0xc18, 0xc1c), state):
            struct.pack_into('<I', before, offset, value)
        u.mem_write(self.heap, b'\x5a' * 0x100)
        u.mem_write(address, bytes(before))
        u.mem_write(address + len(before), b'\x5a' * 64)
        rect = self.heap + 0x4000
        refs = self.heap + 0x5000
        u.mem_write(rect, struct.pack('<4I', *args[:4]))
        u.mem_write(refs, struct.pack('<2I', 0x01234567, 0x89abcdef))
        u.reg_write(arm.UC_ARM_REG_R0, address)
        for reg, value in zip((arm.UC_ARM_REG_R1, arm.UC_ARM_REG_R2, arm.UC_ARM_REG_R3), args[:3]):
            u.reg_write(reg, value)
        u.mem_write(sp, struct.pack('<2I', args[3], args[4]))
        if op in 'RAEI':
            u.reg_write(arm.UC_ARM_REG_R1, rect)
            u.reg_write(arm.UC_ARM_REG_R2, args[4])
        elif op == 'O':
            u.reg_write(arm.UC_ARM_REG_R1, refs)
            u.reg_write(arm.UC_ARM_REG_R2, refs if alias else refs + 4)
        u.emu_start(self.symbols[NAMES[op]]['address'], self.stop, count=5000000)
        assert u.reg_read(arm.UC_ARM_REG_PC) == self.stop
        assert u.reg_read(arm.UC_ARM_REG_SP) == sp
        assert bytes(u.mem_read(self.heap, 0x100)) == b'\x5a' * 0x100
        assert bytes(u.mem_read(address + len(before), 64)) == b'\x5a' * 64
        after = bytes(u.mem_read(address, len(before)))
        after_state = [struct.unpack_from('<I', after, off)[0] for off in (0xc10, 0xc14, 0xc18, 0xc1c)]
        allowed = bytearray(before)
        allowed[8:0xc08] = after[8:0xc08]
        for offset in (0xc10, 0xc14, 0xc18, 0xc1c):
            allowed[offset:offset + 4] = after[offset:offset + 4]
        assert after == bytes(allowed), 'untracked object field changed'
        assert bytes(u.mem_read(rect, 16)) == struct.pack('<4I', *args[:4])
        refs_after = list(struct.unpack('<2I', u.mem_read(refs, 8)))
        changes = [(i, value) for i, value in enumerate(after[8:0xc08]) if value != before[8 + i]]
        result = u.reg_read(arm.UC_ARM_REG_R0) if op in 'WHGLT' else 0
        return result, after_state, refs_after, changes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repository', type=Path)
    args = parser.parse_args()
    output = args.repository / 'uc-library/validation/panel-bitmap-drawing'
    output.mkdir(parents=True, exist_ok=False)
    rng = random.Random(0x42495453)
    seeds = [rng.getrandbits(32) for _ in range(16)]
    cases = []

    def case(op, a=0, b=0, c=0, d=0, e=0, alias=0):
        cases.append((op, rng.choice(seeds), [rng.getrandbits(32) for _ in range(4)],
                      [v & 0xffffffff for v in (a, b, c, d, e)], alias))

    for y in range(64):
        for x in range(192):
            case('G', x, y)
            case('P', x, y, 0)
            case('P', x, y, 1)
    for _ in range(256):
        offset = rng.randrange(3072)
        y = (offset // 192) * 8 + rng.randrange(8)
        x = offset % 192
        for op in 'GP':
            case(op, x, y, rng.randrange(2))
    for y in (-2147483647, -17, -15, -9, -7, -3, -1):
        for x in (-2147483648, -1, 0, 192, 2147483647):
            for op in 'GP':
                case(op, x, y, 1)
    for y, x in [(-8, 192), (-16, 384), (8, -192), (64, -1), (128, -192)]:
        for op in 'GP':
            case(op, x, y, 1)
    rectangles = [(0, 0, 192, 64), (-2, -2, 3, 3), (190, 62, 8, 8), (191, 63, 1, 1),
                  (192, 64, 1, 1), (193, 65, 10, 10), (0, 0, 0, 0), (1, 1, -1, -1),
                  (191, 63, 0, 0), (100, 40, 192, 64), (-100, -100, 1, 1)]
    rectangles.extend((rng.randrange(-20, 213), rng.randrange(-20, 85), rng.randrange(-10, 33), rng.randrange(-10, 17)) for _ in range(64))
    for x, y, width, height in rectangles:
        for mode in (-2147483648, -1, 0, 1, 2, 3, 2147483647):
            for op in 'FR':
                case(op, x, y, width, height, mode)
        for op in 'AEI':
            case(op, x, y, width, height)
    values = list(range(-128, 128)) + [-2147483648, -2147483647, 2147483646, 2147483647]
    values.extend(rng.randrange(-2147483648, 2147483648) for _ in range(256))
    for value in values:
        case('L', value)
        case('T', value)
        case('M', value, rng.randrange(-2147483648, 2147483648))
        case('O', alias=0)
        case('O', alias=1)
    for _ in seeds:
        case('W')
        case('H')
    counts = {key: 0 for key in NAMES}
    originals = {}
    with (output / 'arm-vectors.txt').open('w') as vectors:
        for role_index, role in enumerate(('client', 'server')):
            original = Original(args.repository, role, output)
            for index, (op, seed, state, values, alias) in enumerate(cases):
                result, after_state, refs_after, changes = original.call(op, seed, state, values, alias)
                vectors.write(' '.join(map(str, [op, role_index, seed, *state, *values, alias, result, *after_state, *refs_after,
                                                len(changes), *(v for pair in changes for v in pair)])) + '\n')
                counts[op] += 1
                if index % 20000 == 0:
                    print(json.dumps(dict(role=role, completed=index)), flush=True)
            executed = [s for s in original.all_symbols if s['kind'] == 'STT_FUNC' and isinstance(s['section'], int)
                        and any(s['address'] <= block < s['address'] + s['size'] for block in original.blocks)]
            assert {s['mangled'] for s in executed} <= set(NAMES.values()), 'unexpected dependency executed'
            originals[role] = dict(sha256=original.manifest['sha256'], source=original.manifest['path'], functions=list(original.symbols.values()),
                                   actual_vtable_symbol=original.vtable, verified_vtable_slots=original.vtable_slots,
                                   executed_function_ranges=executed, basic_blocks=sorted(original.blocks))
            print(json.dumps(dict(role=role, completed_cases=len(cases))), flush=True)
    report = dict(originals=originals, counts=counts, total_cases=sum(counts.values()), vectors_sha256=sha(output / 'arm-vectors.txt'),
                  domain='Exhaustive192x64 screen coordinates read/set0/set1; valid3072-byte backing offsets incl beyond logical height, safe negative-y remainder exits and cross-page coordinates; clipped/minimum-size/negative-origin rectangles with nonoverflowing sums, modes allbranches; int32 pen/color/cursor values, aliased/nonaliased external getPos outputs. Actual BitmapDisplay vtable only; no arbitrary overrides, invalid storage addresses, rectangle sum overflow or lifecycle concurrency.',
                  dependency_model='No modeled function dependencies. All selected original methods and original actual virtual callees executed under Unicorn. Core/mutex/clear/update/device paths excluded.',
                  original_full_verification=False, original_arm_abi_compatible=False, hardware_verified=False)
    (output / 'arm-oracle.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(total_cases=report['total_cases'], counts=counts)), flush=True)


if __name__ == '__main__':
    main()
