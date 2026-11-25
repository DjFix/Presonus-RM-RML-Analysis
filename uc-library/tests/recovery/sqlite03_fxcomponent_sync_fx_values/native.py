"""Execute exact ARM sync, conversion, mapping and validity bodies offline."""
import hashlib
import json
import struct
import sys
from pathlib import Path

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UC_MODE_ARM
from unicorn.arm_const import (
    UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2,
    UC_ARM_REG_SP,
)

ROOT = Path(__file__).resolve().parents[4]
ELF = ROOT / 'rootfs/RML16AI_Rack_13731/home/root/mixer'
ELF_SHA = '9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
FX = '_ZN8Presonus5Mixer11FXComponent'
NAME = FX + '12syncFxValuesEv'
TARGET_SHA = '17aed01167fc7bd02750ac2731d52ca97d81eab9ff6e92002650060df39ff631'
METHODS = {
    'sync': NAME,
    'trunc': '__aeabi_f2iz',
    'effect': FX + '21getEffectTypeInternalENS_10EffectTypeE',
    'valid': FX + '19isValidParamForTypeENS_10EffectTypeEi',
    'base_ids': FX + '6mapIDsEi',
    'reverb_ids': '_ZN8Presonus5Mixer15ReverbComponent6mapIDsEi',
    'values': FX + '9mapValuesEPN4Core8Portable9ParameterE',
    'count': '_ZNK8Presonus3Dsp18SLReverbController16getNumParametersEv',
    'calc': '_ZN8Presonus3Dsp18SLReverbController10calcParamsEi',
    'compare': '__aeabi_fcmpeq',
    'set': '_ZN8Presonus3Dsp18SLReverbController8setValueEif',
}


def bits(value):
    return struct.unpack('<I', struct.pack('<f', value))[0]


def signed(value):
    return struct.unpack('<i', struct.pack('<I', value))[0]


def firmware():
    data = ELF.read_bytes()
    assert hashlib.sha256(data).hexdigest() == ELF_SHA
    methods = {}
    with ELF.open('rb') as stream:
        elf = ELFFile(stream)
        symtab = elf.get_section_by_name('.symtab')
        for label, name in METHODS.items():
            symbol, = symtab.get_symbol_by_name(name)
            section_index = symbol['st_shndx']
            section = elf.get_section(section_index)
            address, size = symbol['st_value'], symbol['st_size']
            offset = section['sh_offset'] + address - section['sh_addr']
            assert section.name == '.text' and offset + size <= section['sh_offset'] + section['sh_size']
            code = data[offset:offset + size]
            methods[label] = (dict(mangled=name, address=address, size=size,
                                   section=section.name, section_index=section_index,
                                   file_offset=offset, range_sha256=hashlib.sha256(code).hexdigest()), code)
        set_symbol, set_code = methods['set']
        address = struct.unpack_from('<I', set_code, 0xbf350 - set_symbol['address'])[0]
        section = elf.get_section_by_name('.rodata')
        offset = section['sh_offset'] + address - section['sh_addr']
        code = data[offset:offset + 44]
        assert address == 0x35e008 and offset == 3497992
        methods['preset_9'] = (dict(address=address, size=len(code), section=section.name,
                                    file_offset=offset, range_sha256=hashlib.sha256(code).hexdigest()), code)
    identity = methods['sync'][0]
    assert (identity['address'], identity['size'], identity['section_index'],
            identity['file_offset'], identity['range_sha256']) == (239856, 248, 12, 207088, TARGET_SHA)
    return methods


def oracle(methods, mode, type_bits, entries):
    u = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    memory, stack = 0x600000, 0x800000
    u.mem_map(memory, 0x10000)
    u.mem_map(stack, 0x1000)
    mapped = set()
    addresses = {}
    for label, (symbol, code) in methods.items():
        address = symbol['address']
        addresses[label] = address
        for page in range(address & ~0xfff, ((address + len(code) - 1) & ~0xfff) + 1, 0x1000):
            if page not in mapped:
                u.mem_map(page, 0x1000)
                mapped.add(page)
        u.mem_write(address, code)

    def write(address, *values):
        u.mem_write(address, struct.pack(f'<{len(values)}I', *(word & 0xffffffff for word in values)))

    fx, vtable, array = memory, memory + 0x200, memory + 0x400
    type_param, type_vtable = memory + 0x800, memory + 0x900
    params, metadata, param_vtable = memory + 0x1000, memory + 0x2000, memory + 0x3000
    controller, controller_vtable = memory + 0x4000, memory + 0x4200
    type_get, param_get, fixture_ids, fixture_effect, fixture_value, ret = range(
        memory + 0x5000, memory + 0x5018, 4)

    ids = (addresses['base_ids'], addresses['reverb_ids'], fixture_ids)[mode]
    effect = fixture_effect if mode == 2 else addresses['effect']
    values = fixture_value if mode == 2 else addresses['values']
    write(fx, vtable)
    write(fx + 0x34, array, len(entries))
    write(fx + 0x128, type_param)
    write(fx + 0xb0, controller)
    write(vtable + 0x4c, effect, ids, values)
    write(type_param, type_vtable)
    write(type_vtable + 0x44, type_get)
    write(param_vtable + 0x44, param_get)
    write(controller, controller_vtable)
    write(controller + 0x2c, 9)
    write(controller_vtable + 0xc, addresses['count'])
    write(controller_vtable + 0x14, addresses['set'])
    for index, (tag, _, _) in enumerate(entries):
        p, info = params + 0x20 * index, metadata + 0x20 * index
        write(array + 4 * index, p)
        write(p, param_vtable)
        write(p + 0xc, info)
        write(info + 4, tag)

    trace, sites = [], set()
    cursor = 0

    def result(uc, value):
        uc.reg_write(UC_ARM_REG_R0, value & 0xffffffff)
        uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))

    def hook(uc, pc, _size, _user):
        nonlocal cursor
        r0, r1, r2 = (uc.reg_read(reg) for reg in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2))
        sites.add(pc)
        if pc == type_get:
            assert r0 == type_param
            trace.append(['read-type'])
            result(uc, type_bits)
        elif pc == effect or pc == ids:
            assert r0 == fx
            if pc == effect:
                trace.append(['effect', signed(r1)])
                if mode == 2:
                    result(uc, 12)
            else:
                assert signed(r1) == entries[cursor][0]
                trace.append(['map', signed(r1)])
                if mode == 2:
                    result(uc, entries[cursor][2])
        elif pc in (param_get, fixture_value):
            index = ((r0 if pc == param_get else r1) - params) // 0x20
            assert index == cursor
            value_bits = entries[index][1]
            trace.append(['value', index])
            cursor += 1
            result(uc, value_bits if pc == param_get else value_bits ^ 0x80000000)
        elif pc == addresses['valid']:
            trace.append(['valid', signed(r1), signed(r2)])
        elif pc == addresses['set']:
            assert r0 == controller
            trace.append(['set', signed(r1), r2])
        elif pc == addresses['calc']:
            assert r0 == controller
            trace.append(['calc', signed(r1)])
            result(uc, 0)
        elif pc == addresses['compare']:
            left, right = struct.unpack('<ff', struct.pack('<II', r0, r1))
            result(uc, int(left == right))
        else:
            assert any(symbol['address'] <= pc < symbol['address'] + symbol['size']
                       for label, (symbol, _) in methods.items() if label != 'preset_9'), hex(pc)

    def memory_write(_uc, _access, address, size, _value, _user):
        assert (stack <= address and address + size <= stack + 0x1000
                or controller + 0x1c <= address and address + size <= controller + 0x80)

    u.hook_add(UC_HOOK_CODE, hook)
    u.hook_add(UC_HOOK_MEM_WRITE, memory_write)
    for reg, value in ((UC_ARM_REG_R0, fx), (UC_ARM_REG_LR, ret), (UC_ARM_REG_SP, stack + 0xf00)):
        u.reg_write(reg, value)
    u.emu_start(addresses['sync'], ret, count=5000)
    assert u.reg_read(UC_ARM_REG_PC) == ret and cursor == len(entries)
    dirty = u.mem_read(controller + 0x1c, 1)[0]
    state = list(struct.unpack('<21I', u.mem_read(controller + 0x2c, 84)))
    trace.append(['state', dirty, *state])
    return trace, sites


def generate():
    methods = firmware()
    all_tags = [11, 12, 9, 10, 13, 14, 15, 16, 2, -2, 0, 17]
    ordered = [(tag, bits(9.75 if tag == 2 else (i + 1) / 16), 0) for i, tag in enumerate(all_tags)]
    custom = [(17, bits(.25), 5), (15, bits(.5), 5), (16, bits(.75), 5),
              (-7, bits(.125), 7), (7, bits(.125), 0), (2, bits(.5), -1)]
    inputs = [(0, bits(4.), []), (0, bits(3.), ordered)]
    inputs += [(1, bits(i + .75), ordered) for i in range(13)]
    inputs += [(1, word, ordered) for word in
               (bits(-1.75), bits(13.), 0x7f800000, 0xff800000, 0x7fc00000,
                0x4f000000, 0xcf000000, 0x80000000)]
    inputs += [(2, bits(-1.75), custom), (2, bits(2.5), list(reversed(custom)))]
    cases, sites = [], set()
    for mode, word, entries in inputs:
        trace, executed = oracle(methods, mode, word, entries)
        sites.update(executed)
        cases.append(dict(mode=mode, type_bits=word, entries=[list(e) for e in entries],
                          trace=trace))
    return dict(elf_sha256=ELF_SHA, ranges={key: value[0] for key, value in methods.items()},
                cases=cases, executed_sites=sorted(sites))


if __name__ == '__main__':
    fixtures = generate()
    Path(sys.argv[1]).write_text(json.dumps(fixtures, indent=2) + '\n')
    print(f'{len(fixtures["cases"])} native ARM sync observations')
