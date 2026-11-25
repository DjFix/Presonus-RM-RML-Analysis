"""Run each role's exact ARM MeterPeakControl entry and record state effects."""
import hashlib
from io import BytesIO
import json
from pathlib import Path
import struct

from elftools.elf.elffile import ELFFile
import unicorn
from unicorn.arm_const import (UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0,
                               UC_ARM_REG_R1, UC_ARM_REG_SP)

TASK = Path(__file__).parent.name
PACKET = Path('temp/recovery-work/sqlite-issued/packet') / TASK / 'CONTEXT.json'
ROOT = Path('/home/rs/projects/opencs/ai-line-analysis')
TAGS = (0, 19, -3, -2147483648, 2147483647)
RECEIVER, PARAM, TIMER, STORAGE = 0x20000000, 0x20001000, 0x20002000, 0x20003000
STACK, SENTINEL = 0x20006000, 0x20007000
SURVIVOR = TIMER + 0x1000
CONTROL_D2 = '_ZN8Presonus5Panel7ControlD2Ev'
VECTOR_REMOVE = '_ZN4Core13MutableVectorIPN8Presonus5Panel7Control5TimerENS_6VectorIS5_EEE6removeERKS5_'
PARAM_REMOVE = '_ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE'
TIMERS = '_ZN8Presonus5Panel7Control6timersE'
VTABLE = '_ZTVN8Presonus5Panel16MeterPeakControlE'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def get_symbol(elf, name):
    matches = elf.get_section_by_name('.symtab').get_symbol_by_name(name)
    assert matches and len({s['st_value'] for s in matches}) == 1, name
    return matches[0]


def range_data(elf, image, symbol):
    section = elf.get_section(symbol['st_shndx'])
    relative = symbol['st_value'] - section['sh_addr']
    size = symbol['st_size']
    assert 0 <= relative <= section['sh_size'] - size
    start = section['sh_offset'] + relative
    return section.name, start, image[start:start + size]


def arm_branch_target(pc, word):
    displacement = (word & 0xffffff) << 2
    if displacement & (1 << 25):
        displacement -= 1 << 26
    return pc + 8 + displacement


def observe_target(target, evidence):
    elf_path = ROOT / evidence['original']['elf_path']
    image = elf_path.read_bytes()
    assert sha(image) == target['elf']
    elf = ELFFile(BytesIO(image))
    entry = get_symbol(elf, target['mangled'])
    address, size = target['address'], target['size']
    assert (entry['st_value'], entry['st_size'], entry['st_shndx']) == (
        address, size, target['section'])
    name, offset, body = range_data(elf, image, entry)
    assert sha(body) == target['range_sha256']
    assert offset == evidence['original']['file_offset']
    names = target['mangled']
    construct = 'C1Ei' in names or 'C2Ei' in names
    deleting = 'D0Ev' in names
    destroy = deleting or 'D1Ev' in names
    partner = None
    vtable = get_symbol(elf, VTABLE)['st_value'] + 8
    if construct:
        mate = names.replace('C1Ei', 'C2Ei') if 'C1Ei' in names else names.replace('C2Ei', 'C1Ei')
        mate_symbol = get_symbol(elf, mate)
        _, mate_offset, mate_body = range_data(elf, image, mate_symbol)
        partner = dict(mangled=mate, address=mate_symbol['st_value'],
                       file_offset=mate_offset, size=len(mate_body),
                       range_sha256=sha(mate_body), identical_body=mate_body == body,
                       same_address=address == mate_symbol['st_value'])
        assert body[-4:] == struct.pack('<I', vtable)
    dependency_ranges = {}
    if destroy:
        for dependency in (CONTROL_D2, VECTOR_REMOVE, PARAM_REMOVE):
            symbol = get_symbol(elf, dependency)
            _, dep_offset, dep_body = range_data(elf, image, symbol)
            dependency_ranges[dependency] = dict(address=symbol['st_value'], size=len(dep_body),
                                                  file_offset=dep_offset, range_sha256=sha(dep_body))
        control = dependency_ranges[CONTROL_D2]['address']
        control_body = image[dependency_ranges[CONTROL_D2]['file_offset']:]
        timer_delete = arm_branch_target(control + 0xcc,
                                         struct.unpack_from('<I', control_body, 0xcc)[0])
        assert arm_branch_target(address + 28, struct.unpack_from('<I', body, 28)[0]) == control
        receiver_delete = (arm_branch_target(address + 36, struct.unpack_from('<I', body, 36)[0])
                           if deleting else None)
        branches = [record for record in evidence['site_evidence'] if record['kind'] == 'branch']
        if deleting:
            assert any(r['destination'] == receiver_delete and
                       '_ZdlPv@@GLIBCXX_3.4' in r['names'] for r in branches)
        timers = get_symbol(elf, TIMERS)['st_value']
        arguments = (0, 1)
    elif construct:
        arguments = TAGS
    else:
        literals = struct.unpack_from('<III', body, len(body) - 12)
        arguments = (0, -1, *(x for key in literals for x in (key - 1, key, key + 1)))

    cases = []
    for argument in arguments:
        model = unicorn.Uc(unicorn.UC_ARCH_ARM, unicorn.UC_MODE_ARM)
        def put(where, value):
            model.mem_write(where, struct.pack('<I', value & 0xffffffff))

        def get(where):
            return struct.unpack('<I', bytes(model.mem_read(where, 4)))[0]

        # Map the original loaded image and use separate initialized synthetic
        # object/stack pages. The whole ELF is hash-checked above.
        pages = set()
        for segment in elf.iter_segments():
            if segment['p_type'] != 'PT_LOAD':
                continue
            first = segment['p_vaddr'] & ~0xfff
            last = (segment['p_vaddr'] + segment['p_memsz'] + 0xfff) & ~0xfff
            for page in range(first, last, 0x1000):
                if page not in pages:
                    model.mem_map(page, 0x1000)
                    pages.add(page)
            model.mem_write(segment['p_vaddr'], segment.data())

        for page in range(RECEIVER, SENTINEL + 0x1000, 0x1000):
            model.mem_map(page, 0x1000)
        model.reg_write(UC_ARM_REG_SP, STACK)
        model.reg_write(UC_ARM_REG_LR, SENTINEL)
        model.reg_write(UC_ARM_REG_R0, RECEIVER)
        model.reg_write(UC_ARM_REG_R1, argument & 0xffffffff)
        model.mem_write(RECEIVER, bytes([0xa5]) * 64)
        writes, calls, freed, executed = [], [], [], set()
        if destroy:
            model.mem_write(RECEIVER, bytes(64))
            put(RECEIVER, vtable)
            put(RECEIVER + 8, PARAM if argument else 0)
            put(PARAM + 0x1c, PARAM + 0x100)
            put(PARAM + 0x20, 2 if argument else 0)
            put(PARAM + 0x100, RECEIVER)
            put(PARAM + 0x104, SURVIVOR)
            put(timers + 4, STORAGE + 0x100)
            put(timers + 8, 2 if argument else 0)
            put(timers + 12, 2)
            put(STORAGE + 0x100, TIMER)
            put(STORAGE + 0x104, SURVIVOR)
            put(TIMER, RECEIVER)
            put(SURVIVOR, SURVIVOR)

        def write(_, _access, where, width, value, _context):
            if not STACK - 0x1000 <= where <= STACK - width:
                writes.append([where, width, value])

        def code(_, pc, width, _context):
            if destroy and pc in (timer_delete, receiver_delete):
                pointer = model.reg_read(UC_ARM_REG_R0)
                assert pointer in (TIMER, RECEIVER) and pointer not in freed
                if pointer == RECEIVER:
                    assert get(RECEIVER + 8) == 0
                    if argument:
                        assert get(PARAM + 0x20) == get(timers + 8) == 1
                # External delete boundary: release the live page in the
                # emulator. Later access would fault. Preserve the ARM return.
                model.mem_unmap(pointer, 0x1000)
                freed.append(pointer)
                calls.append(['delete_timer' if pointer == TIMER else 'delete_receiver', pointer])
                model.reg_write(UC_ARM_REG_PC, model.reg_read(UC_ARM_REG_LR))
                return
            for label, dep in dependency_ranges.items():
                if dep['address'] <= pc <= dep['address'] + dep['size'] - width:
                    if pc == dep['address']:
                        calls.append([label, model.reg_read(UC_ARM_REG_R0)])
                    return
            assert address <= pc <= address + size - width, hex(pc)
            executed.add(pc)

        model.hook_add(unicorn.UC_HOOK_MEM_WRITE, write)
        model.hook_add(unicorn.UC_HOOK_CODE, code)
        model.emu_start(address, SENTINEL, count=800)
        assert model.reg_read(UC_ARM_REG_PC) == SENTINEL
        assert model.reg_read(UC_ARM_REG_SP) == STACK
        if destroy:
            count = get(timers + 8)
            observers = get(PARAM + 0x20)
            timer_survived = get(STORAGE + 0x100) == SURVIVOR if argument else None
            observer_survived = get(PARAM + 0x100) == SURVIVOR if argument else None
            assert count == observers == argument
            assert not argument or (timer_survived and observer_survived)
            assert freed == ([TIMER] if argument else []) + ([RECEIVER] if deleting else [])
            if not deleting:
                assert get(RECEIVER + 8) == 0
            output = [int(RECEIVER in freed), count, observers]
        elif construct:
            assert get(RECEIVER) == vtable
            assert bytes(model.mem_read(RECEIVER + 40, 24)) == bytes([0xa5]) * 24
            output = [struct.unpack('<i', bytes(model.mem_read(RECEIVER + off, 4)))[0]
                      for off in range(4, 40, 4)]
        else:
            result = model.reg_read(UC_ARM_REG_R0)
            assert result in (0, RECEIVER) and not writes
            output = [int(result == RECEIVER)]
        cases.append(dict(argument=argument, output=output, writes=writes, calls=calls,
                          instructions=sorted(executed)))
    original = {key: target[key] for key in
                ('firmware', 'role', 'mangled', 'address', 'size', 'section', 'range_sha256')}
    original.update(elf_sha256=target['elf'], file_offset=offset)
    return dict(original=original, elf_path=str(elf_path), section_name=name, cases=cases,
                compared_constructor_variant=partner, dependency_ranges=dependency_ranges,
                vtable_address_point=vtable)


def observe():
    task = json.loads(PACKET.read_text())['task']
    evidence_file, = task['review']['evidence']
    raw = (ROOT / evidence_file['path']).read_bytes()
    assert sha(raw) == evidence_file['sha256']
    evidence = {row['original']['elf']: row for row in json.loads(raw)['native']}
    return {'unicorn_version': unicorn.__version__, 'targets': [
        observe_target(target, evidence[target['elf']]) for target in task['originals']]}
