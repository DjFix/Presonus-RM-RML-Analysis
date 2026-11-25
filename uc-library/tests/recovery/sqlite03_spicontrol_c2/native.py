"""Replay exact ARM SPI and native LED base initialization with inert IO."""
import hashlib
from io import BytesIO
import json
from pathlib import Path
import struct

from elftools.elf.elffile import ELFFile
import unicorn
from unicorn.arm_const import (UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0,
                               UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3,
                               UC_ARM_REG_SP)

TASK = Path(__file__).parent.name
PACKET = Path('temp/recovery-work/sqlite-issued/packet') / TASK / 'CONTEXT.json'
ROOT = Path('/home/rs/projects/opencs/ai-line-analysis')
RECEIVER, IO, SP, CALLBACK, STOP = 0x20000000, 0x20001000, 0x20004000, 0x20005000, 0x20006000
CASES = ((4, 0, 0), (-5, 7, -1), (0, -1, 17),
         (-2147483648, 2147483647, -100), (2147483647, -2147483648, 1))
REGS = (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def branch(address, word):
    relative = (word & 0xffffff) * 4
    if relative & 0x2000000:
        relative -= 0x4000000
    return address + 8 + relative


def observe():
    context = json.loads(PACKET.read_text())['task']
    target, = context['originals']
    path = ROOT / target['elf_path']
    data = path.read_bytes()
    assert sha(data) == target['elf']
    elf = ELFFile(BytesIO(data))
    symbols = elf.get_section_by_name('.symtab')

    def capture(name):
        symbol, = symbols.get_symbol_by_name(name)
        section = elf.get_section(symbol['st_shndx'])
        address = symbol['st_value']
        size = symbol['st_size']
        offset = address - section['sh_addr']
        assert 0 <= offset <= section['sh_size'] - size
        position = section['sh_offset'] + offset
        body = data[position:position + size]
        row = dict(mangled=name, address=address, section=symbol['st_shndx'],
                   section_name=section.name, file_offset=position, size=size,
                   range_sha256=sha(body))
        return row, body

    ctor, body = capture(target['mangled'])
    assert all(ctor[key] == target[key] for key in ctor)
    mate_name = (target['mangled'].replace('C1Eiii', 'C2Eiii') if TASK.endswith('c1')
                 else target['mangled'].replace('C2Eiii', 'C1Eiii'))
    mate, mate_body = capture(mate_name)
    assert mate['address'] != ctor['address'] and body != mate_body
    assert body[:20] == mate_body[:20] and body[24:] == mate_body[24:]
    base, base_body = capture('_ZN8Presonus5Panel10LEDControlC2Eiii')
    for definition, image in ((ctor, body), (mate, mate_body)):
        word, = struct.unpack_from('<I', image, 20)
        assert branch(definition['address'] + 20, word) == base['address']
    spi_vtable, _ = capture('_ZTVN8Presonus5Panel10SPIControlE')
    led_vtable, _ = capture('_ZTVN8Presonus5Panel10LEDControlE')
    spi_point, led_point = spi_vtable['address'] + 8, led_vtable['address'] + 8
    assert int.from_bytes(body[-4:], 'little') == spi_point
    assert int.from_bytes(base_body[-4:], 'little') == led_point
    broadcast, broadcast_body = capture('_ZN8Presonus5Panel10SPIControl14broadcastValueEi')
    evidence, = context['review']['evidence']
    assert sha((ROOT / evidence['path']).read_bytes()) == evidence['sha256']

    def one_case(args):
        model = unicorn.Uc(unicorn.UC_ARCH_ARM, unicorn.UC_MODE_ARM)
        pages = set()
        for entry, image in ((ctor, body), (base, base_body), (broadcast, broadcast_body)):
            first = entry['address'] & ~0xfff
            limit = (entry['address'] + entry['size'] + 0xfff) & ~0xfff
            for page in range(first, limit, 0x1000):
                if page not in pages:
                    model.mem_map(page, 0x1000)
                    pages.add(page)
            model.mem_write(entry['address'], image)
        model.mem_map(RECEIVER, 0x7000)
        model.mem_write(RECEIVER, bytes([0xa5]) * 64)
        model.mem_write(CALLBACK, b'\x1e\xff\x2f\xe1')

        def put(where, value):
            model.mem_write(where, struct.pack('<I', value))

        def get(where):
            return struct.unpack('<I', bytes(model.mem_read(where, 4)))[0]

        def signed(where):
            return struct.unpack('<i', bytes(model.mem_read(where, 4)))[0]

        base_calls, transitions, visible_writes, io_calls = [], [], [], []

        def code(_, pc, width, _arg):
            if pc == base['address']:
                base_calls.append([model.reg_read(r) for r in REGS])
                assert get(RECEIVER) == 0xa5a5a5a5
            if pc == CALLBACK:
                assert model.reg_read(UC_ARM_REG_R0) == IO
                assert model.reg_read(UC_ARM_REG_R1) == RECEIVER
                io_calls.append(signed(RECEIVER + 4))
                return
            assert any(e['address'] <= pc <= e['address'] + e['size'] - width
                       for e in (ctor, base, broadcast))

        def write(_, _access, where, width, value, _arg):
            if where == RECEIVER:
                transitions.append(value)
            if not SP - 0x1000 <= where <= SP - width:
                assert RECEIVER <= where <= RECEIVER + 60 - width
                visible_writes.append([where - RECEIVER, width, value])

        def run(entry, regs):
            for reg, value in zip(REGS, regs):
                model.reg_write(reg, value & 0xffffffff)
            model.reg_write(UC_ARM_REG_SP, SP)
            model.reg_write(UC_ARM_REG_LR, STOP)
            model.emu_start(entry['address'], STOP, count=100)
            assert model.reg_read(UC_ARM_REG_PC) == STOP
            assert model.reg_read(UC_ARM_REG_SP) == SP

        model.hook_add(unicorn.UC_HOOK_CODE, code)
        model.hook_add(unicorn.UC_HOOK_MEM_WRITE, write)
        run(ctor, (RECEIVER, *args))
        assert model.reg_read(UC_ARM_REG_R0) == RECEIVER
        assert base_calls == [[RECEIVER, *(x & 0xffffffff for x in args)]]
        assert transitions == [led_point, spi_point]
        output = [signed(RECEIVER + offset) for offset in
                  (0x18, 0x28, 0x2c, 4, 8, 12, 16, 20, 0x1c, 0x24, 0x30, 0x34, 0x38)]
        output.insert(9, model.mem_read(RECEIVER + 0x20, 1)[0])
        assert bytes(model.mem_read(RECEIVER + 60, 4)) == bytes([0xa5]) * 4
        ctor_writes = visible_writes.copy()

        # Established prior behavior: broadcast a changed level exactly once;
        # equal and initial -1 do not dispatch. No physical transport runs.
        put(RECEIVER + 0x14, IO)
        put(IO, IO + 0x100)
        put(IO + 0x100 + 8, CALLBACK)
        for level in (-1, 22, 22, -5):
            run(broadcast, (RECEIVER, level))
        output += [len(io_calls), *io_calls, signed(RECEIVER + 4)]
        return dict(args=list(args), output=output, base_calls=base_calls, vptrs=transitions,
                    ctor_writes=ctor_writes, io_calls=io_calls)

    ctor.update(elf_sha256=target['elf'], firmware=target['firmware'], role=target['role'])
    return dict(unicorn_version=unicorn.__version__, targets=[
        dict(original=ctor, compared_constructor_variant=mate, native_base=base,
             previous_broadcast=broadcast, elf_path=str(path), cases=[
                 one_case(args) for args in CASES])])
