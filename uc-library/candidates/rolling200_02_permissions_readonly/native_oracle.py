#!/usr/bin/env python3
"""Execute exact ARM getter bodies; libc intercepts model only named boundaries.
No recovered C++ is imported or executed by this fixture producer.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import struct
import unicorn
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_CPSR
from elftools.elf.elffile import ELFFile

ELF_PATH = Path('rootfs/RML16AI_Rack_13731/home/root/mixer')
ELF_HASH = '9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
PACKETS = Path('temp/recovery-work/rolling200-02/implementation-plan01/packets-current-permissions-readonly04-01/packets')
PREFIX = 'rolling200_02_permissions_readonly_'
SELF, CLIENT, OUTPUT, STACK, STOP = 0x1000000, 0x1001000, 0x1002000, 0x1100000, 0x1200000
STARTS = {'app': 0x50f14, 'info': 0x51eec, 'selectedApp': 0x50fa8, 'device': 0x515bc}
ENDS = {'app': 0x50f9c, 'info': 0x51fa8, 'selectedApp': 0x50fd0, 'device': 0x51650}
BOUNDARIES = {0xad18: 'strstr', 0xae68: 'memcpy', 0xae98: 'strlen', 0xae08: 'strncat'}

def sha(data):
    return hashlib.sha256(data).hexdigest()

def cbuffer(text, salt=0):
    raw = bytearray(((i * 37 + salt) % 254 + 1) for i in range(64))
    raw[:len(text)] = text
    raw[len(text)] = 0
    return bytes(raw)

def cases():
    empty = cbuffer(b'')
    app_texts = [b'', b'unknown', b'QMIX', b'UCAPP', b'UCREMOTEAPP', b'qmixucappucremoteapp', b'ucappqmix', b'ucremoteappucapp']
    for literal in (b'qmix', b'ucapp', b'ucremoteapp'):
        app_texts.extend(b'x' * offset + literal for offset in range(64 - len(literal)))
    for text in app_texts:
        for op in ('app', 'selectedApp'):
            yield op, True, cbuffer(text, 13), empty, empty
    yield 'selectedApp', False, empty, empty, empty
    device_texts = [b'', b'unknown', b'iphone', b'IPod', b'IPAD', b'iPadiPodiPhone', b'iPodiPad', b'iPhoneiPod']
    for literal in (b'iPhone', b'iPod', b'iPad'):
        device_texts.extend(b'x' * offset + literal for offset in range(64 - len(literal)))
    for text in device_texts:
        yield 'device', True, empty, cbuffer(text, 19), empty
    yield 'device', False, empty, empty, empty
    # Every display length, clipping edges, output-boundary lengths, patterned tails.
    for length in range(64):
        for device_length in (0, 1, 15, 16, 44, 45, 46, 47, 60, 63):
            yield 'info', True, empty, cbuffer(b'D' * device_length, 29), cbuffer(b'N' * length, 31 + length)
    for text in (b'A\x80\xffZ', b' x:y '):
        yield 'info', True, empty, cbuffer(text, 73), cbuffer(text, 81)

class Oracle:
    def __init__(self):
        self.raw = ELF_PATH.read_bytes()
        assert sha(self.raw) == ELF_HASH
        self.elf = ELFFile(io.BytesIO(self.raw))
        self.ranges = []
        symbols = {s.name: s for s in self.elf.get_section_by_name('.symtab').iter_symbols()}
        for i in range(1, 5):
            packet = PACKETS / (PREFIX + f'{i:02}')
            task = json.loads((packet / 'request.json').read_text())
            original = task['targets'][0]
            symbol = symbols[original['mangled']]
            assert symbol['st_value'] == original['address'] and symbol['st_size'] == original['size']
            section = self.elf.get_section(symbol['st_shndx'])
            assert section.name == '.text' and section['sh_type'] != 'SHT_NOBITS'
            offset = section['sh_offset'] + symbol['st_value'] - section['sh_addr']
            body = self.raw[offset:offset + symbol['st_size']]
            context = (packet / 'ELF_CONTEXT.md').read_text()
            assert sha(body) in context
            self.ranges.append(dict(mangled=symbol.name, address=symbol['st_value'], size=symbol['st_size'], section=section.name, section_index=symbol['st_shndx'], file_offset=offset, sha256=sha(body)))
        self.uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        pages = set()
        for segment in self.elf.iter_segments():
            if segment['p_type'] != 'PT_LOAD':
                continue
            lo = segment['p_vaddr'] & ~4095
            hi = (segment['p_vaddr'] + segment['p_memsz'] + 4095) & ~4095
            for address in range(lo, hi, 4096):
                if address not in pages:
                    self.uc.mem_map(address, 4096)
                    pages.add(address)
            self.uc.mem_write(segment['p_vaddr'], segment.data())
        self.uc.mem_map(SELF, 0x4000)
        self.uc.mem_map(STACK, 0x10000)
        self.uc.mem_map(STOP, 4096)
        self.uc.hook_add(UC_HOOK_CODE, self.code)
        self.uc.hook_add(UC_HOOK_MEM_WRITE, self.write_hook)

    def string(self, address):
        out = bytearray()
        for i in range(256):
            value = self.uc.mem_read(address + i, 1)[0]
            if not value:
                return bytes(out)
            out.append(value)
        raise AssertionError('unterminated boundary string')

    def write_hook(self, uc, access, address, size, value, data):
        assert STACK <= address and address + size <= STACK + 0x10000 or OUTPUT <= address and address + size <= OUTPUT + 64, ('unexpected native write', address, size)
        self.writes.append(dict(address=address, size=size, value=value))

    def boundary_write(self, address, data):
        assert OUTPUT <= address and address + len(data) <= OUTPUT + 64
        self.writes.append(dict(address=address, bytes=data.hex(), boundary=True))
        self.uc.mem_write(address, data)

    def code(self, uc, address, size, data):
        if address == STOP:
            self.finished = True
            uc.emu_stop()
            return
        if address in BOUNDARIES:
            name = BOUNDARIES[address]
            assert name in self.allowed_calls
            r0, r1, r2 = (uc.reg_read(x) for x in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2))
            call = dict(name=name, args=[r0, r1, r2])
            if name == 'strstr':
                hay, needle = self.string(r0), self.string(r1)
                offset = hay.find(needle)
                result = 0 if offset < 0 else r0 + offset
                call.update(haystack=hay.hex(), needle=needle.hex())
            elif name == 'strlen':
                text = self.string(r0)
                result = len(text)
                call['input'] = text.hex()
            elif name == 'memcpy':
                copied = bytes(uc.mem_read(r1, r2))
                self.boundary_write(r0, copied)
                result = r0
                call['input'] = copied.hex()
            elif name == 'strncat':
                target, text = self.string(r0), self.string(r1)
                copied = text[:r2] + b'\0'
                self.boundary_write(r0 + len(target), copied)
                result = r0
                call.update(target=target.hex(), input=text.hex(), copied=copied.hex())
            call['result'] = result
            self.calls.append(call)
            uc.reg_write(UC_ARM_REG_R0, result)
            uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))
            return
        assert any(STARTS[k] <= address < ENDS[k] and address % 4 == 0 for k in self.allowed_code), ('application PC outside exact allowlist', hex(address))
        self.pcs.append(address)

    def run(self, op, selected, app, device, display):
        uc = self.uc
        self.calls, self.writes, self.pcs = [], [], []
        self.finished = False
        self.allowed_code = {op, 'app'} if op == 'selectedApp' else {op}
        self.allowed_calls = {'memcpy', 'strlen', 'strncat'} if op == 'info' else {'strstr'}
        uc.mem_write(SELF, b'\xa5' * 0x3000)
        uc.mem_write(STACK, b'\xcc' * 0x10000)
        for offset, value in ((0x58, app), (0x98, device), (0x118, display)):
            uc.mem_write(CLIENT + offset, value)
        uc.mem_write(SELF + 0xf8, struct.pack('<I', CLIENT if selected else 0))
        before = bytes(uc.mem_read(SELF, 0x2000))
        guards = bytes(uc.mem_read(OUTPUT - 16, 16)), bytes(uc.mem_read(OUTPUT + 64, 16))
        for register in range(UC_ARM_REG_R0, UC_ARM_REG_R0 + 13):
            uc.reg_write(register, 0)
        uc.reg_write(UC_ARM_REG_CPSR, 0x10)
        uc.reg_write(UC_ARM_REG_SP, STACK + 0xff00)
        uc.reg_write(UC_ARM_REG_LR, STOP)
        uc.reg_write(UC_ARM_REG_R0, OUTPUT if op == 'info' else SELF)
        uc.reg_write(UC_ARM_REG_R1, SELF if op == 'info' else CLIENT)
        uc.reg_write(UC_ARM_REG_R2, CLIENT if op == 'info' else 0)
        uc.emu_start(STARTS[op], STOP + 4, count=1000)
        assert self.finished, 'instruction limit or missing return'
        assert bytes(uc.mem_read(SELF, 0x2000)) == before
        assert (bytes(uc.mem_read(OUTPUT - 16, 16)), bytes(uc.mem_read(OUTPUT + 64, 16))) == guards
        if op == 'info':
            assert uc.reg_read(UC_ARM_REG_R0) == OUTPUT
            result = bytes(uc.mem_read(OUTPUT, 64)).hex()
        else:
            result = str(uc.reg_read(UC_ARM_REG_R0))
            assert all(STACK <= w['address'] < STACK + 0x10000 for w in self.writes)
        return result, dict(pcs=self.pcs, calls=self.calls, writes=self.writes, input_unchanged=True, guards_unchanged=True)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    oracle = Oracle()
    counts = {}
    rows = []
    with (out / 'native-traces.jsonl').open('w') as traces:
        for index, (op, selected, app, device, display) in enumerate(cases()):
            result, trace = oracle.run(op, selected, app, device, display)
            rows.append(' '.join((op, str(int(selected)), app.hex(), device.hex(), display.hex(), result)))
            traces.write(json.dumps(dict(case=index, op=op, selected=selected, result=result, **trace)) + '\n')
            counts[op] = counts.get(op, 0) + 1
    (out / 'native-fixture.txt').write_text('\n'.join(rows) + '\n')
    report = dict(elf_path=str(ELF_PATH), elf_sha256=ELF_HASH, ranges=oracle.ranges, counts=counts, unicorn_version=unicorn.__version__, producer_sha256=sha(Path(__file__).read_bytes()), fixture_sha256=sha((out / 'native-fixture.txt').read_bytes()), trace_sha256=sha((out / 'native-traces.jsonl').read_bytes()), mode='Original ARM instructions with named libc boundary models; no original libc/Core instructions executed', application_pc_allowlist={k:[STARTS[k],ENDS[k]] for k in STARTS}, memory_assumptions='Private synthetic memory; NUL-terminated 64-byte app/device/display ranges; borrowed selected pointer at native +0xf8; no original construction or ownership.', write_scope='Only stack and 64-byte info output; input and guards checked after every case')
    (out / 'native-proof.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(counts))

if __name__ == '__main__':
    main()
