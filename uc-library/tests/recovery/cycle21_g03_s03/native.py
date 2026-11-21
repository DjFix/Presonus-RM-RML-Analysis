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

    page_vtable = symbols['_ZTVN8Presonus7Surface23GeqPresetsPageComponentE'] + 8
    param_vtable = symbols['_ZTVN4Core8Portable12NumericParamE'] + 8
    mixer_vtable = symbols['_ZTVN8Presonus24MixerClientComponentBaseE'] + 8
    path = symbols['_ZNK4Core8Portable9Component16getComponentPathERNS_13CStringBufferILi256EEE']
    cases = []
    scenarios = [
        (False, 0, 2, False), (True, 0, 2, True), (True, 1.75, 2, True),
        (True, 2, 2, False), (True, 19, 20, True), (True, 20.75, 2, True),
        (True, 21, 2, True), (True, 22, 2, False), (True, 1, 2, False),
        (True, 20, 2, False),
    ]
    for exists, value, count, present in scenarios:
        cpu = machine()
        parameter, mixer, selected, output = (BASE + offset for offset in (0x1000, 0x2000, 0x3000, 0x4000))
        put(cpu, BASE, page_vtable)
        put(cpu, BASE + 0xe4, mixer)
        put(cpu, parameter, param_vtable)
        put(cpu, mixer, mixer_vtable)
        cpu.reg_write(UC_ARM_REG_R1, output)
        names = {
            get(cpu, page_vtable + 0x18): ('findParameter', 0x11acd8),
            get(cpu, param_vtable + 0x44): ('getValue', 0x11e48c),
            get(cpu, mixer_vtable + 0x48): ('getNumMixGeqs', 0x5d84c),
            get(cpu, mixer_vtable + 0x4c): ('getMainGeq', 0x5d86c),
            get(cpu, mixer_vtable + 0x50): ('getMixGeq', 0x5d8f4),
            path: ('getComponentPath', 0x11ca80),
        }
        assert all(address == expected for address, (_, expected) in names.items())
        calls = []
        runtime = []

        def hook(cpu, address, _size, _user):
            if address not in names:
                if not start <= address < start + size:
                    runtime.append(address)
                return
            operation, _ = names[address]
            receiver = cpu.reg_read(UC_ARM_REG_R0)
            arg = cpu.reg_read(UC_ARM_REG_R1)
            if operation == 'findParameter':
                assert receiver == BASE
                key = bytes(cpu.mem_read(arg, 13)).split(b'\0', 1)[0].decode()
                calls.append([operation, key])
                result = parameter if exists else 0
            elif operation == 'getValue':
                assert receiver == parameter
                calls.append([operation])
                result = struct.unpack('<I', struct.pack('<f', value))[0]
            elif operation == 'getNumMixGeqs':
                assert receiver == mixer
                calls.append([operation])
                result = count
            elif operation in ('getMainGeq', 'getMixGeq'):
                assert receiver == mixer
                calls.append([operation, arg])
                result = selected if present else 0
            else:
                assert receiver == selected and arg == output
                calls.append([operation])
                result = receiver
            cpu.reg_write(UC_ARM_REG_R0, result)
            cpu.reg_write(UC_ARM_REG_PC, cpu.reg_read(UC_ARM_REG_LR))

        run(cpu, hook)
        assert bool(runtime) == exists
        cases.append(dict(parameter_exists=exists, value=value, count=count,
                          target_exists=present, calls=calls, runtime_pcs=runtime))
    boundaries = ('Original ARM target and conversion runtime execute. Vtable slots are read from exact ELF; '
                  'original CCL and mixer entry points are intercepted for modeled provider inputs and call observations.')

    return dict(task_id=TASK, elf_sha256=target['original_elf_sha256'],
                mangled=target['mangled'], section=section.name, file_offset=filename_offset,
                address=start, size=size, range_sha256=sha(body), cases=cases,
                native_boundaries=boundaries, native_elf_input=str(elf_path))


if __name__ == '__main__':
    print(json.dumps(generate(), indent=2))
