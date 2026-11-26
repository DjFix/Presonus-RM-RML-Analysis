"""Execute both retained DAWChannel getType ranges and actual ARM StringParam conversions."""
import importlib.util
import json
from pathlib import Path
from struct import pack, unpack
import sys

from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_LR as LR, UC_ARM_REG_PC as PC
from unicorn.arm_const import UC_ARM_REG_R0 as R0, UC_ARM_REG_R1 as R1, UC_ARM_REG_R2 as R2

BASE = Path('uc-library/tests/recovery/sqlite04_daw_045d71117e05/native.py')
spec = importlib.util.spec_from_file_location('daw_get_type_machine', BASE)
oracle = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = oracle
spec.loader.exec_module(oracle)

SEL = Path('temp/recovery-work/rolling-c001-20261124/selection/sqlite-cycle04/daw-classes')
SNAPSHOT = SEL / 'DAW_CLASS_NATIVE_SNAPSHOT.json'
GET_TYPE = '_ZNK8Presonus10DAWChannel7getTypeEv'
GET_ID = '_ZNK8Presonus10DAWChannel5getIDEv'
CTOR = '_ZN4Core8Portable11StringParamC1ERKNS0_9ParamInfoEb'
FROM_STRING = '_ZN4Core8Portable11StringParam10fromStringEPKcb'
TO_STRING = '_ZNK4Core8Portable11StringParam8toStringEPci'
STRING_VTABLE = '_ZTVN4Core8Portable11StringParamE'


def exact(fact):
    c, n = fact['catalog'], fact['native']
    row = {key: c[key] for key in ('elf', 'anchor', 'role', 'firmware', 'mangled', 'address', 'size')}
    row.update(elf_path=n['elf_path'], section=n['section_index'], section_name=n['section_name'],
               file_offset=n['file_offset'], range_sha256=n['range_sha256'], range_hex=n['hex'])
    oracle.check_range(row)
    return row


def execute(original, id_original):
    m = oracle.Machine(original)

    def read_cstring(address):
        text = bytearray()
        for offset in range(256):
            value = m.uc.mem_read(address + offset, 1)[0]
            if value == 0:
                return text.decode('ascii')
            text.append(value)
        raise AssertionError('unterminated fixture string')

    m.string = read_cstring
    elf, symbols, plt, _ = oracle.read_elf(original['elf_path'])
    guard, buffer = unpack('<II', bytes.fromhex(original['range_hex'])[-8:])
    id_guard, id_buffer = unpack('<II', bytes.fromhex(id_original['range_hex'])[-8:])
    data_symbols = []
    for mangled, address, size in (
        ('_ZZNK8Presonus10DAWChannel7getTypeEvE4type', buffer, 32),
        ('_ZGVZNK8Presonus10DAWChannel7getTypeEvE4type', guard, 4),
    ):
        sym = symbols[mangled]
        section = elf.get_section(sym['st_shndx'])
        assert (sym['st_value'], sym['st_size'], section['sh_type']) == (address, size, 'SHT_NOBITS')
        data_symbols.append(dict(mangled=mangled, address=address, size=size, section=sym['st_shndx'],
                                 section_name=section.name, zero_initialized=True))
    assert buffer != id_buffer and max(buffer, id_buffer) >= min(buffer + 32, id_buffer + 64)
    assert m.load(m.address(STRING_VTABLE) + 8 + 0x70) == m.address(TO_STRING)

    strings = plt['strncpy']
    acquire, release = plt['__cxa_guard_acquire'], plt['__cxa_guard_release']
    calls = []

    def shim(uc, address, _size, _data):
        a, b, c = [uc.reg_read(reg) for reg in (R0, R1, R2)]
        if address == strings:
            assert c <= 255
            data = bytes(uc.mem_read(b, c))
            if b'\0' in data:
                data = data.split(b'\0', 1)[0].ljust(c, b'\0')
            uc.mem_write(a, data)
        elif address == acquire:
            assert a in (guard, id_guard) and m.load(a) == 0
            calls.append(['acquire', a])
            uc.reg_write(R0, 1)
        else:
            assert address == release and a in (guard, id_guard)
            assert uc.mem_read(buffer if a == guard else id_buffer, 1) == b'\0'
            calls.append(['release', a])
            m.store(a, 1)
        uc.reg_write(PC, uc.reg_read(LR))

    for address in (strings, acquire, release):
        m.uc.hook_add(UC_HOOK_CODE, shim, begin=address, end=address)

    def formatting(uc, _address, _size, _data):
        calls.append(['StringParam::toString', *[uc.reg_read(reg) for reg in (R0, R1, R2)]])

    function = m.address(TO_STRING)
    m.uc.hook_add(UC_HOOK_CODE, formatting, begin=function, end=function)

    first, second = oracle.RECEIVER, oracle.PARENT
    m.construct('10DAWChannel', first)
    m.construct('10DAWChannel', second)

    def string_parameter(at, tag, text):
        info, source = at + 0x200, at + 0x300
        raw = pack('<ii32s5fi5I', 4, tag, b'fixture', 0, 0, 0, 0, 0, 0, *[0] * 5)
        m.uc.mem_write(info, raw)
        m.uc.reg_write(R2, 0)
        m.invoke(CTOR, at, info)
        m.uc.mem_write(source, text.encode('ascii') + b'\0')
        m.invoke(FROM_STRING, at, source)

    parm1, parm2, id_param = oracle.PARAMETERS, oracle.PARAMETERS + 0x400, oracle.PARAMETERS + 0x800
    string_parameter(id_param, 22, 'separate-id')
    m.store(first + 0x8c, id_param)
    assert m.invoke(GET_ID, first) == id_buffer and m.string(id_buffer) == 'separate-id'
    id_bytes = bytes(m.uc.mem_read(id_buffer, 64))
    cases = []
    for receiver, parm, text in (
        (first, 0, None), (first, parm1, ''), (first, parm1, 'input'),
        (second, parm2, 'A' * 31), (second, parm2, 'B' * 32),
        (first, parm1, 'C' * 80), (second, parm2, 'x'), (second, 0, None),
    ):
        if parm:
            string_parameter(parm, 0, text)
        m.store(receiver + 0x88, parm)
        calls.clear()
        before = bytes(m.uc.mem_read(buffer, 48))
        result = m.invoke(GET_TYPE, receiver)
        after = bytes(m.uc.mem_read(buffer, 48))
        assert after[32:] == before[32:]
        if text is None:
            assert result == 0 and not calls and after == before
        else:
            assert result == buffer and calls[-1] == ['StringParam::toString', parm, buffer, 32]
            assert after[:32].split(b'\0', 1)[0].decode('ascii') == text[:31]
            assert after[min(len(text), 31)] == 0
            assert len(calls) == (3 if text == '' else 1)
            if text == '':
                assert calls[:2] == [['acquire', guard], ['release', guard]]
        assert bytes(m.uc.mem_read(id_buffer, 64)) == id_bytes
        cases.append(dict(input=text, receiver=receiver, parameter=parm, result=result,
                          calls=list(calls), first32_hex=after[:32].hex()))
    return dict(original=original, comparison_get_id=id_original, buffer=buffer, guard=guard,
                id_buffer=id_buffer, static_symbols=data_symbols,
                original_formatter=dict(mangled=TO_STRING, address=function), cases=cases)


def run(packet):
    context = json.loads(Path(packet).read_text())
    snapshot = json.loads(SNAPSHOT.read_text())
    ids = [exact(fact) for fact in snapshot['facts'] if fact['catalog']['mangled'] == GET_ID]
    return [execute(entry['original'], next(row for row in ids if row['elf'] == entry['original']['elf']))
            for entry in context['originals']]

if __name__ == '__main__':
    print(json.dumps(run(sys.argv[1]), indent=2))
