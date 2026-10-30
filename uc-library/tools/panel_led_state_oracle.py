#!/usr/bin/env python3
"""Execute LED state methods; intercept two explicitly unverified app callbacks."""
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

BASE = '_ZN8Presonus5Panel10LEDControl'
NAMES = {'M': BASE + '13setmatchvalueEi', 'B': BASE + '12setBlinkModeENS1_9BlinkModeE',
         'C': BASE + '8setColorE12RGBLedColors', 'F': BASE + '10setFullOffEv', 'V': BASE + '14broadcastValueEi'}
CALLBACKS = {'T': BASE + '8transmitEv', 'P': BASE + '12paramChangedEPN4Core8Portable9ParameterEi'}
OFFSETS = (4, 0x1c, 0x20, 0x2c, 0x30)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
        self.callbacks = {kind: next(s for s in self.all_symbols if s['mangled'] == name) for kind, name in CALLBACKS.items()}
        self.vtable = next(s for s in self.all_symbols if s['mangled'] == '_ZTVN8Presonus5Panel10LEDControlE')
        assert len(self.symbols) == 5
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
            for symbol in [*self.symbols.values(), *self.callbacks.values(), self.vtable]:
                section = elf.get_section(symbol['section'])
                offset = int(section['sh_offset']) + symbol['address'] - int(section['sh_addr'])
                assert offset == symbol['file_offset']
                assert raw[offset:offset + symbol['size']] == (directory / symbol['export_path']).read_bytes()
        for address, size in [(self.heap, 0x10000), (self.stack, 0x10000), (self.stop, 4096)]:
            self.u.mem_map(address, size)
        self.blocks = set()
        self.u.hook_add(unicorn.UC_HOOK_BLOCK, lambda u, a, s, d: self.blocks.add(a))
        table = struct.unpack('<' + 'I' * (self.vtable['size'] // 4), (directory / self.vtable['export_path']).read_bytes())
        expected_slots = {4: self.callbacks['P'], 0x20: self.symbols[NAMES['V']], 0x24: self.callbacks['T']}
        for offset, target in expected_slots.items():
            assert table[2 + offset // 4] == target['address']
        self.slots = {hex(offset): target['mangled'] for offset, target in expected_slots.items()}
        self.events = []
        self.current_parameter = 0

        def callback(kind):
            def intercept(u, address, size, data):
                assert u.reg_read(arm.UC_ARM_REG_R0) == self.heap + 64
                matches = int(u.reg_read(arm.UC_ARM_REG_R1) == self.current_parameter) if kind == 'P' else 0
                message = u.reg_read(arm.UC_ARM_REG_R2) if kind == 'P' else 0
                self.events.append((kind, matches, message, self.state()))
                lr = u.reg_read(arm.UC_ARM_REG_LR)
                for reg, value in [(arm.UC_ARM_REG_R0, 0x13579bdf), (arm.UC_ARM_REG_R1, 0x2468ace0),
                                   (arm.UC_ARM_REG_R2, 0x11223344), (arm.UC_ARM_REG_R3, 0x55667788), (arm.UC_ARM_REG_R12, 0xabcdef01)]:
                    u.reg_write(reg, value)
                u.reg_write(arm.UC_ARM_REG_PC, lr)
            return intercept

        for kind, symbol in self.callbacks.items():
            self.u.hook_add(unicorn.UC_HOOK_CODE, callback(kind), begin=symbol['address'], end=symbol['address'])
        cs = Cs(CS_ARCH_ARM, CS_MODE_ARM)
        instructions = {name: [dict(address=i.address, mnemonic=i.mnemonic, operands=i.op_str)
                               for i in cs.disasm((directory / symbol['export_path']).read_bytes(), symbol['address'])]
                        for name, symbol in self.symbols.items()}
        (output / (role + '-instructions.json')).write_text(json.dumps(instructions, indent=2) + '\n')

    def state(self):
        u, obj = self.u, self.heap + 64
        return [struct.unpack('<I', u.mem_read(obj + off, 4))[0] if off != 0x20 else u.mem_read(obj + off, 1)[0]
                for off in OFFSETS]

    def call(self, op, argument, present, state):
        u = self.u
        for i in range(13):
            u.reg_write(getattr(arm, f'UC_ARM_REG_R{i}'), 0)
        u.reg_write(arm.UC_ARM_REG_CPSR, 0x10)
        u.reg_write(arm.UC_ARM_REG_SP, self.stack + 0xff00)
        u.reg_write(arm.UC_ARM_REG_LR, self.stop)
        self.current_parameter = self.heap + 0x5000 if present else 0
        before = bytearray(b'\xa5' * 0x80)
        struct.pack_into('<I', before, 0, self.vtable['address'] + 8)
        struct.pack_into('<I', before, 8, self.current_parameter)
        for offset, value in zip(OFFSETS, state):
            if offset == 0x20:
                before[offset] = value
            else:
                struct.pack_into('<I', before, offset, value)
        u.mem_write(self.heap, b'\x5a' * 256)
        u.mem_write(self.heap + 64, bytes(before))
        u.mem_write(self.heap + 0x5000, b'\xfe\xed\xfa\xce' * 4)
        self.events = []
        u.reg_write(arm.UC_ARM_REG_R0, self.heap + 64)
        u.reg_write(arm.UC_ARM_REG_R1, argument)
        u.emu_start(self.symbols[NAMES[op]]['address'], self.stop, count=10000)
        assert u.reg_read(arm.UC_ARM_REG_PC) == self.stop
        assert u.reg_read(arm.UC_ARM_REG_SP) == self.stack + 0xff00
        after = bytes(u.mem_read(self.heap + 64, 0x80))
        allowed = bytearray(before)
        for offset in OFFSETS:
            width = 1 if offset == 0x20 else 4
            allowed[offset:offset + width] = after[offset:offset + width]
        assert after == bytes(allowed), 'untracked object field changed'
        assert bytes(u.mem_read(self.heap, 64)) == b'\x5a' * 64
        assert bytes(u.mem_read(self.heap + 192, 64)) == b'\x5a' * 64
        assert bytes(u.mem_read(self.heap + 0x5000, 16)) == b'\xfe\xed\xfa\xce' * 4
        return self.state(), list(self.events)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repository', type=Path)
    args = parser.parse_args()
    dest = args.repository / 'uc-library/validation/panel-led-state'
    dest.mkdir(parents=True, exist_ok=False)
    rng = random.Random(0x4c454453)
    cases = []

    def state():
        return [rng.getrandbits(32), rng.getrandbits(32), rng.randrange(256), rng.getrandbits(32), rng.getrandbits(32)]

    values = list(range(-128, 128)) + [-2147483648, -2147483647, 2147483646, 2147483647]
    values.extend(rng.randrange(-2147483648, 2147483648) for _ in range(256))
    for signed in values:
        value = signed & 0xffffffff
        for same in (False, True):
            before = state()
            before[3] = value if same else value ^ 0xffffffff
            cases.append(('M', value, rng.randrange(2), before))
            for present in (0, 1):
                before = state()
                before[0] = value if same else value ^ 0xffffffff
                cases.append(('V', value, present, before))
                for cached in (2, 3, 0x7fffffff):
                    before = state()
                    before[0] = cached
                    before[4] = value if same else value ^ 0xffffffff
                    cases.append(('B', value, present, before))
                for dirty in (0, 1, 255):
                    before = state()
                    before[1] = value if same else value ^ 0xffffffff
                    before[2] = dirty
                    cases.append(('C', value, present, before))
    for cached in [-2147483648, -1, 0, 1, 2, 3, 4, 2147483647, *[rng.getrandbits(32) for _ in range(128)]]:
        for present in (0, 1):
            before = state()
            before[0] = cached & 0xffffffff
            cases.append(('F', 0, present, before))
    counts = {key: 0 for key in NAMES}
    originals = {}
    with (dest / 'arm-vectors.txt').open('w') as output:
        for role_index, role in enumerate(('client', 'server')):
            original = Original(args.repository, role, dest)
            event_count = 0
            for op, argument, present, before in cases:
                after, events = original.call(op, argument, present, before)
                flat_events = [value for kind, matches, message, event_state in events for value in (kind, matches, message, *event_state)]
                output.write(' '.join(map(str, [op, role_index, argument, present, *before, *after, len(events), *flat_events])) + '\n')
                counts[op] += 1
                event_count += len(events)
            bodies = [s for s in original.symbols.values() if any(s['address'] <= block < s['address'] + s['size'] for block in original.blocks)]
            boundaries = {s['address'] for s in original.callbacks.values()}
            assert all(block in boundaries or any(s['address'] <= block < s['address'] + s['size'] for s in bodies) for block in original.blocks)
            originals[role] = dict(sha256=original.manifest['sha256'], source=original.manifest['path'], functions=list(original.symbols.values()),
                                   actual_vtable_symbol=original.vtable, verified_vtable_slots=original.slots, intercepted_callbacks=original.callbacks,
                                   executed_selected_body_ranges=bodies, basic_blocks=sorted(original.blocks), callback_dispatches=event_count)
            print(json.dumps(dict(role=role, cases=len(cases), intercepted_dispatches=event_count)), flush=True)
    report = dict(originals=originals, total_cases=sum(counts.values()), counts=counts, vectors_sha256=sha(dest / 'arm-vectors.txt'),
                  domain='Explicit preconfigured app state; all signed8 values plus int32 bounds/random for match/color/blink/cache; equal/changed branches; null/non-null opaque parameter; dirty byte0/1/255; full-off cache suppression; actual selected broadcast body; actual original vtable dispatch to record-only transmit/paramChanged boundaries. No callback side effects/reentrancy/concurrency/Core object dereferences, timer/device or constructor/lifecycle behavior.',
                  dependency_model='Two original app virtual entries are intercepted: LEDControl::transmit() and LEDControl::paramChanged(Core::Portable::Parameter*,int). Defined arguments and complete tracked state at dispatch are recorded; bodies do not run, object memory is preserved, caller-saved registers are poisoned. Actual selected LEDControl::broadcastValue body runs. No Core implementation/API body is modeled or reconstructed.',
                  downstream_callback_behavior_verified=False, original_full_verification=False, original_arm_abi_compatible=False, hardware_verified=False)
    (dest / 'arm-oracle.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(total_cases=report['total_cases'], counts=counts)), flush=True)


if __name__ == '__main__':
    main()
