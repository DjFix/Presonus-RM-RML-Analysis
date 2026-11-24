import hashlib
from pathlib import Path
import struct
from io import BytesIO

from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2
from unicorn.arm_const import UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC

ELF = Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling-c001-20261124/packeting/next59/snapshot/rootfs/CS18_v13840/home/root/surface')
ORIGINAL = {'elf_sha256': '304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0', 'firmware': 'CS18AI surface 13840', 'role': 'client', 'mangled': '_ZN8Presonus21IDAWComponentObserver15onObjectChangedENS0_19ObjectChangeMessageE', 'address': 501472, 'size': 16, 'section': 12, 'file_offset': 468704, 'range_sha256': '60cf0e8b51daf6a0ce5a5eea619d9a3e219bccf7fa26c553983e5baf3012cfad'}
INPUTS = [[0, 0, 0], [1, 1, 0], [2, 4294967295, 0]]
FIELD_OFFSET = None


def observe():
    image = ELF.read_bytes()
    if hashlib.sha256(image).hexdigest() != ORIGINAL['elf_sha256']:
        raise ValueError('Native ELF digest changed')
    elffile = ELFFile(BytesIO(image))
    section = elffile.get_section(ORIGINAL['section'])
    address = ORIGINAL['address']
    size = ORIGINAL['size']
    relative = address - section['sh_addr']
    offset = section['sh_offset'] + relative
    if (not 0 <= relative <= section['sh_size'] - size
            or offset != ORIGINAL['file_offset']):
        raise ValueError('Native target outside verified section range')
    body = image[offset:offset + size]
    if hashlib.sha256(body).hexdigest() != ORIGINAL['range_sha256']:
        raise ValueError('Native symbol range differs from sealed context')
    if not any(sym.name == ORIGINAL['mangled'] and sym['st_value'] == address
               and sym['st_size'] == size and sym['st_shndx'] == ORIGINAL['section']
               for sym in elffile.get_section_by_name('.symtab').iter_symbols()):
        raise ValueError('Original ELF symbol row differs from sealed context')

    model = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    code_page = address & ~0xfff
    model.mem_map(code_page, 0x1000)
    model.mem_write(address, body)
    model.mem_map(0x3000, 0x1000)
    model.mem_map(0x5000, 0x1000)
    model.mem_map(0x7000, 0x1000)
    sentinel = 0x7000
    stack = 0x5f00
    previous = 0
    cases = []
    known = {0: 0}

    for index, arg1, arg2 in INPUTS:
        if FIELD_OFFSET is not None:
            known[arg1] = index
        payload = bytearray(b'\xa5' * 0x1000)
        if FIELD_OFFSET is not None:
            struct.pack_into('<I', payload, FIELD_OFFSET, previous)
        model.mem_write(0x3000, bytes(payload))
        writes = []
        instructions = []

        def trace(_, pc, width, _data):
            if not address <= pc <= address + size - width:
                raise ValueError(f'Unexpected branch or call at {pc:#x}')
            instructions.append(pc)

        def write(_, _access, addr, width, value, _data):
            if not 0x5000 <= addr <= 0x6000 - width:
                writes.append([addr, width, value])

        code_hook = model.hook_add(UC_HOOK_CODE, trace)
        write_hook = model.hook_add(UC_HOOK_MEM_WRITE, write)
        model.reg_write(UC_ARM_REG_SP, stack)
        model.reg_write(UC_ARM_REG_LR, sentinel)
        model.reg_write(UC_ARM_REG_R0, 0x3000)
        model.reg_write(UC_ARM_REG_R1, arg1)
        model.reg_write(UC_ARM_REG_R2, arg2)
        model.emu_start(address, sentinel, count=32)
        if model.reg_read(UC_ARM_REG_PC) != sentinel or model.reg_read(UC_ARM_REG_SP) != stack:
            raise ValueError('Original function did not return with its stack restored')
        observed = bytes(model.mem_read(0x3000, 0x1000))
        previous_token = known[previous]
        if FIELD_OFFSET is not None:
            previous, = struct.unpack_from('<I', observed, FIELD_OFFSET)
            struct.pack_into('<I', payload, FIELD_OFFSET, previous)
        if observed != payload:
            raise ValueError('Original writes outside observed argument or object field')
        cases.append({'input': index, 'r1': arg1, 'r2': arg2,
                      'before': previous_token, 'after': known[previous],
                      'memory_writes': writes, 'instructions': instructions})
        model.hook_del(code_hook)
        model.hook_del(write_hook)
    return {'original': ORIGINAL, 'section_name': section.name,
             'unicorn_version': unicorn.__version__, 'cases': cases}
