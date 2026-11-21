import hashlib
import json
from pathlib import Path
import struct

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import (
    UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_LR,
    UC_ARM_REG_SP, UC_ARM_REG_PC,
)

TASK = Path(__file__).parent.name
RUN = Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/reconstruction10x10-20261121')
READ_MAP = RUN / 'packeting/READ_INPUTS-post32-next-batch02-cycle21_g03-post32-next39-scoped03-dispatch02.json'
PACKET = RUN / 'packeting/post32-next-batch02/packets' / TASK
BASE = 0x3000000
STACK = 0x4000000
STOP = 0x5000000


def sha(data):
    return hashlib.sha256(data).hexdigest()


def generate():
    request = json.loads((PACKET / 'request.json').read_text())
    target = request['targets'][0]
    release = request['work_binding']['binary_releases'][0]
    entry = json.loads(READ_MAP.read_text())[release['original_path']]
    elf_path = Path(entry['frozen_read_path'])
    assert sha(elf_path.read_bytes()) == target['original_elf_sha256'] == entry['sha256']
    start = target['address']
    size = target['size']
    with elf_path.open('rb') as stream:
        elf = ELFFile(stream)
        section = elf.get_section(target['section'])
        filename_offset = section['sh_offset'] + start - section['sh_addr']
        assert 0 <= start - section['sh_addr'] <= section['sh_size'] - size
        stream.seek(filename_offset)
        body = stream.read(size)
        assert len(body) == size
        mappings = [(s['p_vaddr'], s['p_memsz'], s.data()) for s in elf.iter_segments()
                    if s['p_type'] == 'PT_LOAD']
        symbols = {s.name: s['st_value'] for s in elf.get_section_by_name('.symtab').iter_symbols()}
        assert symbols[target['mangled']] == start

    def machine():
        cpu = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        low = min(address for address, _, _ in mappings) & ~4095
        high = max(address + length for address, length, _ in mappings)
        cpu.mem_map(low, (high - low + 4095) & ~4095)
        for address, _, data in mappings:
            cpu.mem_write(address, data)
        assert bytes(cpu.mem_read(start, size)) == body
        for address in (BASE, STACK, STOP):
            cpu.mem_map(address, 0x10000)
        for reg, value in ((UC_ARM_REG_R0, BASE), (UC_ARM_REG_SP, STACK + 0x8000),
                           (UC_ARM_REG_LR, STOP)):
            cpu.reg_write(reg, value)
        return cpu

    def put(cpu, address, word):
        cpu.mem_write(address, struct.pack('<I', word))

    def get(cpu, address):
        return struct.unpack('<I', cpu.mem_read(address, 4))[0]

    def run(cpu, hook):
        cpu.hook_add(UC_HOOK_CODE, hook)
        cpu.emu_start(start, STOP, count=10000)
        assert cpu.reg_read(UC_ARM_REG_PC) == STOP

    cases = []
    string_vtable = symbols['_ZTVN4Core8Portable11StringParamE'] + 8
    provider = symbols['_ZN4Core8Portable11StringParam10fromStringEPKcb']
    base = symbols['_ZN8Presonus7Surface20PresetsPageComponent6onShowEb']
    for show, has_parameter in ((False, False), (False, True), (True, False), (True, True)):
        cpu = machine()
        parameter = BASE + 0x200
        put(cpu, parameter, string_vtable)
        assert get(cpu, string_vtable + 0x74) == provider
        cpu.reg_write(UC_ARM_REG_R1, int(show))
        calls = []

        def cstring(address):
            return bytes(cpu.mem_read(address, 64)).split(bytes(1), 1)[0].decode()

        def hook(cpu, address, _size, _user):
            r0 = cpu.reg_read(UC_ARM_REG_R0)
            r1 = cpu.reg_read(UC_ARM_REG_R1)
            r2 = cpu.reg_read(UC_ARM_REG_R2)
            result = r0
            if address == 0x3ae34:
                title = cstring(r1)
                calls.append(['title', title])
                cpu.mem_write(r0, title.encode() + bytes(1))
            elif address == 0x11acf0:
                assert r0 == BASE
                calls.append(['lookup', r1])
                result = parameter if has_parameter else 0
            elif address == provider:
                assert r0 == parameter
                calls.append(['write', cstring(r1), bool(r2)])
            elif address == base:
                assert r0 == BASE and r1 == show
                calls.append(['base', bool(r1)])
            else:
                return
            cpu.reg_write(UC_ARM_REG_R0, result)
            cpu.reg_write(UC_ARM_REG_PC, cpu.reg_read(UC_ARM_REG_LR))

        run(cpu, hook)
        cases.append(dict(show=show, has_parameter=has_parameter, calls=calls))
    boundaries = ('Original derived ARM body executes. Exact CCL string ctor, lookup and '
                  'StringParam vtable +0x74, and original base onShow are observed controlled boundaries.')
    return dict(task_id=TASK, elf_sha256=target['original_elf_sha256'],
                mangled=target['mangled'], section=section.name, file_offset=filename_offset,
                address=start, size=size, range_sha256=sha(body), cases=cases,
                native_boundaries=boundaries, native_elf_input=str(elf_path))


if __name__ == '__main__':
    print(json.dumps(generate(), indent=2))
