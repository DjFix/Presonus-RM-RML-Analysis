"""Execute the exact immutable lookup or read-only DSP status target."""
import hashlib
import io
import json
from pathlib import Path
import struct
import re

from elftools.elf.elffile import ELFFile
import unicorn as uc
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_SP

task = Path(__file__).parent.name
base = Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/reconstruction10x10-20261121/packeting/post39-tail-batch02')
elf = base / 'snapshot/rootfs/RML16AI_Rack_13731/home/root/mixer'
packet = base / 'packets' / task
source = (packet / 'ELF_CONTEXT.md').read_text()
sha, symbol, address, size, digest = re.search(
    r'ELF `([^\x60]+)`.*?original `([^\x60]+)`; address `(0x\w+)`; size (\d+); section \.text; SHA256 `([^\x60]+)`', source).groups()
address, size = int(address, 16), int(size)
image = elf.read_bytes()
assert hashlib.sha256(image).hexdigest() == sha
binary = ELFFile(io.BytesIO(image))
text = binary.get_section_by_name('.text')
offset = address - text['sh_addr'] + text['sh_offset']
assert text['sh_addr'] <= address and offset + size <= text['sh_offset'] + text['sh_size']
assert hashlib.sha256(image[offset:offset+size]).hexdigest() == digest
STOP = 0x600000
STACK = 0x610000
SHARED = 0x49db64

def observe(args):
    machine = uc.Uc(uc.UC_ARCH_ARM, uc.UC_MODE_ARM)
    machine.mem_map(0x8000, 0x4b0000)
    for seg in binary.iter_segments(type='PT_LOAD'):
        machine.mem_write(seg['p_vaddr'], seg.data())
    machine.mem_map(STOP, 0x30000)
    machine.reg_write(UC_ARM_REG_SP, STACK)
    machine.reg_write(UC_ARM_REG_LR, STOP)
    machine.reg_write(UC_ARM_REG_R0, (args[0] if task.endswith('09') else 0x608000) & 0xffffffff)
    reads, writes, executed = [], [], []
    if task.endswith('10'):
        link, state = args
        machine.mem_write(SHARED, struct.pack('<I', link))
        if link:
            machine.mem_write(link+0x3dec, struct.pack('<I', state))
        assert struct.unpack('<I', machine.mem_read(0x3686b4, 4))[0] == address
        machine.hook_add(uc.UC_HOOK_MEM_READ, lambda _, _access, addr, _size, _value, _data:
                         reads.append(addr) if addr < STOP or addr >= STACK + 0x1000 else None)
        machine.hook_add(uc.UC_HOOK_MEM_WRITE, lambda _, _access, addr, _size, _value, _data:
                         writes.append(addr) if not STACK - 0x1000 <= addr < STACK else None)
        machine.hook_add(uc.UC_HOOK_CODE, lambda _, addr, _size, _data: executed.append(addr))
    machine.emu_start(address, STOP, count=1000)
    assert machine.reg_read(UC_ARM_REG_PC) == STOP
    value = machine.reg_read(UC_ARM_REG_R0)
    if task.endswith('09'):
        rodata = binary.get_section_by_name('.rodata')
        assert rodata['sh_addr'] <= value < rodata['sh_addr'] + rodata['sh_size']
        length = min(256, rodata['sh_addr'] + rodata['sh_size'] - value)
        return machine.mem_read(value, length).split(b'\x00', 1)[0].decode()
    assert executed[5] == 0x104d8c
    assert not writes
    return dict(value=value, reads=[addr for addr in reads if addr not in {0x104db4, 0x104db8}], writes=writes)

def main():
    if task.endswith('09'):
        args = [[value] for value in [-2147483648, -1, 0, 1999, *range(2000,2010), 2010, 2147483647]]
        binding = {}
    else:
        args = [[0, 0], [0x620000, 0], [0x621000, 3],
                [0x620000, 0xffffffff], [0x621000, 0x80000000], [0x620000, 0x12345678]]
        provider = next(s for s in binary.get_section_by_name('.symtab').iter_symbols()
                        if s.name == 'getDSPState')
        assert provider['st_value'] == 0x104d8c and provider['st_size'] == 48
        provider_offset = provider['st_value'] - text['sh_addr'] + text['sh_offset']
        binding = dict(provider_address=provider['st_value'], provider_size=provider['st_size'],
                       provider_offset=provider_offset, vtable_slot=0x3686b4,
                       provider_sha256=hashlib.sha256(image[provider_offset:provider_offset+48]).hexdigest())
    print(json.dumps(dict(elf_sha256=sha, elf=str(elf), mangled=symbol,
        address=address, section='.text', file_offset=offset, range_sha256=digest,
        size=size, unicorn=uc.__version__, binding=binding,
        cases=[dict(arguments=args, expected=observe(args)) for args in args]), indent=2))

if __name__ == '__main__':
    main()
