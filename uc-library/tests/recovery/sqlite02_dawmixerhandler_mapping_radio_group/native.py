"""Execute original ARM mapping behavior in Unicorn."""
import hashlib
from io import BytesIO
import json
from pathlib import Path

from elftools.elf.elffile import ELFFile
import unicorn
from unicorn.arm_const import (UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0,
                               UC_ARM_REG_R1, UC_ARM_REG_SP)

TASK = Path(__file__).parent.name
PACKET = Path('temp/recovery-work/sqlite-issued/packet') / TASK / 'CONTEXT.json'
ROOT = Path('/home/rs/projects/opencs/ai-line-analysis')
ELF = ROOT / 'rootfs/CS18_v13840/home/root/surface'
UPDATE = '_ZN8Presonus7Surface18DawFxPageComponent10updateListEb'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def observe():
    target, = json.loads(PACKET.read_text())['task']['originals']
    image = ELF.read_bytes()
    assert sha(image) == target['elf']
    elf = ELFFile(BytesIO(image))
    section = elf.get_section(target['section'])
    symbols = elf.get_section_by_name('.symtab')
    address, size = target['address'], target['size']
    relative = address - section['sh_addr']
    assert 0 <= relative <= section['sh_size'] - size
    offset = section['sh_offset'] + relative
    body = image[offset:offset + size]
    assert sha(body) == target['range_sha256']
    assert any(sym['st_value'] == address and sym['st_size'] == size
               and sym['st_shndx'] == target['section']
               for sym in symbols.get_symbol_by_name(target['mangled']))
    cases = []
    for receiver, parameter in ((0x20000000, 0), (0x20000000, 0x20002000),
                                (0x20001000, 0), (0x20001000, 0x20002000)):
        stack, sentinel = 0x20004000, 0x20005000
        model = unicorn.Uc(unicorn.UC_ARCH_ARM, unicorn.UC_MODE_ARM)
        model.mem_map(address & ~0xfff, 0x2000)
        model.mem_write(address, body)
        model.mem_map(0x20000000, 0x6000)
        model.mem_write(receiver, bytes([0xa5]) * 128)
        if parameter:
            model.mem_write(parameter, bytes([0x5a]) * 128)
        model.reg_write(UC_ARM_REG_R0, receiver)
        model.reg_write(UC_ARM_REG_R1, parameter)
        model.reg_write(UC_ARM_REG_SP, stack)
        model.reg_write(UC_ARM_REG_LR, sentinel)
        writes, calls, instructions = [], [], []

        def write(_, _access, where, width, value, _context):
            if not stack - 0x1000 <= where <= stack - width:
                writes.append([where, width, value])

        def code(_, pc, width, _context):
            assert address <= pc <= address + size - width
            instructions.append(pc)

        model.hook_add(unicorn.UC_HOOK_MEM_WRITE, write)
        model.hook_add(unicorn.UC_HOOK_CODE, code)
        model.emu_start(address, sentinel, count=64)
        assert model.reg_read(UC_ARM_REG_PC) == sentinel
        assert model.reg_read(UC_ARM_REG_SP) == stack
        assert not writes and not calls
        assert bytes(model.mem_read(receiver, 128)) == bytes([0xa5]) * 128
        if parameter:
            assert bytes(model.mem_read(parameter, 128)) == bytes([0x5a]) * 128
        cases.append(dict(receiver=receiver, parameter=parameter,
                          result=model.reg_read(UC_ARM_REG_R0), writes=writes,
                          instructions=instructions))
    original = {key: target[key] for key in
                ('firmware', 'role', 'mangled', 'address', 'size', 'section', 'range_sha256')}
    original.update(elf_sha256=target['elf'], file_offset=offset)
    return {'unicorn_version': unicorn.__version__,
            
            'targets': [dict(original=original, elf_path=str(ELF),
                             section_name=section.name, cases=cases)]}
