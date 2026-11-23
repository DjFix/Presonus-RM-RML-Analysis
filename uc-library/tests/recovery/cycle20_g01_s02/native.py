"""Execute the exact original destructor with explicit offline call boundaries."""
import hashlib
import json
from pathlib import Path
import re
import struct

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, __version__
from unicorn.arm_const import (
    UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_SP,
)

TASK = Path(__file__).resolve().parent.name
ROOT = Path('/home/rs/projects/opencs/ai-line-analysis')
CONTROL = ROOT / 'temp/recovery-work/control10x20-after-4fed70d11/packeting'
PACKET = CONTROL / 'first-lane01-batch/packets' / TASK
OBJECT = 0x3000000
HANDLER = 0x3100000
STACK = 0x4000000
STOP = 0x5000000
CALLS = {0xAD5C: 'delete', 0x11FE8: 'timer', 0x124820: 'attributes',
         0x11B5E0: 'component', HANDLER + 0x200: 'detach'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def execute(segments, target, bound):
    uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    lo = min(address for address, _, _ in segments) & ~4095
    hi = max(address + size for address, size, _ in segments)
    uc.mem_map(lo, (hi - lo + 4095) & ~4095)
    for address, _, data in segments:
        uc.mem_write(address, data)
    for address in (OBJECT, HANDLER, STACK, STOP):
        uc.mem_map(address, 0x1000)

    def put(address, value):
        uc.mem_write(address, struct.pack('<I', value))

    def get(address):
        return struct.unpack('<I', uc.mem_read(address, 4))[0]

    put(OBJECT, 0x11111111)
    put(OBJECT + 0x98, HANDLER if bound else 0)
    put(HANDLER, HANDLER + 0x100)
    put(HANDLER + 0x120, HANDLER + 0x200)
    uc.reg_write(UC_ARM_REG_R0, OBJECT)
    uc.reg_write(UC_ARM_REG_SP, STACK + 0x800)
    uc.reg_write(UC_ARM_REG_LR, STOP)
    trace = []
    released = False
    returned = False
    final = {}

    def snapshot():
        return dict(vptr=get(OBJECT), secondary_vptr=get(OBJECT + 4),
                    timer_vptr=get(OBJECT + 0x84), handler_slot=get(OBJECT + 0x98))

    def hook(machine, address, _size, _data):
        nonlocal released, returned
        if address == STOP:
            returned = True
            machine.emu_stop()
            return
        if address not in CALLS:
            assert target['address'] <= address < target['address'] + target['size'], hex(address)
            return
        name = CALLS[address]
        receiver = machine.reg_read(UC_ARM_REG_R0)
        event = dict(name=name, call_address=address, receiver=receiver)
        if name == 'detach':
            event['controller'] = machine.reg_read(UC_ARM_REG_R1)
            assert receiver == HANDLER and event['controller'] == 0
            assert get(OBJECT + 0x98) == HANDLER
        elif name == 'delete':
            assert receiver == OBJECT and not released
            final.update(snapshot())
            machine.mem_unmap(OBJECT, 0x1000)
            released = True
        else:
            assert get(OBJECT + 0x98) == 0
            event['offset'] = receiver - OBJECT
        trace.append(event)
        machine.reg_write(UC_ARM_REG_PC, machine.reg_read(UC_ARM_REG_LR))

    uc.hook_add(UC_HOOK_CODE, hook)
    uc.emu_start(target['address'], STOP + 4, count=1024)
    assert returned
    if not released:
        final.update(snapshot())
    return dict(bound=bound, trace=trace, storage_unmapped_by_delete_boundary=released, **final)


def generate():
    request = json.loads((PACKET / 'request.json').read_text())
    target = request['targets'][0]
    release = request['work_binding']['binary_releases'][0]
    reads = json.loads((CONTROL / 'READ_INPUTS-first-lane01-batch-cycle20_g01.json').read_text())
    frozen_elf = Path(reads[release['original_path']]['frozen_read_path'])
    elf_hash = sha(frozen_elf.read_bytes())
    assert elf_hash == target['original_elf_sha256']
    with frozen_elf.open('rb') as stream:
        elf = ELFFile(stream)
        section = elf.get_section(target['section'])
        start = target['address'] - section['sh_addr']
        assert 0 <= start and start + target['size'] <= section['sh_size']
        offset = section['sh_offset'] + start
        section_range = section.data()[start:start + target['size']]
        stream.seek(offset)
        raw = stream.read(target['size'])
        assert raw == section_range and len(raw) == target['size']
        sealed = re.search(r'; SHA256 `([a-f0-9]{64})`', (PACKET / 'ELF_CONTEXT.md').read_text())
        assert sealed and sha(raw) == sealed[1]
        segments = [(s['p_vaddr'], s['p_memsz'], s.data())
                    for s in elf.iter_segments() if s['p_type'] == 'PT_LOAD']
    inputs = (False, True) if 'MappingComponent' in target['mangled'] else (False,)
    return dict(task_id=TASK, elf_sha256=elf_hash, frozen_path=str(frozen_elf),
                firmware=release['firmware_version'], role=release['role'],
                section=section.name, section_index=target['section'], file_offset=offset,
                address=target['address'], size=target['size'], mangled=target['mangled'],
                range_sha256=sha(raw), emulator=f'Unicorn {__version__}',
                boundaries='External calls observed at their real targets; the delete boundary unmaps receiver storage. No Core body execution.',
                cases=[execute(segments, target, bound) for bound in inputs])


if __name__ == '__main__':
    print(json.dumps(generate(), indent=2))
