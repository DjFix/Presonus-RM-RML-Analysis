MODE = 'focus'
import hashlib
import json
from pathlib import Path
import struct
import sys

import unicorn
from elftools.elf.elffile import ELFFile
from unicorn import UC_ARCH_ARM, UC_HOOK_CODE, UC_MODE_ARM, Uc
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_R0, UC_ARM_REG_R1
from unicorn.arm_const import UC_ARM_REG_R2, UC_ARM_REG_PC, UC_ARM_REG_SP

root = Path(__file__).resolve().parents[4]
task = Path(__file__).resolve().parent.name
packet = root / 'temp/recovery-work/sqlite-issued/packet' / task / 'CONTEXT.json'
if not packet.exists():
    packet = next(root.glob(
        f'temp/recovery-work/rolling-c001-20261124/packeting/sqlite-cycle02/'
        f'assignment01/packet/**/{task}/CONTEXT.json'))
original = json.loads(packet.read_text())['originals'][0]['original']
firmware = next(parent / original['elf_path'] for parent in (root, *root.parents)
                if (parent / original['elf_path']).is_file())
elf_bytes = firmware.read_bytes()
assert hashlib.sha256(elf_bytes).hexdigest() == original['elf']
with firmware.open('rb') as stream:
    elf = ELFFile(stream)
    table = elf.get_section_by_name('.symtab')

    def symbol(name):
        return table.get_symbol_by_name(name)[0].entry

    section = elf.get_section(original['section'])
    entry = symbol(original['mangled'])
    address = original['address']
    assert entry.st_value == address and entry.st_size == original['size']
    assert entry.st_shndx == original['section'] and section.name == original['section_name']
    offset = section['sh_offset'] + address - section['sh_addr']
    body = elf_bytes[offset:offset + original['size']]
    assert offset == original['file_offset'] and body.hex() == original['range_hex']
    assert hashlib.sha256(body).hexdigest() == original['range_sha256']
    d0 = symbol('_ZN8Presonus17AssignmentHandlerD0Ev')
    vtable = symbol('_ZTVN8Presonus17AssignmentHandlerE')
    vtable_section = elf.get_section(vtable.st_shndx)
    d0_slot = struct.unpack_from('<I', vtable_section.data(),
                                vtable.st_value - vtable_section['sh_addr'] + 16)[0]
    assert d0_slot == d0.st_value
    d0_section = elf.get_section(d0.st_shndx)
    begin = d0.st_value - d0_section['sh_addr']
    d0_body = d0_section.data()[begin:begin + d0.st_size]

RECEIVER, ITEMS, INFO, PARAM = 0x200000, 0x200100, 0x200200, 0x200300
VTABLE, CAST, FOCUS, STOP = 0x201000, 0x202000, 0x202100, 0x202200
DELETE = 0xAD5C

def execute(slots, parameter=False):
    emu = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    emu.mem_map(0x75000, 0x1000)
    emu.mem_map(0x200000, 0x10000)
    emu.mem_write(address, body)
    emu.reg_write(UC_ARM_REG_SP, 0x20fff0)
    emu.reg_write(UC_ARM_REG_LR, STOP)
    trace = []
    objects = {0x203000 + i * 0x100: i for i in range(len(slots))}
    live = set()
    count = len(slots)

    def write(where, *values):
        emu.mem_write(where, struct.pack('<' + 'I' * len(values), *values))

    def read(where):
        return struct.unpack('<I', emu.mem_read(where, 4))[0]

    for obj, index in objects.items():
        if slots[index] != '-':
            write(obj, VTABLE)
            live.add(obj)
    write(RECEIVER, ITEMS if count else 0, count)
    write(ITEMS, *(obj if obj in live else 0 for obj in objects))
    write(INFO, 0)
    write(VTABLE, CAST, 0, d0.st_value)
    write(VTABLE + 0x3c, FOCUS)
    if MODE == 'destructor':
        emu.mem_map(0x7e000, 0x1000)
        emu.mem_write(d0.st_value, d0_body)
        emu.mem_map(0xa000, 0x1000)

    def hook(uc, pc, size, user_data):
        if pc not in (CAST, FOCUS, d0.st_value, DELETE):
            return
        obj = uc.reg_read(UC_ARM_REG_R0)
        index = objects[obj]
        if pc == d0.st_value:
            trace.append(['d0', index])
            return
        if pc == DELETE:
            assert obj in live and read(obj) != VTABLE
            trace.append(['delete', index])
            live.remove(obj)
            # Model the imported deallocator by removing this synthetic
            # allocation from the live set and clearing its first word.
            uc.mem_write(obj, bytes(4))
        elif pc == CAST:
            tag = uc.reg_read(UC_ARM_REG_R1)
            trace.append(['cast', index, tag])
            uc.reg_write(UC_ARM_REG_R0, obj if slots[index] != 'n' else 0)
        else:
            assert uc.reg_read(UC_ARM_REG_R1) == INFO
            forwarded = uc.reg_read(UC_ARM_REG_R2)
            assert forwarded in (0, PARAM)
            trace.append(['focus', index, bool(forwarded)])
            write(INFO, index + 1)
            uc.reg_write(UC_ARM_REG_R0, 7 if slots[index] == 't' else 0)
        uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))

    emu.hook_add(UC_HOOK_CODE, hook)
    emu.reg_write(UC_ARM_REG_R0, RECEIVER)
    emu.reg_write(UC_ARM_REG_R1, INFO)
    emu.reg_write(UC_ARM_REG_R2, PARAM if parameter else 0)
    table_before = bytes(emu.mem_read(RECEIVER, 8))
    items_before = bytes(emu.mem_read(ITEMS, 4 * count)) if count else b''
    emu.emu_start(address, STOP, count=10000)
    assert emu.reg_read(UC_ARM_REG_PC) == STOP
    assert bytes(emu.mem_read(RECEIVER, 8)) == table_before
    if count:
        assert bytes(emu.mem_read(ITEMS, 4 * count)) == items_before
    if MODE == 'destructor':
        assert not live
        return {'slots': slots, 'trace': trace, 'receiver_return': emu.reg_read(UC_ARM_REG_R0) == RECEIVER}
    return {'slots': slots, 'parameter': parameter, 'trace': trace,
            'result': emu.reg_read(UC_ARM_REG_R0), 'info': read(INFO)}


if MODE == 'focus':
    cases = [execute(slots, param) for slots in ('', '-', 'n', 'f', 't', 'n-ftf', 'tft', 'f-nf') for param in (False, True)]
elif MODE == 'count':
    cases = [execute(slots) for slots in ('', 'n', '-', 'nn', 'n--nn')]
else:
    cases = [execute(slots) for slots in ('', '-', 'n', 'n-n', 'nnnnn')]
payload = {'original': original, 'unicorn': unicorn.__version__, 'cases': cases}
if MODE == 'destructor':
    payload['deleting_destructor'] = {'address': d0.st_value,
                                      'size': d0.st_size,
                                      'sha256': hashlib.sha256(d0_body).hexdigest(),
                                      'operator_delete_plt': DELETE}
rendered = json.dumps(payload, indent=2) + '\n'
if len(sys.argv) > 1:
    assert Path(sys.argv[1]).read_text() == rendered
    print(f'Original {MODE} replay: {len(cases)} cases')
else:
    print(rendered, end='')
