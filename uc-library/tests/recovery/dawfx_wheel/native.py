"""Execute the exact original ARM wheel body; stop at the existing callee boundary."""
import argparse
import hashlib
import json
import struct
from pathlib import Path
import unicorn
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_SP, UC_ARM_REG_LR
from elftools.elf.elffile import ELFFile

ELF_HASH = '304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
SYMBOL = '_ZN8Presonus7Surface18DawFxPageComponent12onWheelInputERKN4Core8Portable10WheelEventE'

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--elf', required=True)
    p.add_argument('--out', required=True)
    a = p.parse_args()
    blob = Path(a.elf).read_bytes()
    assert hashlib.sha256(blob).hexdigest() == ELF_HASH
    with open(a.elf, 'rb') as f:
        elf = ELFFile(f)
        matches = [s for sec in elf.iter_sections() if sec['sh_type'] == 'SHT_SYMTAB' for s in sec.iter_symbols() if s.name == SYMBOL]
        assert len(matches) == 1
        s = matches[0]
        sec = elf.get_section(s['st_shndx'])
        offset = sec['sh_offset'] + s['st_value'] - sec['sh_addr']
        assert (s['st_value'], s['st_size'], sec.name, offset) == (0xb7adc, 24, '.text', 0xafadc)
    body = blob[offset:offset+24]
    assert hashlib.sha256(body).hexdigest() == '15e746bd6e512f092d376f03450f140215d377d9762198bc40db8376021cb7c5'
    cases = []
    for delta in [-2147483648, -2147483647, -100000, -11, -5, -1, 0, 1, 5, 11, 100000, 2147483646, 2147483647]:
        for axis in [0, 1]:
            u = Uc(UC_ARCH_ARM, UC_MODE_ARM)
            u.mem_map(0xb7000, 0x1000)
            u.mem_write(0xb7adc, body)
            u.mem_map(0x200000, 0x3000)
            event = struct.pack('<iI', delta, axis)
            obj = bytes(range(128))
            u.mem_write(0x200000, obj)
            u.mem_write(0x201000, event)
            u.reg_write(UC_ARM_REG_R0, 0x200000)
            u.reg_write(UC_ARM_REG_R1, 0x201000)
            u.reg_write(UC_ARM_REG_SP, 0x202ff0)
            u.reg_write(UC_ARM_REG_LR, 0x12345678)
            calls = []
            writes = []
            def memory_write(uc, access, address, size, value, data):
                writes.append({"address": address, "size": size, "value": value})
            u.hook_add(UC_HOOK_MEM_WRITE, memory_write)
            def hook(uc, address, size, data):
                if address == 0xb7ab0:
                    calls.append({'this': uc.reg_read(UC_ARM_REG_R0), 'delta': struct.unpack('<i', struct.pack('<I', uc.reg_read(UC_ARM_REG_R1)))[0], 'sp': uc.reg_read(UC_ARM_REG_SP), 'lr': uc.reg_read(UC_ARM_REG_LR)})
                    uc.emu_stop()
            u.hook_add(UC_HOOK_CODE, hook)
            u.emu_start(0xb7adc, 0xb7b00, count=20)
            assert calls == [{'this': 0x200000, 'delta': delta, 'sp': 0x202ff0, 'lr': 0x12345678}]
            assert bytes(u.mem_read(0x200000, 128)) == obj
            assert bytes(u.mem_read(0x201000, 8)) == event
            cases.append({'delta': delta, 'axis': axis, 'calls': calls, 'object_unchanged': True, 'event_unchanged': True, 'memory_writes': writes})
    out = {'elf_sha256': ELF_HASH, 'mangled': SYMBOL, 'address': 0xb7adc, 'size': 24, 'section': '.text', 'file_offset': offset, 'range_sha256': hashlib.sha256(body).hexdigest(), 'producer_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'unicorn_version': unicorn.__version__, 'cases': cases, 'domain': 'Original wrapper only; callee is an observed external-call boundary, not an emulated provider.'}
    Path(a.out).write_text(json.dumps(out, indent=2)+'\n')
    print(f'ARM original: {len(cases)} cases passed')

if __name__ == '__main__':
    main()
