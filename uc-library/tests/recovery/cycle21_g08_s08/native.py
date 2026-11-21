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
elf = root / 'snapshot/rootfs/RML16AI_Rack_13731/home/root/mixer'
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

ROOT, HANDLER, STACK = 0x600000, 0x601000, 0x620000
TABLE, STOP, OUT1, OUT2 = 0x35a7b4, 0x630000, 0x625000, 0x625004

def observe(bound, first, second, alias):
    cpu = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    cpu.mem_map(0x8000, 0x4a0000)
    for seg in binary.iter_segments(type='PT_LOAD'):
        cpu.mem_write(seg['p_vaddr'], seg.data())
    cpu.mem_map(0x600000, 0x40000)
    def put(addr, word):
        cpu.mem_write(addr, struct.pack('<I', word & 0xffffffff))
    def get(addr):
        return struct.unpack('<I', cpu.mem_read(addr, 4))[0]
    def signed(addr):
        return struct.unpack('<i', cpu.mem_read(addr, 4))[0]
    assert get(TABLE) == 0x9e984
    put(ROOT + 0x380, HANDLER if bound else 0)
    put(HANDLER, TABLE - 4)
    put(OUT1, -3)
    put(OUT2, -9)
    called = []
    def call(_, pc, length, __):
        if pc == 0x9e984:
            assert cpu.reg_read(UC_ARM_REG_R0) == HANDLER
            payload = cpu.reg_read(UC_ARM_REG_R1)
            assert get(payload) == 0x73746174 and get(payload + 4) == 60
            assert signed(OUT1) == 0 and (alias or signed(OUT2) == 0)
            assert get(payload + 0x18) == 0 and get(payload + 0x20) == 0
            called.append((get(payload), get(payload + 4)))
            # Local metadata receiver contract. Host separately executes the
            # actual TCardHandler and TCard providers over preloaded card data.
            put(payload + 0x20, first)
            put(payload + 0x18, second)
            cpu.reg_write(UC_ARM_REG_PC, cpu.reg_read(UC_ARM_REG_LR))
    cpu.hook_add(UC_HOOK_CODE, call)
    cpu.reg_write(UC_ARM_REG_SP, STACK)
    cpu.reg_write(UC_ARM_REG_LR, STOP)
    cpu.reg_write(UC_ARM_REG_R0, ROOT)
    cpu.reg_write(UC_ARM_REG_R1, OUT1)
    cpu.reg_write(UC_ARM_REG_R2, OUT1 if alias else OUT2)
    cpu.emu_start(address, STOP, count=1000)
    assert cpu.reg_read(UC_ARM_REG_PC) == STOP
    assert len(called) == bound
    return [signed(OUT1), signed(OUT2), len(called)]

def main():
    cases = []
    for bound, first, second, alias in [
        (0, 1, 2, 0), (0, 1, 2, 1), (1, 0, 0, 0), (1, 17, 63, 0),
        (1, -123, -456, 0), (1, -2147483648, 2147483647, 0),
        (1, 2147483647, -2147483648, 1),
    ]:
        args = [bound, first, second, alias]
        cases.append(dict(arguments=args, expected=observe(*args)))
    print(json.dumps(dict(elf_sha256=sha, elf=str(elf), mangled=symbol,
        address=address, section='.text', file_offset=offset, range_sha256=digest,
        size=size, unicorn=__import__('unicorn').__version__, cases=cases), indent=2))

if __name__ == '__main__':
    main()
