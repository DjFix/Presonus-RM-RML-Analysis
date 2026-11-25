"""Execute the sealed ARM application methods with bounded provider inputs."""
import hashlib
from io import BytesIO
import json
from pathlib import Path
import struct

from elftools.elf.elffile import ELFFile
import unicorn
from unicorn.arm_const import (UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0,
                               UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_SP)

TASK = Path(__file__).parent.name
PACKET = Path('temp/recovery-work/sqlite-issued/packet') / TASK / 'CONTEXT.json'
ROOT = Path('/home/rs/projects/opencs/ai-line-analysis')
AUTO_SCROLL = TASK.endswith('calcautoscroll')
CLASS = '8Presonus7Surface18DawFxPageComponent'
EDIT_INDEX = '_ZNK' + CLASS + '16getEditSlotIndexEPNS_15DAWDeviceFolderE'
OFFSET = '_ZNK' + CLASS + '13getListOffsetEv'
SEND = '_ZNK' + CLASS + '10isSendModeEv'
USED = '_ZNK8Presonus15DAWDeviceFolder12getUsedCountEv'
GET_TAG = '_ZNK4Core8Portable9Component17getParameterByTagEi'
FOLDER, PAGE, ROSTER = 0x20000000, 0x20001000, 0x20002000
CHILD, PARAM, VTABLE = 0x20003000, 0x20005000, 0x20007000
VALUE, STACK, EXIT = 0x20007800, 0x20009000, 0x2000A000
STEP = 0x100
ABSENT = -999


def sha(data):
    return hashlib.sha256(data).hexdigest()


def cases():
    def case(name='inserts', used=8, values=(ABSENT, -2, 0, 1, 3, 0, 4, 5),
             slot=None, send=0, offsets=(0, 5), folder=True):
        return dict(name=name, used=used, values=list(values), slot=slot,
                    send=send, offsets=list(offsets), folder=folder)

    yield case(folder=False)
    yield case(name='Inserts')
    yield case(name='sends')
    yield case(used=ABSENT)
    yield case(used=0)
    yield case(used=-1)
    yield case(used=3)
    yield case(used=4)
    yield case(used=19)
    yield case(values=(1, 2))
    yield case(values=())
    yield case(values=(ABSENT, -3, 0, -1))

    if AUTO_SCROLL:
        yield case(folder=False, slot=-1)
        yield case(slot=-1)
        yield case(slot=0, used=0)
        yield case(slot=7, used=1)
        yield case(slot=5, name='sends')
        yield case(send=1)
        yield case(send=-1, slot=4)
        yield case(send=ABSENT, slot=4)
        for send in (0, 1):
            for slot in (0, 1, 4, 5, 6, 7, 9, 10, 13):
                yield case(slot=slot, send=send, values=(0,) * 14)
        for offset in (-8, -4, 1, 3, 7, 2147483647, -2147483648):
            yield case(slot=6, offsets=(offset, 0))


def observe():
    target, = json.loads(PACKET.read_text())['originals']
    target = target['original']
    image = (ROOT / target['elf_path']).read_bytes()
    assert sha(image) == target['elf']
    elf = ELFFile(BytesIO(image))
    symtab = elf.get_section_by_name('.symtab')

    def checked_symbol(name):
        entry, = {(s['st_value'], s['st_size'], s['st_shndx'])
                  for s in symtab.get_symbol_by_name(name) if s['st_size']}
        address, size, section_id = entry
        section = elf.get_section(section_id)
        relative = address - section['sh_addr']
        assert 0 <= relative <= section['sh_size'] - size
        offset = section['sh_offset'] + relative
        return dict(mangled=name, address=address, size=size, section=section_id,
                    section_name=section.name, file_offset=offset,
                    range_sha256=sha(image[offset:offset + size]))

    body = checked_symbol(target['mangled'])
    assert all(target[key] == value for key, value in body.items())
    names = [target['mangled'], USED, '__aeabi_f2iz', '__aeabi_fcmpgt']
    if AUTO_SCROLL:
        names += [EDIT_INDEX, OFFSET, SEND]
    verified = {name: checked_symbol(name) for name in names}
    # Core provider execution is scoped to input/return capture at its entry.
    tag_address = symtab.get_symbol_by_name(GET_TAG)[0]['st_value']
    strcmp_address = 0xb0f8

    def run(inputs):
        model = unicorn.Uc(unicorn.UC_ARCH_ARM, unicorn.UC_MODE_ARM)
        loads = [s for s in elf.iter_segments() if s['p_type'] == 'PT_LOAD']
        low = min(s['p_vaddr'] for s in loads) & ~0xfff
        high = (max(s['p_vaddr'] + s['p_memsz'] for s in loads) + 0xfff) & ~0xfff
        model.mem_map(low, high - low)
        for segment in loads:
            model.mem_write(segment['p_vaddr'], segment.data())
        model.mem_map(FOLDER, 0xB000)

        def store(address, value):
            model.mem_write(address, struct.pack('<I', value & 0xffffffff))

        def parameter(address, value):
            store(address, VTABLE)
            parameter_values[address] = value

        parameter_values, tags = {}, {}
        store(VTABLE + 0x44, VALUE)
        model.mem_write(FOLDER + 8, inputs['name'].encode() + b'\0')
        store(FOLDER + 0x58, ROSTER)
        store(FOLDER + 0x5C, len(inputs['values']))
        if inputs['used'] != ABSENT:
            store(FOLDER + 0x84, PARAM)
            parameter(PARAM, inputs['used'])
        for index, value in enumerate(inputs['values']):
            child = CHILD + index * STEP
            store(ROSTER + index * 4, child)
            if value != ABSENT:
                address = PARAM + (index + 1) * STEP
                parameter(address, value / 2)
                tags[child] = address
        if inputs['send'] != ABSENT:
            store(PAGE + 0xC0, PARAM + 0x1800)
            parameter(PARAM + 0x1800, inputs['send'])
        store(PAGE + 0xC4, inputs['offsets'][0])
        store(PAGE + 0xC8, inputs['offsets'][1])
        slot = inputs['slot']
        model.reg_write(UC_ARM_REG_R0, PAGE)
        model.reg_write(UC_ARM_REG_R1, FOLDER if inputs['folder'] else 0)
        model.reg_write(UC_ARM_REG_R2, 0 if slot is None else CHILD + slot * STEP)
        model.reg_write(UC_ARM_REG_SP, STACK)
        model.reg_write(UC_ARM_REG_LR, EXIT)
        writes, calls, instructions = [], [], []
        entry_names = {v['address']: k for k, v in verified.items()}

        def write(_, _access, where, width, value, _context):
            if not STACK - 0x1000 <= where <= STACK - width:
                writes.append([where, width, value])

        def c_string(address):
            result = bytearray()
            while byte := model.mem_read(address + len(result), 1)[0]:
                result.append(byte)
            return result

        def code(_, pc, _width, _context):
            arg0 = model.reg_read(UC_ARM_REG_R0)
            arg1 = model.reg_read(UC_ARM_REG_R1)
            instructions.append(pc)
            if pc == strcmp_address:
                assert arg0 == FOLDER + 8
                left, right = c_string(arg0), c_string(arg1)
                result = (left > right) - (left < right)
                calls.append(['strcmp', left.decode(), right.decode(), result])
            elif pc == tag_address:
                assert (arg0 - CHILD) % STEP == 0 and arg1 == 1
                index = (arg0 - CHILD) // STEP
                assert 0 <= index < len(inputs['values'])
                result = tags.get(arg0, 0)
                calls.append(['getParameterByTag', index, arg1, bool(result)])
            elif pc == VALUE:
                value = parameter_values[arg0]
                result, = struct.unpack('<I', struct.pack('<f', value))
                calls.append(['getValue', arg0, result])
            else:
                if pc in entry_names:
                    calls.append([entry_names[pc], arg0, arg1])
                assert low <= pc < high
                return
            model.reg_write(UC_ARM_REG_R0, result & 0xffffffff)
            model.reg_write(UC_ARM_REG_PC, model.reg_read(UC_ARM_REG_LR))

        model.hook_add(unicorn.UC_HOOK_MEM_WRITE, write)
        model.hook_add(unicorn.UC_HOOK_CODE, code)
        model.emu_start(body['address'], EXIT, count=8192)
        assert model.reg_read(UC_ARM_REG_PC) == EXIT
        assert model.reg_read(UC_ARM_REG_SP) == STACK and not writes
        result, = struct.unpack('<i', struct.pack('<I', model.reg_read(UC_ARM_REG_R0)))
        return dict(inputs=inputs, result=result, calls=calls, writes=writes,
                    instruction_count=len(instructions))

    original = dict(body, elf_sha256=target['elf'], firmware=target['firmware'],
                    role=target['role'])
    return dict(unicorn_version=unicorn.__version__, elf_path=target['elf_path'],
                provider_ranges=list(verified.values())[1:],
                modeled_entries=dict(strcmp=strcmp_address, get_tag=tag_address,
                                     parameter_get_value=VALUE),
                targets=[dict(original=original, cases=[run(i) for i in cases()])])
