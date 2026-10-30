#!/usr/bin/env python3
"""Execute original MeterControl state/configuration methods without hardware/Core."""
import argparse
import json
from pathlib import Path
import random
import struct
from capstone import Cs, CS_ARCH_ARM, CS_MODE_ARM
from elftools.elf.elffile import ELFFile
from unicorn import arm_const as arm
from panel_db_table_oracle import Original, bits, sha

NAMES = {
    'S': '_ZN8Presonus5Panel12MeterControl13setMeterStepsEiiPKfS3_',
    'R': '_ZN8Presonus5Panel12MeterControl10setDbRangeEff',
    'D': '_ZN8Presonus5Panel12MeterControl15setBusDirectionENS1_12BusDirectionE',
    'G': '_ZNK8Presonus5Panel12MeterControl16getNumMeterStepsENS1_12BusDirectionEb',
}
DATA = {'counts': '_ZN8Presonus5Panel12MeterControl13numMeterStepsE',
        'input': '_ZN8Presonus5Panel12MeterControl10inputTableE',
        'output': '_ZN8Presonus5Panel12MeterControl11outputTableE'}


class MeterOriginal(Original):
    def __init__(self, root, role, evidence):
        super().__init__(root, role, evidence)
        self.db_symbols = self.symbols
        self.symbols = {s['mangled']: s for s in self.all_symbols if s['mangled'] in NAMES.values()}
        self.data = {key: next(s for s in self.all_symbols if s['mangled'] == name) for key, name in DATA.items()}
        assert len(self.symbols) == 4
        directory = root / 'uc-library/recovered-all' / role
        path = root / self.manifest['path']
        raw = path.read_bytes()
        cs = Cs(CS_ARCH_ARM, CS_MODE_ARM)
        instructions = {}
        with path.open('rb') as stream:
            elf = ELFFile(stream)
            for symbol in [*self.symbols.values(), *self.data.values()]:
                section = elf.get_section(symbol['section'])
                if section['sh_type'] == 'SHT_NOBITS':
                    assert symbol['size'] == 140 and 'NOBITS' in symbol['storage']
                    continue
                offset = int(section['sh_offset']) + symbol['address'] - int(section['sh_addr'])
                assert offset == symbol['file_offset']
                data = (directory / symbol['export_path']).read_bytes()
                assert data == raw[offset:offset + symbol['size']]
                if symbol['kind'] == 'STT_FUNC':
                    instructions[symbol['mangled']] = [dict(address=i.address, mnemonic=i.mnemonic, operands=i.op_str)
                                                         for i in cs.disasm(data, symbol['address'])]
                else:
                    assert struct.unpack('<2i', data) == (16, 16)
        (evidence / (role + '-meter-instructions.json')).write_text(json.dumps(instructions, indent=2) + '\n')

    def meter_call(self, op, state, a, b, direction, override, override_count, input_steps, output_steps):
        u = self.u
        for i in range(13):
            u.reg_write(getattr(arm, f'UC_ARM_REG_R{i}'), 0)
        u.reg_write(arm.UC_ARM_REG_CPSR, 0x10)
        u.reg_write(arm.UC_ARM_REG_SP, self.stack + 0xff00)
        u.reg_write(arm.UC_ARM_REG_LR, self.stop)
        obj = bytearray(b'\x5a' * 64)
        struct.pack_into('<I', obj, 0x20, self.heap + 0x2000 if override else 0)
        struct.pack_into('<I', obj, 0x24, direction)
        u.mem_write(self.heap, b'\x5a' * 512)
        u.mem_write(self.heap + 64, bytes(obj))
        u.mem_write(self.heap + 0x1000, struct.pack('<16I', *input_steps))
        u.mem_write(self.heap + 0x1800, struct.pack('<16I', *output_steps))
        u.mem_write(self.heap + 0x2000, struct.pack('<I', override_count))
        for key, first, count in [('counts', 0, 2), ('input', 2, 35), ('output', 37, 35)]:
            u.mem_write(self.data[key]['address'], struct.pack('<' + str(count) + 'I', *state[first:first + count]))
        if op == 'S':
            regs = [a, b, self.heap + 0x1000 if 0 < a <= 16 else 0, self.heap + 0x1800 if 0 < b <= 16 else 0]
        elif op == 'R':
            regs = [a, b, 0, 0]
        else:
            regs = [self.heap + 64, a, b, 0]
        for i, value in enumerate(regs):
            u.reg_write(getattr(arm, f'UC_ARM_REG_R{i}'), value)
        u.emu_start(self.symbols[NAMES[op]]['address'], self.stop, count=40000)
        assert u.reg_read(arm.UC_ARM_REG_PC) == self.stop
        assert u.reg_read(arm.UC_ARM_REG_SP) == self.stack + 0xff00
        assert bytes(u.mem_read(self.heap, 64)) == b'\x5a' * 64
        assert bytes(u.mem_read(self.heap + 128, 384)) == b'\x5a' * 384
        after_obj = bytes(u.mem_read(self.heap + 64, 64))
        after_direction = struct.unpack_from('<I', after_obj, 0x24)[0]
        struct.pack_into('<I', obj, 0x24, after_direction)
        assert after_obj == bytes(obj)
        assert bytes(u.mem_read(self.heap + 0x1000, 64)) == struct.pack('<16I', *input_steps)
        assert bytes(u.mem_read(self.heap + 0x1800, 64)) == struct.pack('<16I', *output_steps)
        assert bytes(u.mem_read(self.heap + 0x2000, 4)) == struct.pack('<I', override_count)
        after = []
        for key, count in [('counts', 2), ('input', 35), ('output', 35)]:
            after.extend(struct.unpack('<' + str(count) + 'I', u.mem_read(self.data[key]['address'], count * 4)))
        return u.reg_read(arm.UC_ARM_REG_R0) if op == 'G' else 0, after_direction, after


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repository', type=Path)
    args = parser.parse_args()
    dest = args.repository / 'uc-library/validation/panel-meter-control'
    dest.mkdir(parents=True, exist_ok=False)
    rng = random.Random(0x4d455445)
    steps = list(map(bits, [-200, -144, -120, -90, -60, -20, -6, 0, 6, 20, 80, 100, -144, -20, 0, 6]))
    cases = []

    def state():
        tables = []
        for _ in range(2):
            tables.extend([rng.randrange(17)] + [bits(rng.uniform(-200, 20)) for _ in range(34)])
        return [rng.getrandbits(32), rng.getrandbits(32)] + tables

    def case(op, a, b=0, override=0, value=0):
        before = state()
        rotation = rng.randrange(16)
        cases.append((op, before, a & 0xffffffff, b & 0xffffffff, rng.getrandbits(32), override, value & 0xffffffff,
                      steps[rotation:] + steps[:rotation], list(reversed(steps))))

    for a in [-2147483648, -1, 0, 1, 2, 8, 15, 16]:
        for b in [-2147483648, -1, 0, 1, 2, 8, 15, 16]:
            for _ in range(8):
                case('S', a, b)
    floats = [0, 0x80000000, bits(-144), bits(0.1), bits(1), bits(20), 0x7f800000, 0xff800000,
              0x7fc00123, 0xffc00123, 1, 0x80000001, 0x7f7fffff, 0xff7fffff]
    for a in floats:
        for b in floats:
            case('R', a, b)
    directions = list(range(-256, 257)) + [-2147483648, -2147483647, -65536, 65536, 2147483646, 2147483647]
    directions.extend(rng.randrange(-2147483648, 2147483648) for _ in range(1024))
    for direction in directions:
        case('D', direction)
        for alternate in (0, 1):
            case('G', direction, alternate, override=1, value=rng.getrandbits(32))
            if direction >= 0:
                case('G', direction, alternate)
    counts = {key: 0 for key in NAMES}
    originals = {}
    with (dest / 'arm-vectors.txt').open('w') as output:
        for role_index, role in enumerate(('client', 'server')):
            original = MeterOriginal(args.repository, role, dest)
            for op, before, a, b, direction, override, value, input_steps, output_steps in cases:
                result, result_direction, after = original.meter_call(op, before, a, b, direction, override, value, input_steps, output_steps)
                output.write(' '.join(map(str, [op, role_index, a, b, direction, override, value, result, result_direction,
                                               *before, *input_steps, *output_steps, *after])) + '\n')
                counts[op] += 1
            executed = [s for s in original.all_symbols if s['kind'] == 'STT_FUNC' and isinstance(s['section'], int)
                        and any(s['address'] <= block < s['address'] + s['size'] for block in original.blocks)]
            originals[role] = dict(sha256=original.manifest['sha256'], source=original.manifest['path'], functions=list(original.symbols.values()),
                                   data_symbols=original.data, actual_dbtable_functions=list(original.db_symbols.values()),
                                   executed_function_ranges=executed, basic_blocks=sorted(original.blocks), modeled_powf_calls=original.pow_calls)
            print(json.dumps(dict(role=role, cases=len(cases), modeled_powf_calls=original.pow_calls)), flush=True)
    report = dict(originals=originals, counts=counts, total_cases=sum(counts.values()), vectors_sha256=sha(dest / 'arm-vectors.txt'),
                  domain='setMeterSteps counts <=0 or1..16, valid nonoverlapping tables; full two-global-DbTable state and count writes; setDbRange signedzero/finite/Inf/qNaN/subnormal/extreme bits; signed direction guard incl all8bit and int32 boundaries/random; bool0/1; override dereferenced firstint allbits. Null override fallback requires nonnegative direction; negative fallback indexing is excluded. Explicit preconfigured states, not historical process startup.',
                  dependency_model='Real original MeterControl, DbTable and compiler float instructions run. Only imported powf uses real native Linux libm contract as in sealed DbTable proof; historical ARM libm behavior remains unverified. No Core/hardware calls.',
                  original_full_verification=False, original_arm_abi_compatible=False, hardware_verified=False)
    (dest / 'arm-oracle.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(total_cases=report['total_cases'], counts=counts)), flush=True)


if __name__ == '__main__':
    main()
