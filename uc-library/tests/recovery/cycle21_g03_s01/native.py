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
READ_MAP = RUN / 'packeting/READ_INPUTS-post15-wave-compatible35-batch04-cycle21_g03.json'
PACKET = RUN / 'packeting/post15-wave-compatible35-batch04/packets' / TASK
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

    callee = symbols['_ZN8Presonus7Surface20PresetsPageComponent12paramChangedEPN4Core8Portable9ParameterEi']
    assert callee == 0xb47b0
    cases = []
    for message in (0, 2, 3, 0xffffffff):
        cpu = machine()
        pointer = BASE + 0x100
        cpu.reg_write(UC_ARM_REG_R1, pointer)
        cpu.reg_write(UC_ARM_REG_R2, message)
        calls = []

        def hook(cpu, address, _size, _user):
            if address == callee:
                assert cpu.reg_read(UC_ARM_REG_R0) == BASE
                assert cpu.reg_read(UC_ARM_REG_R1) == pointer
                assert cpu.reg_read(UC_ARM_REG_R2) == message
                calls.append(address)
                cpu.reg_write(UC_ARM_REG_PC, cpu.reg_read(UC_ARM_REG_LR))

        run(cpu, hook)
        assert calls == [callee]
        cases.append(dict(message=message if message < 0x80000000 else message - (1 << 32),
                          target=calls[0], unchanged_parameter_pointer=True,
                          unchanged_receiver=True))
    boundaries = 'Original derived ARM body executes; exact original base tail target is observed and intercepted before its body.'

    return dict(task_id=TASK, elf_sha256=target['original_elf_sha256'],
                mangled=target['mangled'], section=section.name, file_offset=filename_offset,
                address=start, size=size, range_sha256=sha(body), cases=cases,
                native_boundaries=boundaries, native_elf_input=str(elf_path))


if __name__ == '__main__':
    print(json.dumps(generate(), indent=2))
