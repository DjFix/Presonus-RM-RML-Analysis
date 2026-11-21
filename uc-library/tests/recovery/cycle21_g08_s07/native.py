"""Execute original target ranges against isolated CCL and panel call boundaries."""
import hashlib
import io
import json
from pathlib import Path
import re
import struct
import sys

from elftools.elf.elffile import ELFFile
from unicorn import UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, Uc
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_SP

task = Path(__file__).parent.name
root = Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/reconstruction10x10-20261121/packeting/post32-next-batch02')
elf = root / 'snapshot/rootfs/CS18_v13840/home/root/surface'
ospec = (root / 'packets' / task / 'ELF_CONTEXT.md').read_text()
sha, symbol, address, size, digest = re.search(
    r'ELF `([^\x60]+)`.*?original `([^\x60]+)`; address `(0x\w+)`; size (\d+); section \.text; SHA256 `([^\x60]+)`',
    ospec).groups()
address, size = int(address, 16), int(size)
original = elf.read_bytes()
assert hashlib.sha256(original).hexdigest() == sha
binary = ELFFile(io.BytesIO(original))
text = binary.get_section_by_name('.text')
offset = address - text['sh_addr'] + text['sh_offset']
assert text['sh_addr'] <= address and offset + size <= text['sh_offset'] + text['sh_size']
assert hashlib.sha256(original[offset:offset + size]).hexdigest() == digest

ROOT = 0x400100
SCREEN = 0x400800
PANEL = 0x401000
PARAM = 0x402000
TABLE = 0x420000
STACK = 0x43f000
STOP = 0x440000
GET = 0x440100
SET = 0x440200
TAGS = list(range(100, 112)) + list(range(115, 119)) + [903, 2002, 9000, 2, 31, 34, 38]
PARAMETERS = {tag: PARAM + index*16 for index, tag in enumerate(TAGS)}
PARAM_TAG = {address: tag for tag, address in PARAMETERS.items()}

def observe(registrar, argument, tags, base_value):
    cpu = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    cpu.mem_map(0x8000, 0x300000)
    for seg in binary.iter_segments(type='PT_LOAD'):
        cpu.mem_write(seg['p_vaddr'], seg.data())
    cpu.mem_map(0x400000, 0x50000)
    def put(addr, word):
        cpu.mem_write(addr, struct.pack('<I', word & 0xffffffff))
    def float_of(word):
        return struct.unpack('<f', struct.pack('<I', word))[0]
    def word_of(value):
        return struct.unpack('<I', struct.pack('<f', value))[0]
    def args():
        return tuple(cpu.reg_read(r) for r in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2))
    def ret(value=None):
        if value is not None:
            cpu.reg_write(UC_ARM_REG_R0, value & 0xffffffff)
        cpu.reg_write(UC_ARM_REG_PC, cpu.reg_read(UC_ARM_REG_LR))
    values = {tag: base_value for tag in TAGS}
    values.update(tags)
    observers = {tag: int(tag in [31, 34]) for tag in TAGS}
    counts = {tag: 0 for tag in TAGS}
    trace = []
    for p in PARAMETERS.values():
        put(p, TABLE)
    put(TABLE + 0x44, GET)
    put(TABLE + 0x58, SET)
    put(ROOT + 0x114, PANEL if registrar else 0)
    def call(_, pc, length, __):
        r0, r1, r2 = args()
        if pc == 0x11acf0:
            if r0 not in {ROOT, SCREEN}:
                raise ValueError(hex(r0))
            trace.append(f'tag:{r1}')
            ret(PARAMETERS[r1])
        elif pc == GET:
            tag = PARAM_TAG[r0]
            trace.append(f'get:{tag}')
            ret(word_of(values[tag]))
        elif pc == SET:
            tag = PARAM_TAG[r0]
            value = int(float_of(r1))
            trace.append(f'set:{tag}:{value}:{r2}')
            if values[tag] != value:
                counts[tag] += observers[tag]
            values[tag] = value
            ret()
        elif pc in {0x11f4f0, 0x11e2e0}:
            assert r1 == ROOT + 4
            tag = PARAM_TAG[r0]
            action = 'add' if pc == 0x11f4f0 else 'remove'
            trace.append(f'{action}:{tag}')
            observers[tag] = 1 if action == 'add' else 0
            ret()
        elif pc == 0xad000:
            assert r0 == ROOT
            ret(SCREEN)
        elif pc == 0xa61e0:
            assert r0 == PANEL
            trace.append(f'run:{r1}:{r2}')
            ret()
        elif pc == 0x1179d4:
            msg = cpu.mem_read(r0, 100).split(b'\0')[0]
            if b'paramChangedLaunchTestTouchscreen' in msg:
                choice = cpu.mem_read(r1, 6).split(b'\0')[0].decode()
                trace.append('debug:' + choice)
            elif b'activeTestCount' in msg:
                trace.append('debug:count')
            ret()
    cpu.hook_add(UC_HOOK_CODE, call)
    cpu.reg_write(UC_ARM_REG_SP, STACK)
    cpu.reg_write(UC_ARM_REG_LR, STOP)
    cpu.reg_write(UC_ARM_REG_R0, ROOT)
    cpu.reg_write(UC_ARM_REG_R1, PARAMETERS[9000] if task.endswith(('05','07')) else argument)
    cpu.emu_start(address, STOP, count=4000)
    assert cpu.reg_read(UC_ARM_REG_PC) == STOP
    return {'values': values, 'observers': observers,
            'touchscreen': cpu.mem_read(ROOT + 0x130, 1)[0],
            'observer_notifications': sum(counts.values()), 'trace': trace}

def main():
    task_number = int(task[-2:])
    states = [
        (1, 0, {}, 0.0),
        (1, 1, {}, 0.0),
        (1, 0, {100: 1, 101: 1, 103: -1, 104: .5, 105: 1, 108: 1, 109: 1, 110: 1, 115: 1, 116: -1, 117: .5, 118: 2}, 0.0),
        (1, 1, {100: .5, 101: 1, 102: .5, 103: -1, 105: .5, 111: 1, 2002: 1, 9000: 1}, 0.0),
        (1, 1, {9000: -.5, 109: .5, 110: 2, 105: 1, 108: 1}, 0.0),
    ]
    if task_number in (1, 2, 4, 5):
        states.extend([(0, 0, {}, 0.0), (0, 1, {}, 0.0)])
    cases = []
    for enabled, argument, tags, base in states:
        cases.append({'registrar': enabled, 'argument': argument, 'tags': tags,
                      'base_value': base, 'expected': observe(enabled, argument, tags, base)})
    print(json.dumps({'elf_sha256': sha, 'elf': str(elf), 'mangled': symbol,
        'address': address, 'section': '.text', 'file_offset': offset,
        'range_sha256': digest, 'size': size,
        'unicorn': __import__('unicorn').__version__, 'cases': cases}, indent=2))

if __name__ == '__main__':
    main()
