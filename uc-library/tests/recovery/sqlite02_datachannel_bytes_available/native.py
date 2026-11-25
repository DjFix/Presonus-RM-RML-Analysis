MODE = 'bytes_available'
import hashlib
import json
from pathlib import Path
import struct
import sys

from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import UC_ARCH_ARM, UC_HOOK_CODE, UC_MODE_ARM, Uc
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0
from unicorn.arm_const import UC_ARM_REG_R1, UC_ARM_REG_SP

root = Path(__file__).resolve().parents[4]
task = Path(__file__).resolve().parent.name
packet = (root / 'temp/recovery-work/rolling-c001-20261124/packeting'
          / 'sqlite-cycle02/datachannel_worker12/packet/tasks' / task / 'CONTEXT.json')
original = json.loads(packet.read_text())['originals'][0]['original']
image = next(p / original['elf_path'] for p in (root, *root.parents)
             if (p / original['elf_path']).is_file())
assert hashlib.sha256(image.read_bytes()).hexdigest() == original['elf']
with image.open('rb') as stream:
    elf = ELFFile(stream)
    symtab = elf.get_section_by_name('.symtab')

    def extract(name):
        entry = symtab.get_symbol_by_name(name)[0].entry
        section = elf.get_section(entry.st_shndx)
        start = entry.st_value - section['sh_addr']
        data = section.data()[start:start + entry.st_size]
        return entry, section['sh_offset'] + start, data, section.name

    target, offset, code, section = extract(original['mangled'])
    address = target.st_value
    assert address == original['address'] and len(code) == original['size']
    assert offset == original['file_offset'] and section == original['section_name']
    assert target.st_shndx == original['section']
    assert code.hex() == original['range_hex']
    assert hashlib.sha256(code).hexdigest() == original['range_sha256']

    table, vtable_offset, vtable_bytes, _ = extract('_ZTVN8Presonus2UC11DataChannelE')
    slot = 3 if MODE == 'bytes_available' else 8
    assert struct.unpack_from('<I', vtable_bytes, slot * 4)[0] == address
    vtable = {'address': table.st_value, 'file_offset': vtable_offset,
              'size': table.st_size, 'sha256': hashlib.sha256(vtable_bytes).hexdigest(),
              'absolute_word_index': slot, 'address_point_slot': slot - 2}

    queue_name = '_ZN8Presonus2UC11PacketQueue13getTotalBytesEv'
    queue, queue_offset, queue_code, queue_section = extract(queue_name)
    lock = extract('_ZN4Core7Threads8CoreLock4lockEv')[0].st_value
    unlock = extract('_ZN4Core7Threads8CoreLock6unlockEv')[0].st_value

BASE, INCOMING, OUTGOING, STOP = 0x200000, 0x200100, 0x200200, 0x22ff00

def execute(n_in, n_out, timeout, variant):
    machine = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    machine.mem_map(0x104000, 0x1000)
    machine.mem_map(0x10e000, 0x1000)
    machine.mem_map(BASE, 0x30000)
    machine.mem_write(address, code)
    machine.mem_write(queue.st_value, queue_code)
    machine.reg_write(UC_ARM_REG_SP, 0x22fff0)
    machine.reg_write(UC_ARM_REG_LR, STOP)
    receiver = BASE + 0x300 * variant
    trace = []

    def pack(where, *values):
        machine.mem_write(where, struct.pack('<' + 'I' * len(values), *values))

    def setup_queue(q, n, first_packet):
        pack(q + 0x20, first_packet if n else 0)
        while n:
            length = min(n, 200)
            n -= length
            pack(first_packet, first_packet + 16 if n else 0, 0, 0, length)
            first_packet += 16

    pack(receiver, table.st_value + 8, INCOMING, OUTGOING, 0xcafe00 + variant)
    setup_queue(INCOMING, n_in, BASE + 0x1000)
    setup_queue(OUTGOING, n_out, BASE + 0x2000)
    state = bytes(machine.mem_read(BASE, 0x3000))
    machine.reg_write(UC_ARM_REG_R0, receiver)
    machine.reg_write(UC_ARM_REG_R1, timeout & 0xffffffff)

    def hook(emu, pc, size, data):
        if pc == queue.st_value:
            trace.append(['total_bytes', emu.reg_read(UC_ARM_REG_R0)])
        if pc in (lock, unlock):
            trace.append(['lock' if pc == lock else 'unlock', emu.reg_read(UC_ARM_REG_R0)])
            emu.reg_write(UC_ARM_REG_PC, emu.reg_read(UC_ARM_REG_LR))

    machine.hook_add(UC_HOOK_CODE, hook)
    machine.emu_start(address, STOP, count=4000)
    assert machine.reg_read(UC_ARM_REG_PC) == STOP
    assert bytes(machine.mem_read(BASE, 0x3000)) == state
    return {'incoming': n_in, 'outgoing': n_out, 'timeout': timeout, 'receiver_variant': variant,
            'result': machine.reg_read(UC_ARM_REG_R0), 'boundary_trace': trace}

sizes = [(0, 0), (0, 73), (1, 0), (199, 201), (200, 987), (201, 3), (4097, 4122)]
timeouts = [0, -1, -2147483648, 1, 42, 2147483647]
if MODE == 'bytes_available':
    cases = [execute(i, o, 0, index % 2) for index, (i, o) in enumerate(sizes)]
    assert all(row['boundary_trace'] == [[op, INCOMING] for op in ('total_bytes', 'lock', 'unlock')]
               for row in cases)
else:
    cases = [execute(i, o, t, index % 2) for index, (i, o) in enumerate(sizes)
             for t in timeouts]
    assert all(not row['boundary_trace'] for row in cases)
output = {'original': original, 'unicorn': unicorn.__version__, 'vtable': vtable,
          'cases': cases}
if MODE == 'bytes_available':
    output['packet_queue'] = {'mangled': queue_name, 'address': queue.st_value,
                              'section': queue_section, 'size': queue.st_size,
                              'file_offset': queue_offset,
                              'sha256': hashlib.sha256(queue_code).hexdigest(),
                              'core_boundaries': {'lock': lock, 'unlock': unlock}}
rendered = json.dumps(output, indent=2) + '\n'
if len(sys.argv) > 1:
    assert Path(sys.argv[1]).read_text() == rendered
    print(f'Original {MODE}: {len(cases)} cases')
else:
    print(rendered, end='')
