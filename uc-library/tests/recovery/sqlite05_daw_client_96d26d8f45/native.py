"""Execute separately range-verified ARM methods with traced provider seams."""

import functools
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0
from unicorn.arm_const import UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_SP

PACKETS = Path('temp/recovery-work/sqlite-issued/packet')
RECEIVER, STACK, FINISH = 0x10000000, 0x11000800, 0x12000000
VTABLE, CHILD, OBSERVERS = 0x13000000, 0x14000000, 0x15000000
POINTERS = (0, 0x16000100, 0x16000200)
FLAG_SEED = 0x12345001
FLAG_OFFSET, FOCUS_OFFSET, HANDLER_OFFSET, TIME_OFFSET = 0x6b4, 0x694, 0x690, 0x68c
OBS_ARRAY, OBS_COUNT = 0x64c, 0x650
ORDER = (2, 0, 1)
OBSERVER_SEAMS = {
    'setFocusChannel': 0, 'channelsChanged': 1, 'slotCountChanged': 3,
    'slotEditChanged': 4, 'sendObjectChangeMessage': 7, 'setDAWProgress': 7,
}
LOOP_METHODS = ('getLoopStartParam', 'getLoopEndParam')
NAMED_METHODS = {
    'getMixer', 'getControlLink', 'getDocument', 'getRecordDiskSpace',
    'getSessionComponent', 'getRecordPanelComponent', 'getMetronomeComponent',
}
RETURN_METHODS = NAMED_METHODS | set(LOOP_METHODS) | {
    'getFocusChannel', 'getTimeInfo', 'isDAWProgressMode', 'castTo',
}
CCL_OPTIMIZE = '_ZN4Core17FormatterRegistry8optimizeEPPKc'
DAW_VTABLE = '_ZTVN8Presonus18DAWClientComponentE'
CCL_FIND_CHILD = '_ZNK4Core8Portable9Component9findChildEPKc'
CCL_BY_TAG = '_ZNK4Core8Portable9ParamList5byTagEi'
SEND_MESSAGE = '_ZN8Presonus18DAWClientComponent23sendObjectChangeMessageENS_21IDAWComponentObserver19ObjectChangeMessageE'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def packet_path(task):
    return PACKETS / task / 'CONTEXT.json'


def packet_method(packet):
    name = packet['originals'][0]['original']['mangled']
    text = subprocess.check_output(['c++filt', name], text=True).strip()
    return text.split('::')[2].split('(')[0]


@functools.lru_cache(maxsize=2)
def image(path, sha):
    data = Path(path).read_bytes()
    assert digest(data) == sha
    return data, ELFFile(io.BytesIO(data))


@functools.lru_cache(maxsize=2)
def symbol_table(elf):
    return elf.get_section_by_name('.symtab')


def symbol_range(data, elf, name, kind='STT_FUNC'):
    symbols = symbol_table(elf).get_symbol_by_name(name)
    symbol, = symbols
    assert symbol['st_info']['type'] == kind
    section = elf.get_section(symbol['st_shndx'])
    address = symbol['st_value']
    start = address - section['sh_addr']
    size = symbol['st_size']
    assert 0 <= start < start + size <= section['sh_size']
    offset = section['sh_offset'] + start
    payload = data[offset:offset + size]
    assert section.data()[start:start + size] == payload
    return dict(mangled=name, address=address, size=size, section=symbol['st_shndx'],
                section_name=section.name, file_offset=offset, range_hex=payload.hex(),
                range_sha256=digest(payload))


def cases(method):
    if method == 'castTo':
        type_ids = [0x64774343, 0x436c5274, 0x436c436f, 0x436f6d70]
        rejects = [0, 0x80000000, 0xffffffff, 0x7fffffff, 0x504f4253]
        return [(0, value, 0) for value in type_ids + rejects +
                [value + delta for value in type_ids for delta in (-1, 1)]]
    if method == 'setFocusChannel':
        return [(before, after, count) for count in (0, 1, 3)
                for before, after in ((0, 0), (0, 1), (1, 1), (1, 2), (2, 0))]
    if method in ('channelsChanged', 'slotCountChanged', 'slotEditChanged'):
        return [(0, value, count) for count in (0, 1, 3)
                for value in range(4 if method == 'slotEditChanged' else 2)]
    if method == 'sendObjectChangeMessage':
        return [(FLAG_SEED, value, count) for count in (0, 1, 3)
                for value in (0, 1, 2, 3, 0x12345678)]
    if method == 'setDAWProgress':
        return [(flags, value, count) for flags in (0, 2, FLAG_SEED, FLAG_SEED | 2)
                for count in (0, 1, 3) for value in (0, 1)]
    if method == 'isDAWProgressMode':
        return [(flags, 0, 0) for flags in (0, 1, 2, 3, 0xfffffffd, 0xfffffffe)]
    if method in ('setDialogHandler', 'setTimeInfoFactory'):
        return [(before, after, 0) for before, after in ((0, 1), (1, 2), (2, 0), (1, 1))]
    if method in NAMED_METHODS:
        return [(mode, 0, 0) for mode in range(4)]
    if method in LOOP_METHODS or method in ('getFocusChannel', 'getTimeInfo'):
        return [(mode, 0, 0) for mode in range(3)]
    assert method == 'optimize'
    return [(0, 0, 0)]


def execute(data, elf, method, original, provider, inputs):
    init, arg, count = inputs
    machine = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    mapped = set()
    loads = [s for s in elf.iter_segments() if s['p_type'] == 'PT_LOAD']

    def map_page(address):
        page = address & ~0xfff
        if page not in mapped:
            machine.mem_map(page, 0x1000)
            mapped.add(page)

    def read_elf(address, size):
        for segment in loads:
            offset = address - segment['p_vaddr']
            if 0 <= offset <= offset + size <= segment['p_filesz']:
                begin = segment['p_offset'] + offset
                return data[begin:begin + size]
        raise ValueError(f'Address not backed by the ELF: {address:#x}')

    def install(address, payload):
        for page in range(address & ~0xfff, address + len(payload), 0x1000):
            map_page(page)
        machine.mem_write(address, payload)

    def put(address, value):
        install(address, struct.pack('<I', value))

    def get(address):
        return struct.unpack('<I', machine.mem_read(address, 4))[0]

    def original_word(address):
        return struct.unpack('<I', read_elf(address, 4))[0]

    def original_string(address):
        payload = bytearray()
        for offset in range(128):
            byte = read_elf(address + offset, 1)[0]
            if byte == 0:
                return payload.decode('ascii')
            payload.append(byte)
        raise ValueError('Unterminated original ELF string')

    def normalized(address):
        return POINTERS.index(address)

    # Exact selected target bytes plus the real same-role fanout when progress
    # transfers there. Other provider calls stop at traced seams.
    for entry in (original, provider if method == 'setDAWProgress' else None):
        if entry:
            install(entry['address'], bytes.fromhex(entry['range_hex']))
    map_page(STACK)
    map_page(FINISH)
    install(RECEIVER, b'\xa7' * 0x700)
    put(RECEIVER, VTABLE)
    put(RECEIVER + OBS_ARRAY, OBSERVERS)
    put(RECEIVER + OBS_COUNT, count)
    put(RECEIVER + FLAG_OFFSET, init if method in (
        'isDAWProgressMode', 'setDAWProgress', 'sendObjectChangeMessage') else FLAG_SEED)
    put(RECEIVER + TIME_OFFSET, POINTERS[init if method == 'getTimeInfo' else 1])
    put(RECEIVER + HANDLER_OFFSET, POINTERS[init if method == 'setDialogHandler' else 1])
    put(RECEIVER + FOCUS_OFFSET, POINTERS[init if method in ('getFocusChannel', 'setFocusChannel') else 0])
    callback_targets = {}
    if method in OBSERVER_SEAMS:
        slot = OBSERVER_SEAMS[method]
        for position, index in enumerate(ORDER):
            observer = OBSERVERS + 0x100 + index * 0x100
            observer_vtable = VTABLE + 0x100 + index * 0x100
            target = CHILD + 0x100 + index * 4
            callback_targets[target] = (index, observer)
            put(OBSERVERS + position * 4, observer)
            put(observer, observer_vtable)
            put(observer_vtable + slot * 4, target)
            install(target, bytes.fromhex('1eff2fe1'))

    if method in NAMED_METHODS:
        put(VTABLE + 0x14, provider['address'])
    if provider and method != 'setDAWProgress':
        install(provider['address'], bytes.fromhex('1eff2fe1'))

    factory_address = None
    if method == 'setTimeInfoFactory':
        factory_address = original_word(original['address'] + original['size'] - 4)
        section = elf.get_section_by_name('.bss')
        assert section['sh_addr'] <= factory_address < section['sh_addr'] + section['sh_size']
        install(factory_address - 4, b'\xac' * 12)
        put(factory_address, POINTERS[init])
    else:
        assert method != 'optimize' or provider

    r0, r1, r2 = RECEIVER, arg, 0
    if method in ('setFocusChannel', 'setDialogHandler', 'channelsChanged', 'slotCountChanged'):
        r1 = POINTERS[arg]
    if method == 'slotEditChanged':
        r1, r2 = POINTERS[arg & 1], bool(arg & 2)
    if method == 'setTimeInfoFactory':
        r0, r1 = POINTERS[arg], 0xdeadbeef

    before = bytes(machine.mem_read(RECEIVER, 0x700))
    writes, callbacks, names, boundaries = [], [], [], []
    for reg, value in ((UC_ARM_REG_R0, r0), (UC_ARM_REG_R1, r1), (UC_ARM_REG_R2, r2),
                       (UC_ARM_REG_SP, STACK), (UC_ARM_REG_LR, FINISH)):
        machine.reg_write(reg, value)

    def instruction(_, address, size, __):
        a0, a1, a2 = [machine.reg_read(r) for r in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2)]
        if address in callback_targets:
            index, receiver = callback_targets[address]
            assert a0 == receiver
            slot = OBSERVER_SEAMS[method]
            if slot == 0:
                value, state = normalized(get(RECEIVER + FOCUS_OFFSET)), 0
            elif slot == 7:
                value, state = a1, get(RECEIVER + FLAG_OFFSET)
            else:
                value, state = normalized(a1), a2 if slot == 4 else 0
            callbacks.append([slot, index, value, state])
        elif provider and address == provider['address']:
            boundaries.append([address, a0, a1])
            if method in NAMED_METHODS:
                assert a0 == RECEIVER
                names.append(original_string(a1))
                machine.reg_write(UC_ARM_REG_R0, POINTERS[max(0, init - 1)])
            elif method in LOOP_METHODS:
                assert a0 == RECEIVER + 0x28 and a1 == LOOP_METHODS.index(method)
                machine.reg_write(UC_ARM_REG_R0, POINTERS[init == 2])
            elif method == 'optimize':
                for index in range(5):
                    pointer = original_word(a0 + index * 4)
                    if pointer == 0:
                        break
                    names.append(original_string(pointer))
                else:
                    raise AssertionError('No native list terminator')
            else:
                assert method == 'setDAWProgress' and a0 == RECEIVER

    def write(_, __, address, size, value, ___):
        if STACK - 128 <= address and address + size <= STACK:
            return
        writes.append([address, size, value & ((1 << (size * 8)) - 1)])

    machine.hook_add(UC_HOOK_CODE, instruction)
    machine.hook_add(UC_HOOK_MEM_WRITE, write)
    machine.emu_start(original['address'], FINISH, count=500)
    assert machine.reg_read(UC_ARM_REG_PC) == FINISH
    assert machine.reg_read(UC_ARM_REG_SP) == STACK

    after = bytearray(before)
    for address, size, value in writes:
        assert size == 4
        if address == factory_address:
            assert method == 'setTimeInfoFactory'
            continue
        offset = address - RECEIVER
        assert offset == {
            'setFocusChannel': FOCUS_OFFSET, 'setDialogHandler': HANDLER_OFFSET,
            'setDAWProgress': FLAG_OFFSET,
        }.get(method)
        after[offset:offset+size] = value.to_bytes(size, 'little')
    assert bytes(after) == machine.mem_read(RECEIVER, 0x700)
    assert machine.mem_read(RECEIVER + OBS_ARRAY, 8) == before[OBS_ARRAY:OBS_ARRAY + 8]
    if factory_address:
        assert get(factory_address - 4) == get(factory_address + 4) == 0xacacacac
    result = machine.reg_read(UC_ARM_REG_R0)
    if method not in RETURN_METHODS:
        result = 0
    elif method == 'castTo':
        assert result in (0, RECEIVER)
        result = int(result == RECEIVER)
    elif method != 'isDAWProgressMode':
        result = normalized(result)
    output = [result, normalized(get(RECEIVER + FOCUS_OFFSET)), get(RECEIVER + FLAG_OFFSET),
              normalized(get(RECEIVER + HANDLER_OFFSET)),
              normalized(get(factory_address)) if factory_address else 1]
    lines = [' '.join(map(str, output))]
    lines.extend(' '.join(map(str, call)) for call in callbacks)
    if method == 'optimize':
        lines = names + lines
    else:
        lines.extend(names)
    return dict(inputs=list(inputs), writes=writes, observer_callbacks=callbacks,
                provider_boundaries=boundaries, names=names, comparable_output=lines)


def observe(task):
    packet = json.loads(packet_path(task).read_text())
    method = packet_method(packet)
    observations = []
    for row in packet['originals']:
        original = row['original']
        data, elf = image(original['elf_path'], original['elf'])
        exact = symbol_range(data, elf, original['mangled'])
        for name, value in exact.items():
            assert original[name] == value, (original['role'], name)
        provider_name = {'setDAWProgress': SEND_MESSAGE, 'optimize': CCL_OPTIMIZE,
                         **dict.fromkeys(LOOP_METHODS, CCL_BY_TAG),
                         **dict.fromkeys(NAMED_METHODS, CCL_FIND_CHILD)}.get(method)
        provider = symbol_range(data, elf, provider_name) if provider_name else None
        vtable = None
        if method in NAMED_METHODS or method == 'castTo':
            vtable = symbol_range(data, elf, DAW_VTABLE, 'STT_OBJECT')
            slot_offset = 0 if method == 'castTo' else 0x14
            entry = struct.unpack_from('<I', bytes.fromhex(vtable['range_hex']), 8 + slot_offset)[0]
            assert entry == (original['address'] if method == 'castTo' else provider['address'])
        if provider and method not in NAMED_METHODS:
            # These methods use a tail branch as their last nonliteral word.
            pc = original['address'] + original['size'] - (8 if method == 'optimize' else 4)
            word = struct.unpack_from('<I', bytes.fromhex(original['range_hex']),
                                      pc-original['address'])[0]
            assert word >> 24 == 0xea
            displacement = (word & 0xffffff) << 2
            if displacement & (1 << 25):
                displacement -= 1 << 26
            assert pc + 8 + displacement == provider['address']
        observations.append(dict(original=original, provider=provider, vtable=vtable,
                                 cases=[execute(data, elf, method, original, provider, case)
                                        for case in cases(method)]))
    return dict(task=task, method=method, observations=observations)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('task')
    args = parser.parse_args()
    print(json.dumps(observe(args.task), indent=2))
