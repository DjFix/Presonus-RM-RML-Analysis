import hashlib
import json
from pathlib import Path
import struct
import sys

from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import UC_ARCH_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UC_MODE_ARM, Uc
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0
from unicorn.arm_const import UC_ARM_REG_R1, UC_ARM_REG_SP

here = Path(__file__).resolve().parent
root = here.parents[3]
packet = (root / 'temp/recovery-work/rolling-c001-20261124/packeting/sqlite-cycle02'
          / 'surface_channel_worker12/packet/tasks' / here.name / 'CONTEXT.json')
original = json.loads(packet.read_text())['originals'][0]['original']
image = next(p / original['elf_path'] for p in (root, *root.parents)
             if (p / original['elf_path']).is_file())
assert hashlib.sha256(image.read_bytes()).hexdigest() == original['elf']
is_input = 'surfaceinput' in here.name

channel_prefix = '_ZN8Presonus7Surface23SurfaceChannelComponent'
channel_c2 = channel_prefix + 'C2Ei'
server_c2 = '_ZN8Presonus2UC15ServerComponentC2EPKc'
core_c2 = '_ZN4Core8Portable9ComponentC2EPKc'

with image.open('rb') as stream:
    elf = ELFFile(stream)
    symtab = elf.get_section_by_name('.symtab')

    def extract(name):
        entry = symtab.get_symbol_by_name(name)[0].entry
        section = elf.get_section(entry.st_shndx)
        start = entry.st_value - section['sh_addr']
        data = section.data()[start:start + entry.st_size]
        return {'mangled': name, 'address': entry.st_value, 'size': entry.st_size,
                'file_offset': section['sh_offset'] + start, 'section': entry.st_shndx,
                'sha256': hashlib.sha256(data).hexdigest()}, data

    target, code = extract(original['mangled'])
    address = target['address']
    for field in ('address', 'size', 'file_offset', 'section'):
        assert target[field] == original[field]
    assert code.hex() == original['range_hex']
    assert target['sha256'] == original['range_sha256']
    channel, channel_code = extract(channel_c2)
    server, server_code = extract(server_c2)
    # Core is an observed provider boundary. Its ELF range is never executed.
    core_entry = symtab.get_symbol_by_name(core_c2)[0].entry
    core_address = core_entry.st_value
    vtable_class = ('21SurfaceInputComponent' if is_input
                    else '23SurfaceChannelComponent')
    vtable, _ = extract('_ZTVN8Presonus7Surface' + vtable_class + 'E')
    channel_table, _ = extract('_ZTVN8Presonus7Surface23SurfaceChannelComponentE')
    server_table, _ = extract('_ZTVN8Presonus2UC15ServerComponentE')

BASE, STOP = 0x200000, 0x203000

def execute(mode, seed):
    machine = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    for page in (0xb6000, 0xb7000, 0x45000, 0x11a000, BASE):
        machine.mem_map(page, 0x1000)
    machine.mem_map(0x201000, 0x3000)
    machine.mem_write(address, code)
    machine.mem_write(server['address'], server_code)
    if is_input:
        machine.mem_write(channel['address'], channel_code)
    receiver = BASE + 0x100 * seed
    initial = bytearray([0x40 + seed] * 0x90)
    sentinel = f'name-{seed}'.encode() + b'\0'
    initial[8:8 + len(sentinel)] = sentinel
    machine.mem_write(receiver, bytes(initial))
    machine.reg_write(UC_ARM_REG_SP, 0x202ff0)
    machine.reg_write(UC_ARM_REG_LR, STOP)
    machine.reg_write(UC_ARM_REG_R0, receiver)
    machine.reg_write(UC_ARM_REG_R1, mode & 0xffffffff)
    events = []

    def hook(emu, pc, size, data):
        if pc == channel['address'] and is_input:
            assert emu.reg_read(UC_ARM_REG_R0) == receiver
            events.append(['channel_c2', emu.reg_read(UC_ARM_REG_R1)])
        if pc in (server['address'], core_address):
            kind = 'server_c2' if pc == server['address'] else 'core_c2'
            assert emu.reg_read(UC_ARM_REG_R0) == receiver
            assert emu.reg_read(UC_ARM_REG_R1) == receiver + 8
            events.append([kind, 8])
        if pc == core_address:
            assert bytes(emu.mem_read(receiver + 8, len(sentinel))) == sentinel
            emu.reg_write(UC_ARM_REG_PC, emu.reg_read(UC_ARM_REG_LR))

    def writes(emu, access, where, size, value, data):
        if receiver <= where < receiver + len(initial):
            events.append(['write', where - receiver, size, value])

    machine.hook_add(UC_HOOK_CODE, hook)
    machine.hook_add(UC_HOOK_MEM_WRITE, writes)
    machine.emu_start(address, STOP, count=400)
    assert machine.reg_read(UC_ARM_REG_PC) == STOP
    assert machine.reg_read(UC_ARM_REG_R0) == receiver
    expected_mode = 1 if is_input else mode & 0xffffffff
    expected = ([['channel_c2', 1]] if is_input else [])
    expected += [['server_c2', 8], ['core_c2', 8],
                 ['write', 4, 4, server_table['address'] + 8 + 0x3c],
                 ['write', 0x84, 1, 0], ['write', 0x28, 1, 1],
                 ['write', 0, 4, server_table['address'] + 8],
                 ['write', 0x88, 4, expected_mode],
                 ['write', 4, 4, channel_table['address'] + 8 + 0x48],
                 ['write', 0x28, 1, 1],
                 ['write', 0, 4, channel_table['address'] + 8]]
    if is_input:
        expected += [['write', 0, 4, vtable['address'] + 8],
                     ['write', 4, 4, vtable['address'] + 8 + 0x48]]
    assert events == expected, events
    unchanged = list(range(8, 0x28)) + list(range(0x29, 0x84))
    actual = bytes(machine.mem_read(receiver, len(initial)))
    assert all(actual[i] == initial[i] for i in unchanged)
    return {'argument': mode, 'seed': seed, 'mode': struct.unpack_from('<I', actual, 0x88)[0],
            'base_flag': actual[0x28], 'receiver_return': True, 'events': events}

modes = (-2147483648, -1, 0, 1, 2, 2147483647)
cases = [execute(mode, 1 + i % 2) for i, mode in enumerate(modes)]
result = {'original': original, 'server_c2': server,
          'core_c2_boundary': {'mangled': core_c2, 'address': core_address},
          'vtable': vtable, 'unicorn': unicorn.__version__, 'cases': cases}
if is_input:
    result['channel_c2'] = channel
rendered = json.dumps(result, indent=2) + '\n'
if len(sys.argv) > 1:
    assert Path(sys.argv[1]).read_text() == rendered
    print(f'Original constructor: {len(cases)} executions')
else:
    print(rendered, end='')
