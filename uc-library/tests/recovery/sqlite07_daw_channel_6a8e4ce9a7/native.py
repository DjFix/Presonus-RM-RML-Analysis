"""Execute exact DAWChannel entries against genuine ELF providers and bounded ABI hooks."""
import importlib.util
import json
from pathlib import Path
import struct
import sys

from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_LR as LR, UC_ARM_REG_PC as PC
from unicorn.arm_const import UC_ARM_REG_R0 as R0, UC_ARM_REG_R1 as R1, UC_ARM_REG_R2 as R2

PROVIDER_MACHINE = Path('uc-library/tests/recovery/sqlite04_daw_045d71117e05/native.py')
SPEC = importlib.util.spec_from_file_location('daw_arm_machine', PROVIDER_MACHINE)
provider = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = provider
SPEC.loader.exec_module(provider)

CHANNEL = '10DAWChannel'
FOLDERS = {'getInserts': 'inserts', 'getCueMixes': 'cuemix',
           'getPosts': 'posts', 'getSends': 'sends'}
FOLDER_ID = 0x64774446
FIND_CHILD = '_ZNK4Core8Portable9Component9findChildEPKc'
SELECTED = 'isSelected'
ID = 'getID'


def method(mangled):
    assert mangled.startswith('_ZNK8Presonus10DAWChannel') and mangled.endswith('Ev')
    return mangled.removeprefix('_ZNK8Presonus10DAWChannel')[:-2].lstrip('0123456789')


def folder(original, name):
    pointer, type_id = struct.unpack('<II', bytes.fromhex(original['range_hex'])[-8:])
    assert type_id == FOLDER_ID
    cases = []
    for variation in ('missing', 'foreign', 'wrong-name', 'match'):
        machine = provider.Machine(original)
        receiver, child = provider.RECEIVER, provider.CHILDREN
        machine.construct(CHANNEL, receiver)
        literal = machine.string(pointer)
        assert literal == FOLDERS[name]
        if variation != 'missing':
            machine.construct(None if variation == 'foreign' else provider.FOLDER, child)
            child_name = literal + 'Other' if variation == 'wrong-name' else literal
            machine.uc.mem_write(child + 8, child_name.encode('ascii') + b'\0')
            machine.children(receiver, [child])

        def trace(uc, _address, _size, _data):
            assert uc.reg_read(R0) == receiver and uc.reg_read(R1) == pointer
            machine.events.append([FIND_CHILD, receiver, pointer, machine.string(pointer)])

        address = machine.address(FIND_CHILD)
        machine.uc.hook_add(UC_HOOK_CODE, trace, begin=address, end=address)
        machine.events.clear()
        result = machine.invoke(original['mangled'], receiver)
        assert result == (child if variation == 'match' else 0)
        assert machine.events[0] == [FIND_CHILD, receiver, pointer, literal]
        casts = [event for event in machine.events if event[0] in
                 (provider.CAST_BASE, provider.CAST_FOLDER)]
        assert casts == ([[provider.CAST_BASE, child, type_id]] if variation == 'foreign'
                         else [[provider.CAST_FOLDER, child, type_id]] if variation == 'match'
                         else [])
        cases.append(dict(input=[name, variation], addresses=dict(receiver=receiver, child=child),
                          result=result, trace=machine.events, portable='identity' if result else 'null'))
    return cases


def selected(original):
    cases = []
    for value in (None, -1.5, -0.0, 0.0, 0.125, 1.25):
        machine = provider.Machine(original)
        receiver, parm = provider.RECEIVER, provider.PARAMETERS
        machine.construct(CHANNEL, receiver)
        if value is not None:
            machine.parameter(parm, 'selected', 6, value)
            machine.store(receiver + 0x84, parm)
        machine.events.clear()
        result = machine.invoke(original['mangled'], receiver)
        reads = [event for event in machine.events if event[0] == provider.GET_VALUE]
        assert reads == ([] if value is None else [[provider.GET_VALUE, parm]])
        assert result == int(value is not None and value > 0)
        cases.append(dict(input=[SELECTED, 'missing' if value is None else repr(value)],
                          result=result, trace=machine.events, portable=str(result)))
    return cases


def identifier(original):
    machine = provider.Machine(original)
    guard, buffer = struct.unpack('<II', bytes.fromhex(original['range_hex'])[-8:])
    _, _, imports, _ = provider.read_elf(original['elf_path'])
    acquire, release = [imports['__cxa_guard_' + kind] for kind in ('acquire', 'release')]
    machine.store(guard, 0)
    machine.uc.mem_write(buffer, b'\xA5' * 64)
    receiver, other = provider.RECEIVER, provider.PARENT
    machine.construct(CHANNEL, receiver)
    machine.construct(CHANNEL, other)
    table, stub = provider.PARAMETERS + 0x700, 0x5200FD00
    machine.store(table + 0x70, stub)
    current_parameter = None
    text = None

    def guard_hook(uc, address, _size, _data):
        assert uc.reg_read(R0) == guard
        if address == acquire:
            assert machine.load(guard) == 0
            uc.reg_write(R0, 1)
            machine.events.append(['guard_acquire', guard])
        else:
            assert address == release and machine.uc.mem_read(buffer, 1) == b'\0'
            machine.store(guard, 1)
            machine.events.append(['guard_release', guard])
        uc.reg_write(PC, uc.reg_read(LR))

    def format_string(uc, _address, _size, _data):
        args = [uc.reg_read(reg) for reg in (R0, R1, R2)]
        assert args == [current_parameter, buffer, 64]
        machine.uc.mem_write(buffer, text.encode('ascii')[:63] + b'\0')
        machine.events.append(['formatter_boundary', *args])
        uc.reg_write(PC, uc.reg_read(LR))

    for address, hook in ((acquire, guard_hook), (release, guard_hook), (stub, format_string)):
        machine.uc.hook_add(UC_HOOK_CODE, hook, begin=address, end=address)

    args = [None, '', 'Group-Bus 3', 'X' * 80]
    cases = []
    for index, text in enumerate(args):
        obj = other if index == 3 else receiver
        current_parameter = provider.PARAMETERS + index * 0x100
        if text is not None:
            machine.store(current_parameter, table)
            machine.store(obj + 0x8c, current_parameter)
        machine.events.clear()
        result = machine.invoke(original['mangled'], obj)
        if text is None:
            assert result == 0 and not machine.events and machine.load(guard) == 0
            observed = 'null'
        else:
            assert result == buffer and machine.load(guard) == 1
            expected_events = [['guard_acquire', guard], ['guard_release', guard]] if index == 1 else []
            assert machine.events == expected_events + [['formatter_boundary', current_parameter, buffer, 64]]
            observed = machine.string(result)
            assert observed == text[:63]
        cases.append(dict(input=[ID, 'missing' if text is None else 'present', *([] if text is None else [text])],
                          receiver=obj, result=result, trace=machine.events, portable=observed))
    return cases


def run(packet):
    result = []
    for item in json.loads(packet.read_text())['originals']:
        original = item['original']
        provider.check_range(original)
        name = method(original['mangled'])
        if name in FOLDERS:
            cases = folder(original, name)
        elif name == SELECTED:
            cases = selected(original)
        else:
            assert name == ID
            cases = identifier(original)
        result.append(dict(original=original, method=name, cases=cases))
    return result


if __name__ == '__main__':
    print(json.dumps(run(Path(sys.argv[1])), indent=2))
