import hashlib
import json
from pathlib import Path
import struct

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import (
    UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_LR,
    UC_ARM_REG_SP, UC_ARM_REG_PC,
)

TASK = Path(__file__).parent.name
RUN = Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/reconstruction10x10-20261121')
READ_MAP = RUN / 'packeting/READ_INPUTS-post32-next-batch02-cycle21_g03-post32-next39-scoped01-dispatch02.json'
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
    task = TASK[-2:]
    inputs = {
        '04': [(0, 0, False), (0, 0, True), (5, 0, True), (22, 15, True), (15, 0, True)],
        '05': [(0, -1), (3, 0), (3, 2), (14, 2), (15, 2), (10, -20), (9, 2147483647)],
        '06': [(0, -4), (1, -1), (1, 0), (3, 2), (14, 3)],
        '07': [(9, 1000, 2, 1.0), (9, 1001, 2, 1.0), (9, 1001, 3, 1.0),
               (9, 1000, 2, 0.0), (9, 1001, 2, -1.0), (9, 1002, 2, 1.0)],
        '08': [(1000, 2, []), (1000, 2, [1, 0, 1]), (1000, 3, [0]), (1001, 2, [1])],
    }
    for args in inputs[task]:
        cpu = machine()
        pointer, info, entries, observers, obj_vt = [BASE + n for n in (0x100, 0x200, 0x300, 0x400, 0x600)]
        trace, labels, targets = [], [], []
        visible = False
        start_offset = 0
        numeric_vtable = symbols['_ZTVN4Core8Portable12NumericParamE'] + 8
        string_vtable = symbols['_ZTVN4Core8Portable11StringParamE'] + 8
        mixer_vtable = symbols['_ZTVN8Presonus7Surface14SLMixerHandlerE'] + 8
        page_vtable = symbols['_ZTVN8Presonus7Surface16GeqPageComponentE'] + 8
        assert get(cpu, numeric_vtable + 0x44) == 0x11e48c
        assert get(cpu, string_vtable + 0x74) == 0x12134c
        assert get(cpu, mixer_vtable + 0x70) == 0x84118
        assert get(cpu, mixer_vtable + 0x7c) == 0x840e4
        assert get(cpu, page_vtable + 0x18) == 0x11acd8
        if task != '08':
            start_offset = args[0]
            put(cpu, BASE + 0xc8, start_offset)
            put(cpu, BASE, page_vtable)
        if task == '04':
            _, notified, visible = args
            put(cpu, BASE + 0xcc, notified)
            put(cpu, BASE + 0xd0, entries)
            put(cpu, BASE + 0xd4, 2)
            for index in range(2):
                address = observers + index * 8
                put(cpu, entries + 4 * index, address)
                put(cpu, address, mixer_vtable + 0x7c)
        elif task == '05':
            cpu.reg_write(UC_ARM_REG_R1, args[1] & 0xffffffff)
        elif task == '06':
            put(cpu, pointer, args[1] & 0xffffffff)
            cpu.reg_write(UC_ARM_REG_R1, pointer)
        else:
            tag, message = args[1:3] if task == '07' else args[:2]
            cpu.reg_write(UC_ARM_REG_R1, pointer)
            cpu.reg_write(UC_ARM_REG_R2, message)
            put(cpu, pointer, numeric_vtable)
            put(cpu, pointer + 12, info)
            put(cpu, info + 4, tag)
            if task == '08':
                put(cpu, BASE + 0xc8, entries)
                put(cpu, BASE + 0xcc, len(args[2]))
                for index, identity in enumerate(args[2]):
                    address = observers + identity * 8
                    put(cpu, entries + 4 * index, address)
                    put(cpu, address, mixer_vtable + 0x70)
        labels_base, aliases_base, targets_base = BASE + 0x1000, BASE + 0x2000, BASE + 0x3000
        for index in range(16):
            put(cpu, labels_base + index * 8, string_vtable)

        def cstring(address):
            return bytes(cpu.mem_read(address, 64)).split(bytes(1), 1)[0].decode()

        def hook(cpu, address, _size, _user):
            r0, r1, r2, r3 = (cpu.reg_read(reg) for reg in
                              (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3))
            result = r0
            intercepted = True
            if address == 0x8deec:
                assert r0 == BASE
                trace.append(['offset', struct.unpack('<i', struct.pack('<I', r1))[0]])
                return
            if address == 0x8dcc0:
                assert r0 == BASE
                trace.append(['refresh'])
                return
            if address == 0x681d4:
                assert r0 == BASE
                trace.append(['visible'])
                result = int(visible)
            elif address in (0x840e4, 0x84118):
                trace.append(['observer', (r0 - observers) // 8])
                assert (r0 - observers) % 8 == 0 and 0 <= (r0 - observers) // 8 < 2
            elif address == 0x11f24c:
                assert r0 == BASE + 0x28 and 0 <= r1 < 32
                result = (aliases_base if r1 % 2 else labels_base) + (r1 // 2) * 8
            elif address == 0xae58:
                assert r1 == symbols['_ZTIN4Core8Portable9ParameterE']
                assert r2 == symbols['_ZTIN4Core8Portable10AliasParamE']
                assert aliases_base <= r0 < aliases_base + 128 and r3 == 0
            elif address in (0x8c1a8, 0x4b47c):
                fmt = cstring(r1)
                if fmt == '%s_%02d':
                    formatted = fmt % (cstring(r2), r3)
                elif fmt == '%.1fk':
                    formatted = fmt % struct.unpack('<d', struct.pack('<II', r2, r3))[0]
                else:
                    assert fmt in ('%d', '%dk')
                    formatted = fmt % r2
                cpu.mem_write(r0, formatted.encode() + bytes(1))
            elif address == 0x12134c:
                assert r2 == 0 and r0 == labels_base + len(labels) * 8
                labels.append(cstring(r1))
            elif address == 0x11acd8:
                assert r0 == BASE
                name = cstring(r1)
                index = int(name.rsplit('_', 1)[1])
                trace.append(['find', name])
                result = targets_base + 8 * index if index % 2 else 0
            elif address == 0x120e24:
                assert r0 == aliases_base + 8 * len(targets)
                targets.append((r1 - targets_base) // 8 if r1 else None)
            elif address == 0x11c87c:
                assert [r0, r1, r2] == [BASE, pointer, args[2]]
                trace.append(['base', r2])
            elif address == 0x11e48c:
                assert r0 == pointer
                trace.append(['value'])
                result = struct.unpack('<I', struct.pack('<f', args[3]))[0]
            else:
                intercepted = False
            if intercepted:
                cpu.reg_write(UC_ARM_REG_R0, result)
                cpu.reg_write(UC_ARM_REG_PC, cpu.reg_read(UC_ARM_REG_LR))

        run(cpu, hook)
        cases.append(dict(args=list(args), trace=trace, labels=labels, targets=targets,
                          offset=get(cpu, BASE + 0xc8) if task != '08' else None,
                          last_notified=get(cpu, BASE + 0xcc) if task == '04' else None))
    boundaries = ('Original target instructions and reachable application downstream offset/refresh bodies '
                  'and compiler runtime execute. Exact native virtual slot identities and controlled '
                  'provider inputs, callbacks, CCL and runtime type boundaries are recorded in the traces.')
    return dict(task_id=TASK, elf_sha256=target['original_elf_sha256'],
                mangled=target['mangled'], section=section.name, file_offset=filename_offset,
                address=start, size=size, range_sha256=sha(body), cases=cases,
                native_boundaries=boundaries, native_elf_input=str(elf_path))


if __name__ == '__main__':
    print(json.dumps(generate(), indent=2))
