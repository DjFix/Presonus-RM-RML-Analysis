"""Execute both original ARM access predicates on isolated receiver storage."""
import hashlib
from io import BytesIO
import json
from pathlib import Path
import struct

from elftools.elf.elffile import ELFFile
import unicorn
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_SP

TASK = Path(__file__).parent.name
PACKET = Path('temp/recovery-work/sqlite-issued/packet') / TASK / 'CONTEXT.json'
ROOT = Path('/home/rs/projects/opencs/ai-line-analysis')
INPUTS = (0, 1, 0x80000000, 0xffffffff, 0)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def observe():
    output = []
    for target in json.loads(PACKET.read_text())['task']['originals']:
        leaf = ('CS18_v13840/home/root/surface' if target['role'] == 'client'
                else 'RML16AI_Rack_13731/home/root/mixer')
        elf_path = ROOT / 'rootfs' / leaf
        image = elf_path.read_bytes()
        assert sha(image) == target['elf']
        elf = ELFFile(BytesIO(image))
        section = elf.get_section(target['section'])
        address, size = target['address'], target['size']
        relative = address - section['sh_addr']
        assert 0 <= relative <= section['sh_size'] - size
        offset = section['sh_offset'] + relative
        body = image[offset:offset + size]
        assert sha(body) == target['range_sha256']
        assert any(sym.name == target['mangled'] and sym['st_value'] == address
                   and sym['st_size'] == size and sym['st_shndx'] == target['section']
                   for sym in elf.get_section_by_name('.symtab').get_symbol_by_name(target['mangled']))
        cases = []
        for observation in INPUTS:
            data, stack, sentinel = 0x20000000, 0x20002000, 0x20003000
            model = unicorn.Uc(unicorn.UC_ARCH_ARM, unicorn.UC_MODE_ARM)
            model.mem_map(address & ~0xfff, 0x2000)
            model.mem_write(address, body)
            model.mem_map(data, 0x4000)
            model.mem_write(data + 0x1d8, struct.pack('<I', observation))
            model.reg_write(UC_ARM_REG_R0, data)
            model.reg_write(UC_ARM_REG_SP, stack)
            model.reg_write(UC_ARM_REG_LR, sentinel)
            writes, instructions = [], []

            def write(_, _access, where, width, value, _context):
                if not data + 0x1000 <= where <= stack - width:
                    writes.append([where, width, value])

            def code(_, pc, width, _context):
                assert address <= pc <= address + size - width
                instructions.append(pc)

            model.hook_add(unicorn.UC_HOOK_MEM_WRITE, write)
            model.hook_add(unicorn.UC_HOOK_CODE, code)
            model.emu_start(address, sentinel, count=32)
            assert model.reg_read(UC_ARM_REG_PC) == sentinel
            assert model.reg_read(UC_ARM_REG_SP) == stack
            assert not writes
            cases.append({'observation': observation, 'r0': model.reg_read(UC_ARM_REG_R0),
                          'external_writes': writes, 'instructions': instructions})
        original = {key: target[key] for key in
                    ('firmware', 'role', 'mangled', 'address', 'size', 'section', 'range_sha256')}
        original.update(elf_sha256=target['elf'], file_offset=offset)
        output.append({'original': original, 'elf_path': str(elf_path),
                       'section_name': section.name, 'cases': cases})
    return {'unicorn_version': unicorn.__version__, 'targets': output}
