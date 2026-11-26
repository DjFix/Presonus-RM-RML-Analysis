"""Run the exact original init bodies and their native component and parameter providers."""
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
from struct import pack, unpack
import sys

from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_LR as LR, UC_ARM_REG_PC as PC
from unicorn.arm_const import UC_ARM_REG_R0 as R0, UC_ARM_REG_R1 as R1
from unicorn.arm_const import UC_ARM_REG_R2 as R2, UC_ARM_REG_R3 as R3

PROVIDER_MACHINE = Path('uc-library/tests/recovery/sqlite04_daw_045d71117e05/native.py')
SPEC = importlib.util.spec_from_file_location('daw_init_arm_machine', PROVIDER_MACHINE)
provider = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = provider
SPEC.loader.exec_module(provider)

CHANNEL = '10DAWChannel'
NUMERIC_CTOR = '_ZN4Core8Portable12NumericParamC1ERKNS0_9ParamInfoEb'
NUMERIC_VTABLE = '_ZTVN4Core8Portable12NumericParamE'
LIST_CTOR = '_ZN4Core8Portable9ListParamC1ERKNS0_9ParamInfoEb'
LIST_VTABLE = '_ZTVN4Core8Portable9ListParamE'
MIN = '_ZN4Core8Portable12NumericParam6setMinEf'
MAX = '_ZN4Core8Portable12NumericParam6setMaxEf'
REMOVE_HELPER = '_ZL11removeParamRN4Core8Portable9ParamListEi'
REMOVE = '_ZN4Core8Portable9ParamList6removeEPNS0_9ParameterE'
ADD = '_ZN4Core8Portable9ParamList3addEPKNS0_9ParamInfoEib'
ADD_DATA = '_ZL28DAWChannelParamListExtension'
GAIN = '_ZN8Presonus3Dsp15GainDBFormatterC1Eb'
GAIN_VTABLE = '_ZTVN8Presonus3Dsp15GainDBFormatterE'
GAIN_DTOR = '_ZN8Presonus3Dsp15GainDBFormatterD1Ev'
PROFILE_TAGS = {
    'full': (0, 5, 6, 8, 9, 18, 21, 22, 23, 91),
    'partial': (5, 6, 21, 23, 91),
    'empty': (),
}
FOLDERS = {'full': 2, 'partial': 1, 'empty': 0}
FEEDBACK_ORDER = (0, 22, 18, 5, 6, 23)
REMOVAL_ORDER = (8, 9, 5, 21, 18)
CAPACITY = 24
SERVER_COPY = 'rootfs/RML16AI_Rack_13731/home/root/mixer'


def hash_bytes(data):
    return sha256(data).hexdigest()


def symbol_binding(machine, name):
    elf, syms, _, _ = provider.read_elf(machine.elf_path)
    symbol = syms[name]
    section = elf.get_section(symbol['st_shndx'])
    delta = symbol['st_value'] - section['sh_addr']
    size = symbol['st_size']
    assert size and 0 <= delta <= section['sh_size'] - size
    data = section.data()[delta:delta + size]
    return dict(name=name, address=symbol['st_value'], size=size, section=symbol['st_shndx'],
                file_offset=section['sh_offset'] + delta, sha256=hash_bytes(data)), data


def line(*items):
    return ':'.join(str(item) for item in items)


def decode_descriptor(raw):
    typ, tag, name, lo, hi, mid, default, delta, flags, *pointers = unpack('<ii32s5fi5I', raw)
    assert pointers == [0] * 5
    return [typ, tag, name.split(b'\0', 1)[0].decode('ascii'), int(lo), int(hi),
            int(mid), int(default), int(delta), flags]


class InitMachine(provider.Machine):
    def __init__(self, original):
        super().__init__(original)
        self.elf_path = original['elf_path']
        _, _, imports, _ = provider.read_elf(self.elf_path)
        self.ext, self.raw = symbol_binding(self, ADD_DATA)
        assert len(self.raw) == 252
        self.descriptors = [decode_descriptor(self.raw[i:i + 84]) for i in range(0, 252, 84)]
        self.next_page = 0x53000000
        self.context = None
        self.guard = None
        self.gain_address = None
        self.edges = {self.address(name): name for name in (
            REMOVE_HELPER, REMOVE, ADD, GAIN, MIN, MAX, provider.INIT_FOLDER
        )}
        self.boundaries = {imports[name]: name for name in (
            '_Znwj', 'memcpy', '__cxa_guard_acquire', '__cxa_guard_release', '__aeabi_atexit',
        )}
        for address in self.edges:
            self.uc.hook_add(UC_HOOK_CODE, self.observe, begin=address, end=address)
        for address in self.boundaries:
            self.uc.hook_add(UC_HOOK_CODE, self.runtime, begin=address, end=address)
        for name in (NUMERIC_VTABLE, LIST_VTABLE):
            vtable = self.address(name) + 8
            assert self.load(vtable + 0x4c) == self.address(MIN)
            assert self.load(vtable + 0x50) == self.address(MAX)

    def allocate(self, size):
        assert 0 < size <= 0x1000
        address = self.next_page
        self.next_page += 0x1000
        self.uc.mem_map(address, 0x1000)
        self.allocations[address] = provider.Allocation(0x1000)
        return address

    def runtime(self, uc, address, _size, _data):
        name = self.boundaries[address]
        a, b, c = [uc.reg_read(reg) for reg in (R0, R1, R2)]
        if name == '_Znwj':
            uc.reg_write(R0, self.allocate(a))
        elif name == 'memcpy':
            uc.mem_write(a, bytes(uc.mem_read(b, c)))
        elif name == '__cxa_guard_acquire':
            assert self.guard is None and self.load(a) & 1 == 0
            self.guard = a
            self.events.append(['guard_acquire', a])
            uc.reg_write(R0, 1)
        elif name == '__cxa_guard_release':
            assert a == self.guard and self.gain_address is not None
            self.store(a, 1)
            self.events.append(['guard_release', a])
        else:
            assert name == '__aeabi_atexit' and a == self.gain_address
            assert b == self.address(GAIN_DTOR) and c != 0
            self.events.append(['atexit', a, b, c])
            uc.reg_write(R0, 0)
        uc.reg_write(PC, uc.reg_read(LR))

    def observe(self, uc, address, _size, _data):
        name = self.edges[address]
        a, b, c, d = [uc.reg_read(reg) for reg in (R0, R1, R2, R3)]
        if name in (REMOVE_HELPER, REMOVE, ADD):
            assert a == self.context['receiver'] + 0x28
        if name == ADD:
            assert (b, c, d) == (self.ext['address'], 3, 0)
            assert bytes(uc.mem_read(b, 252)) == self.raw
            event = [name, a, b, c, d]
        elif name in (REMOVE_HELPER, REMOVE, MIN, MAX):
            event = [name, a, b]
        elif name == GAIN:
            assert self.gain_address is None and b == 1
            self.gain_address = a
            event = [name, a, b]
        else:
            assert name == provider.INIT_FOLDER
            event = [name, a]
        self.events.append(event)

    def feedback(self, parameter):
        return int(bool(self.load(parameter + 4) & 8))

    def construct_parameter(self, tag, name, value=0, list_parameter=False):
        parameter = self.allocate(0x100)
        info = self.allocate(84)
        minimum, maximum, strings = -2, 3, 0
        if list_parameter:
            minimum, strings = 0, self.allocate(0x100)
            for index, label in enumerate((b'zero', b'one', b'two', b'three')):
                at = strings + 0x40 + index * 0x20
                self.uc.mem_write(at, label + b'\0')
                self.store(strings + 4 * index, at)
        raw = pack('<ii32s5fi5I', 2 if list_parameter else 3, tag,
                   name.encode('ascii'), minimum, maximum, 0, value, 0, 0,
                   0, 0, strings, 0, 0)
        self.uc.mem_write(info, raw)
        self.uc.reg_write(R2, 0)
        self.invoke(LIST_CTOR if list_parameter else NUMERIC_CTOR, parameter, info)
        return parameter

    def parameter_list(self, receiver, params):
        array = self.allocate(CAPACITY * 4)
        self.parameters(receiver, params, array)
        self.store(receiver + 0x34, array)
        self.store(receiver + 0x3c, CAPACITY)
        self.store(receiver + 0x40, CAPACITY)

    def case(self, profile, remove_controls, original):
        receiver = self.allocate(0x94)
        self.construct(CHANNEL, receiver)
        params = {}
        for tag in PROFILE_TAGS[profile]:
            list_parameter = profile == 'partial' and tag == 21
            params[tag] = self.construct_parameter(tag, f'tag-{tag}',
                                                   2 if list_parameter else .5,
                                                   list_parameter)
        self.parameter_list(receiver, list(params.values()))
        stale = self.allocate(0x34)
        for offset in (0x84, 0x88, 0x8c):
            self.store(receiver + offset, stale)

        children = []
        folders = []
        if profile != 'empty':
            foreign = self.allocate(0x84)
            self.construct(None, foreign)
            parameter = self.construct_parameter(0, 'foreign')
            self.parameter_list(foreign, [parameter])
            children.append(foreign)
        for index in range(FOLDERS[profile]):
            folder, slot = self.allocate(0x88), self.allocate(0x88)
            self.construct(provider.FOLDER, folder)
            self.construct(provider.SLOT, slot)
            count = self.construct_parameter(0, 'count', 1)
            edit = self.construct_parameter(7, 'edit')
            self.parameter_list(folder, [count])
            self.parameter_list(slot, [edit])
            self.children(folder, [slot])
            children.insert(index * 2, folder)
            folders.append((folder, slot, count, edit))
        self.children(receiver, children)
        self.context = {'receiver': receiver}
        self.events.clear()
        self.invoke(original['mangled'], receiver, int(remove_controls))
        events = self.events.copy()

        removed = [tag for tag in REMOVAL_ORDER if tag in params] if remove_controls else []
        assert [event[2] for event in events if event[0] == REMOVE_HELPER] == (
            list(REMOVAL_ORDER) if remove_controls else [])
        assert [event[2] for event in events if event[0] == REMOVE] == [params[t] for t in removed]
        assert [event[1] for event in events if event[0] == '_ZdlPv'] == [params[t] for t in removed]
        assert all(not self.allocations[params[t]].live for t in removed)
        live = {tag: ptr for tag, ptr in params.items() if tag not in removed}
        assert [event[2] for event in events if event[0] == provider.BY_TAG
                and event[1] == receiver + 0x28] == (
            (list(REMOVAL_ORDER) if remove_controls else []) + [8, *FEEDBACK_ORDER, 21])
        expected_feedback = [live[t] for t in FEEDBACK_ORDER if t in live]
        for _, _, count, edit in folders:
            expected_feedback.extend((count, edit))
        assert [event[1] for event in events if event[0] == provider.FEEDBACK] == expected_feedback
        assert all(event[2] == 1 for event in events if event[0] == provider.FEEDBACK)
        assert [event[1] for event in events if event[0] == provider.INIT_FOLDER] == [f[0] for f in folders]
        assert [event[1] for event in events if event[0] == provider.INIT_SLOT] == [f[1] for f in folders]
        assert [event[1:] for event in events if event[0] in (MIN, MAX)] == (
            [[live[21], 0], [live[21], 0x3f800000]] if 21 in live else [])
        assert sum(event[0] == ADD for event in events) == 1

        ptr_array = self.load(receiver + 0x34)
        stored = self.load(receiver + 0x38)
        addresses = [self.load(ptr_array + index * 4) for index in range(stored)]
        assert addresses[:-3] == list(live.values())
        lines = [line('removed', *removed), line('present', *live)]
        cached = [self.load(receiver + offset) for offset in (0x84, 0x88, 0x8c)]
        assert cached == [live.get(tag, 0) for tag in (6, 0, 22)]
        lines.append(line('caches', *[('null' if not ptr else self.load(self.load(ptr + 0xc) + 4))
                                      for ptr in cached]))
        lines.append(line('feedback', *[tag for tag, ptr in live.items() if self.feedback(ptr)]))
        if 8 in live:
            formatter = self.load(live[8] + 0x10)
            assert formatter == self.gain_address
            assert self.load(formatter) == self.address(GAIN_VTABLE) + 8
            assert self.uc.mem_read(formatter + 8, 1) == b'\1'
            lines.append(line('gain', self.string(self.load(formatter + 4))))
        else:
            lines.append('gain:null')
        if 21 in live:
            info = self.load(live[21] + 0xc)
            minimum, maximum = unpack('<ff', self.uc.mem_read(info + 0x28, 8))
            value, = unpack('<f', self.uc.mem_read(live[21] + 0x2c, 4))
            assert (minimum, maximum, value) == (0, 1, 1 if profile == 'partial' else .5)
            lines.append(line('range', int(minimum), int(maximum), format(value, 'g')))
        else:
            lines.append('range:null')
        for index, pointer in enumerate(addresses[-3:]):
            info = self.load(pointer + 0xc)
            assert info == self.ext['address'] + index * 84
            assert self.load(pointer + 4) & 1 == 0
            data = bytes(self.uc.mem_read(info, 84))
            assert decode_descriptor(data) == self.descriptors[index]
            lines.append(line('extension', *decode_descriptor(data), 0))
        for folder, slot, count, edit in folders:
            assert self.load(folder + 0x84) == count and self.load(slot + 0x84) == edit
            lines.append(line('folder', self.feedback(count), self.feedback(edit)))
        if profile != 'empty':
            assert not self.feedback(parameter)
        return dict(profile=profile, remove_controls=remove_controls,
                    receiver=receiver, events=events, normalized=lines)


def run(packet):
    results = []
    for context in json.loads(packet.read_text())['originals']:
        original = context['original']
        selected_path = original['elf_path']
        if original['role'] == 'server' and not Path(selected_path).is_file():
            selected_path = SERVER_COPY
        actual = {**original, 'elf_path': selected_path}
        provider.check_range(actual)
        machine = InitMachine(actual)
        cases = [machine.case(profile, remove, actual) for profile in PROFILE_TAGS for remove in (False, True)]
        assert sum(event[0] == GAIN for case in cases for event in case['events']) == 1
        assert sum(event[0] == 'guard_acquire' for case in cases for event in case['events']) == 1
        ranges = [symbol_binding(machine, n)[0] for n in (
            REMOVE_HELPER, REMOVE, ADD, GAIN, MIN, MAX, NUMERIC_VTABLE, LIST_VTABLE,
            provider.INIT_FOLDER, provider.INIT_SLOT
        )]
        results.append(dict(original=original, extension=machine.ext, extension_hex=machine.raw.hex(),
                            provider_ranges=ranges, cases=cases))
    return results


if __name__ == '__main__':
    print(json.dumps(run(Path(sys.argv[1])), indent=2))
