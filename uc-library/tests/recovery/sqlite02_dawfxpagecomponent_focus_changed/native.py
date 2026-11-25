"""Execute original ARM focus behavior in Unicorn."""
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
    update, = {sym['st_value'] for sym in symbols.get_symbol_by_name(UPDATE)}
    cases = []
    for receiver_index, receiver in enumerate((0x20000000, 0x20001000)):
        stack, sentinel = 0x20004000, 0x20005000
        model = unicorn.Uc(unicorn.UC_ARCH_ARM, unicorn.UC_MODE_ARM)
        model.mem_map(address & ~0xfff, 0x2000)
        model.mem_write(address, body)
        # The observer hook returns from the called entry without executing
        # its application body. This only proves the caller's dispatch.
        model.mem_write(update, b'\x1e\xff\x2f\xe1')
        model.mem_map(0x20000000, 0x6000)
        model.reg_write(UC_ARM_REG_R0, receiver)
        model.reg_write(UC_ARM_REG_SP, stack)
        model.reg_write(UC_ARM_REG_LR, sentinel)
        writes, calls, instructions = [], [], []

        def write(_, _access, where, width, value, _context):
            if not stack - 0x1000 <= where <= stack - width:
                writes.append([where, width, value])

        def code(_, pc, width, _context):
            if pc == update:
                assert model.reg_read(UC_ARM_REG_R0) == receiver
                calls.append([receiver_index, model.reg_read(UC_ARM_REG_R1)])
            else:
                assert address <= pc <= address + size - width
                instructions.append(pc)

        model.hook_add(unicorn.UC_HOOK_MEM_WRITE, write)
        model.hook_add(unicorn.UC_HOOK_CODE, code)
        model.emu_start(address, sentinel, count=64)
        assert model.reg_read(UC_ARM_REG_PC) == sentinel
        assert model.reg_read(UC_ARM_REG_SP) == stack
        assert not writes and len(calls) == 1
        cases.append(dict(receiver=receiver, calls=calls, writes=writes,
                          instructions=instructions))
    original = {key: target[key] for key in
                ('firmware', 'role', 'mangled', 'address', 'size', 'section', 'range_sha256')}
    original.update(elf_sha256=target['elf'], file_offset=offset)
    return {'unicorn_version': unicorn.__version__,
            'update_entry': update,
            'targets': [dict(original=original, elf_path=str(ELF),
                             section_name=section.name, cases=cases)]}
