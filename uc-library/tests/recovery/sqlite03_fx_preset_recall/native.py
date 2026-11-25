"""Execute original ARM recall and selector-6 with explicit provider boundaries."""
import hashlib
import json
from pathlib import Path
import struct

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import (
    UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3,
    UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC,
)

PACKET = Path('temp/recovery-work/sqlite-issued/packet/sqlite03_fx_preset_recall/CONTEXT.json')
FILTER = '_ZN8Presonus5Mixer14MixerComponent9getFilterENS0_18MixerComponentBase6FilterEPN4Core8Portable9ComponentE'
VTABLE = '_ZTVN8Presonus5Mixer18RackMixerComponentE'
FILTER_VTABLE = '_ZTVN8Presonus5Mixer14FxPresetFilterE'
CASES = [(0, 'missing'), (1, 'malformed'), (0, 'failure'),
         (0, 'success'), (1, 'success'), (1, 'move')]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def generate():
    context = json.loads(PACKET.read_text())
    original = context['originals'][0]['original']
    path = Path(original['elf_path'])
    with path.open('rb') as stream:
        elf = ELFFile(stream)
        assert digest(path.read_bytes()) == original['elf']
        symtab = elf.get_section_by_name('.symtab')

        def identity(name):
            sym, = symtab.get_symbol_by_name(name)
            section = elf.get_section(sym['st_shndx'])
            start, size = sym['st_value'], sym['st_size']
            offset = start - section['sh_addr']
            data = section.data()[offset:offset + size]
            return dict(mangled=name, address=start, size=size,
                        section_name=section.name, section=sym['st_shndx'],
                        file_offset=section['sh_offset'] + offset,
                        range_sha256=digest(data)), data

        target, data = identity(original['mangled'])
        assert all(original[key] == value for key, value in target.items())
        assert data.hex() == original['range_hex']
        selector, _ = identity(FILTER)
        mixer_table, _ = identity(VTABLE)
        filter_table, _ = identity(FILTER_VTABLE)
        segments = [(s['p_vaddr'], s.data()) for s in elf.iter_segments()
                    if s['p_type'] == 'PT_LOAD']

    executions = []
    for selected, scenario in CASES:
        uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        uc.mem_map(0x8000, 0x600000)
        for address, data in segments:
            uc.mem_write(address, data)
        obj, stack = 0x1000000, 0x9000000
        uc.mem_map(obj, 0x10000)
        uc.mem_map(stack, 0x10000)
        mixer, array, slot, loaded, eff0, eff1 = [obj + i * 0x1000 for i in range(1, 7)]
        slot_vt, loaded_vt, effect_vt = [obj + i * 0x100 for i in range(1, 4)]
        stop, read_slot, write_loaded, load_effect = [obj + i * 4 + 0xf000 for i in range(4)]
        def put(address, value):
            uc.mem_write(address, struct.pack('<I', value))
        def word(address):
            return struct.unpack('<I', uc.mem_read(address, 4))[0]
        for address, value in (
            (obj + 0xe4, mixer), (obj + 0xe0, selected),
            (mixer + 0x29c, array), (mixer + 0x2a0, 2),
            (mixer, mixer_table['address'] + 8), (array, eff0), (array + 4, eff1),
            (obj + 0xc8, slot), (obj + 0xd0, loaded),
            (slot, slot_vt), (slot_vt + 0x44, read_slot),
            (loaded, loaded_vt), (loaded_vt + 0x58, write_loaded),
            (eff0, effect_vt), (eff1, effect_vt), (effect_vt + 0x20, load_effect),
        ):
            put(address, value)
        assert word(word(mixer) + 0x80) == selector['address']
        assert word(0x2d2a4) == 0x2d388
        effect = (eff0, eff1)[selected]
        trace, api, writes, executed = [], [], [], []
        attributes = filename = filter_guard = None
        slot_index = 1
        loaded_value = 0

        def code(cpu, pc, size, _):
            nonlocal attributes, filename, filter_guard, loaded_value, slot_index
            if pc == stop:
                cpu.emu_stop()
                return
            r0, r1, r2, r3, sp = map(cpu.reg_read, (UC_ARM_REG_R0, UC_ARM_REG_R1,
                                                    UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_SP))
            result = 0
            if pc == 0x54818:
                assert r0 == obj
                result = slot_index
                trace.append(f'slot:{slot_index}')
            elif pc == 0x56030:
                assert (r0, r1) == (obj, slot_index)
                trace.append(f'path:{r1}')
                result = int(scenario == 'missing')
            elif pc == 0x121dbc:
                result = obj + 0x7100
                api.append(['allocator', result])
            elif pc == 0x121a68:
                assert r1 == obj + 0x7100
                attributes = r0
                api.append(['attributes', attributes])
            elif pc == 0x129ba4:
                assert r1 == 0
                filename = r0
                api.append(['filename', filename])
            elif pc == 0x55f84:
                assert (r0, r1, r2) == (obj, slot_index, filename)
                trace.append(f'path:{r1}')
            elif pc == 0x117fa8:
                assert (r0, r1, r2, r3, word(sp), word(sp + 4)) == (attributes, filename, 0, 0, 0, 0)
                trace.append('archive')
                api.append(['loadFromFile', r0, r1, r2, r3, word(sp), word(sp + 4)])
                result = int(scenario != 'malformed')
            elif pc == 0xb030:
                filter_guard = r0
                assert word(filter_guard) == 0
                result = 1
                api.append(['guardAcquire', r0])
            elif pc == 0xaa3c:
                assert r0 == filter_guard
                put(r0, 1)
                api.append(['guardRelease', r0])
            elif pc == 0x1debc:
                assert r1 == 0
                put(r0, 0)
                api.append(['emptyMode', r0])
            elif pc == load_effect:
                assert r0 == effect
                values = [word(r1 + offset) for offset in (0, 32, 36, 40, 44, 48)]
                _, filter_object, *rest = values
                assert rest == [0, 0, 0, attributes]
                assert values[0] == 0
                assert word(filter_object) == filter_table['address'] + 8
                trace.append(f'fx:{selected}')
                api.append(['storage', *values, word(filter_object)])
                if scenario == 'move':
                    slot_index = 2
                result = int(scenario != 'failure')
            elif pc == read_slot:
                assert r0 == slot
                result = struct.unpack('<I', struct.pack('<f', slot_index))[0]
                trace.append(f'live:{slot_index}')
            elif pc == write_loaded:
                assert r0 == loaded and r2 == 0
                loaded_value = int(struct.unpack('<f', struct.pack('<I', r1))[0])
                trace.append(f'loaded:{loaded_value}:{r2}')
            elif pc == 0x56148:
                assert r0 == obj
                trace.append(f'ui:{slot_index}')
            elif pc == 0x1228b0:
                assert r0 == attributes
                api.append(['destroyAttributes', r0])
            else:
                assert (target['address'] <= pc < 0x56400 or
                        selector['address'] <= pc < selector['address'] + selector['size']), hex(pc)
                if pc == selector['address']:
                    assert (r0, r1, r2) == (mixer, 6, 0)
                    api.append(['filterSelect', r0, r1, r2])
                executed.append(pc)
                return
            cpu.reg_write(UC_ARM_REG_R0, result)
            cpu.reg_write(UC_ARM_REG_PC, cpu.reg_read(UC_ARM_REG_LR))

        def write(_, access, address, size, value, data):
            writes.append([address, size, value])
            assert stack <= address < stack + 0x10000 or (
                filter_guard is not None and address < 0x600000)

        uc.hook_add(UC_HOOK_CODE, code)
        uc.hook_add(UC_HOOK_MEM_WRITE, write)
        for reg, value in ((UC_ARM_REG_R0, obj), (UC_ARM_REG_SP, stack + 0x8000),
                           (UC_ARM_REG_LR, stop)):
            uc.reg_write(reg, value)
        uc.emu_start(target['address'], stop + 0x20, count=400)
        assert uc.reg_read(UC_ARM_REG_PC) == stop, (scenario, hex(uc.reg_read(UC_ARM_REG_PC)), trace, executed[-5:])
        result = uc.reg_read(UC_ARM_REG_R0)
        assert result in (0, 1)
        if any(item.startswith('fx:') for item in trace):
            assert 0x2d388 in executed and 0x2d494 in executed
        executions.append(dict(argv=[str(selected), scenario], trace=trace, api=api,
                               writes=writes, executed=executed,
                               result=result, loaded=loaded_value))
    return dict(elf_path=str(path), elf_sha256=original['elf'],
                ranges=[target, selector, mixer_table, filter_table], cases=executions)


if __name__ == '__main__':
    print(json.dumps(generate(), indent=2))
