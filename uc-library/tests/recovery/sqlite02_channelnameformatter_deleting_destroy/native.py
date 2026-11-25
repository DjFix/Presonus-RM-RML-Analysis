"""Run the caller, constructors and destructors from exact ARM sections."""
import ctypes
import hashlib
from io import BytesIO
import json
import math
from pathlib import Path
import struct

from elftools.elf.elffile import ELFFile
import unicorn
from unicorn.arm_const import (UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0,
                               UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_SP)

TASK = Path(__file__).parent.name
PACKET = Path('temp/recovery-work/sqlite-issued/packet') / TASK / 'CONTEXT.json'
ROOT = Path('/home/rs/projects/opencs/ai-line-analysis')
CLASS = 'N8Presonus2UC6Format20ChannelNameFormatter'
RECEIVER, ARG, OUT = 0x20000000, 0x20001000, 0x20002000
STACK, SENTINEL = 0x20004000, 0x20005000
INPUTS = ((0x00000000, 32, True), (0x80000000, 4, True), (0, 2, True),
          (0, 1, True), (0, 0, True), (0, 8, False), (0x41480000, 32, True),
          (0xc0600000, 32, True), (0x3f000000, 32, True), (0x42c80000, 5, True),
          (0xc3a10000, 3, True), (0xcf000000, 32, True), (0x4effffff, 32, True),
          (0x3f800000, 0, True), (0xbf800000, 8, False))
LIBC = ctypes.CDLL(None)
LIBC.snprintf.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_char_p, ctypes.c_int]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def raw_float(value):
    return struct.unpack('<f', struct.pack('<I', value))[0]


def raw_signed(value):
    return ctypes.c_int32(value).value


def observe_target(target, evidence):
    elf_path = ROOT / evidence['original']['elf_path']
    image = elf_path.read_bytes()
    assert sha(image) == target['elf']
    elf = ELFFile(BytesIO(image))
    symbols = elf.get_section_by_name('.symtab')

    def capture(name):
        sym, = symbols.get_symbol_by_name(name)
        section = elf.get_section(sym['st_shndx'])
        address, size = sym['st_value'], sym['st_size']
        relative = address - section['sh_addr']
        assert 0 <= relative <= section['sh_size'] - size
        offset = section['sh_offset'] + relative
        body = image[offset:offset + size]
        return dict(mangled=name, address=address, size=size, section=sym['st_shndx'],
                    section_name=section.name, file_offset=offset, range_sha256=sha(body)), body

    def string_at(address):
        for seg in elf.iter_segments():
            start = seg['p_vaddr']
            if seg['p_type'] == 'PT_LOAD' and start <= address < start + seg['p_filesz']:
                data = seg.data()[address - start:]
                return data.split(b'\0', 1)[0]
        raise AssertionError(hex(address))

    def word(data, offset):
        return struct.unpack_from('<I', data, offset)[0]

    original, body = capture(target['mangled'])
    assert all(original[k] == target[k] for k in ('address', 'size', 'section', 'range_sha256'))
    assert original['file_offset'] == evidence['original']['file_offset']
    addresses = {r['code_offset']: r for r in evidence['site_evidence']}
    target_ctor = target['mangled'].endswith(('C1Ev', 'C2Ev'))
    target_dtor = target['mangled'].endswith(('D1Ev', 'D0Ev'))
    deleting = target['mangled'].endswith('D0Ev')
    app_vtable, _ = capture('_ZTV' + CLASS + 'E')
    core_vtable, _ = capture('_ZTVN4Core9FormatterE')
    app_point, core_point = app_vtable['address'] + 8, core_vtable['address'] + 8
    ctor, ctor_body = capture('_Z' + CLASS + 'C1Ev')
    name_ptr = word(ctor_body, len(ctor_body) - 4)
    name = string_at(name_ptr)
    assert name == b'ch_name'
    mate = None
    endpoints = {}
    if target_ctor:
        mate_name = target['mangled'].replace('C1Ev','C2Ev') if target['mangled'].endswith('C1Ev') else target['mangled'].replace('C2Ev','C1Ev')
        mate, mate_body = capture(mate_name)
        mate.update(identical_body=mate_body == body, same_address=mate['address'] == original['address'])
        assert word(body, len(body) - 8) == app_point
    elif target_dtor:
        assert word(body, len(body) - 4) == core_point
        if deleting:
            assert '_ZdlPv@@GLIBCXX_3.4' in addresses[28]['names']
            endpoints[addresses[28]['destination']] = 'delete'
    else:
        for offset, kind in ((40, 'compare'), (104, 'strlen'), (132, 'copy'),
                             (156, 'truncate'), (176, 'format')):
            endpoints[addresses[offset]['destination']] = kind
        assert string_at(addresses[52]['value']) == b'Off'
        assert string_at(addresses[168]['value']) == b'Ch %d'

    def run(item):
        model = unicorn.Uc(unicorn.UC_ARCH_ARM, unicorn.UC_MODE_ARM)
        pages = set()
        def map_page(address):
            page = address & ~0xfff
            if page not in pages:
                model.mem_map(page, 0x1000)
                pages.add(page)
        for row, source in ((original, body), (ctor, ctor_body)):
            map_page(row['address'])
            map_page(row['address'] + row['size'] - 1)
            model.mem_write(row['address'], source)
        if not (target_ctor or target_dtor):
            for offset in (52, 168):
                literal_address = addresses[offset]['value']
                literal = string_at(literal_address) + b'\0'
                map_page(literal_address)
                map_page(literal_address + len(literal) - 1)
                model.mem_write(literal_address, literal)
        for endpoint in endpoints:
            map_page(endpoint)
        for page in range(RECEIVER, SENTINEL + 0x1000, 0x1000):
            map_page(page)
        model.mem_write(RECEIVER, bytes([0xa5]) * 16)
        model.mem_write(OUT, bytes([0xa5]) * 36)
        if target_dtor or not target_ctor:
            model.reg_write(UC_ARM_REG_R0, RECEIVER)
            model.reg_write(UC_ARM_REG_SP, STACK)
            model.reg_write(UC_ARM_REG_LR, SENTINEL)
            model.emu_start(ctor['address'], SENTINEL, count=40)
            assert model.reg_read(UC_ARM_REG_PC) == SENTINEL
            assert bytes(model.mem_read(RECEIVER, 8)) == struct.pack('<II', app_point, name_ptr)
        if item is not None:
            bits, capacity, has_buffer = item
            model.mem_write(ARG, struct.pack('<IIIII', 0, OUT if has_buffer else 0,
                                             capacity, bits, 0))
        calls, writes = [], []

        def read_text(pointer):
            text = bytearray()
            while len(text) < 128:
                byte = model.mem_read(pointer + len(text), 1)[0]
                if not byte:
                    return bytes(text)
                text.append(byte)
            raise AssertionError('missing boundary terminator')

        def code(_, pc, width, _arg):
            if pc not in endpoints:
                assert original['address'] <= pc <= original['address'] + original['size'] - width
                return
            kind = endpoints[pc]
            a, b, c = (model.reg_read(r) for r in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2))
            calls.append([kind, a, b, c])
            if kind == 'delete':
                assert a == RECEIVER
                assert struct.unpack('<II', model.mem_read(a, 8)) == (core_point, name_ptr)
                model.mem_unmap(a, 0x1000)
            elif kind == 'compare':
                model.reg_write(UC_ARM_REG_R0, int(raw_float(a) == raw_float(b)))
            elif kind == 'truncate':
                assert math.isfinite(raw_float(a))
                model.reg_write(UC_ARM_REG_R0, int(raw_float(a)) & 0xffffffff)
            elif kind == 'strlen':
                model.reg_write(UC_ARM_REG_R0, len(read_text(a)))
            elif kind == 'copy':
                assert a == OUT and c <= capacity - 1
                if c:
                    assert len(read_text(b)) >= c
                    model.mem_write(a, bytes(model.mem_read(b, c)))
                model.reg_write(UC_ARM_REG_R0, a)
            else:
                # Observe the independently supplied real libc integer formatting
                # primitive at the verified CCL appendFormat boundary.
                assert read_text(a) == b'' and read_text(b) == b'Ch %d'
                buf = ctypes.create_string_buffer(128)
                count = LIBC.snprintf(buf, len(buf), read_text(b), raw_signed(c))
                assert 0 <= count < len(buf)
                model.mem_write(a, buf.value + b'\0')
                model.reg_write(UC_ARM_REG_R0, a)
            model.reg_write(UC_ARM_REG_PC, model.reg_read(UC_ARM_REG_LR))

        def write(_, _access, where, width, value, _arg):
            if not STACK - 0x1000 <= where <= STACK - width:
                writes.append([where, width, value])

        model.hook_add(unicorn.UC_HOOK_CODE, code)
        model.hook_add(unicorn.UC_HOOK_MEM_WRITE, write)
        model.reg_write(UC_ARM_REG_R0, RECEIVER)
        model.reg_write(UC_ARM_REG_R1, ARG)
        model.reg_write(UC_ARM_REG_SP, STACK)
        model.reg_write(UC_ARM_REG_LR, SENTINEL)
        model.emu_start(original['address'], SENTINEL, count=200)
        assert model.reg_read(UC_ARM_REG_PC) == SENTINEL
        assert model.reg_read(UC_ARM_REG_SP) == STACK
        if target_ctor:
            first, second = struct.unpack('<II', model.mem_read(RECEIVER, 8))
            assert (first, second) == (app_point, name_ptr) and not calls
            output = name.decode()
        elif target_dtor:
            assert writes == [[RECEIVER, 4, core_point]]
            assert len(calls) == int(deleting)
            if not deleting:
                assert struct.unpack('<II', model.mem_read(RECEIVER, 8)) == (core_point, name_ptr)
            output = int(deleting)
        else:
            assert all(OUT <= item[0] < OUT + capacity for item in writes)
            output = bytes(model.mem_read(OUT, 36)).hex()
            assert bytes(model.mem_read(RECEIVER, 8)) == struct.pack('<II', app_point, name_ptr)
        return dict(input=list(item) if item is not None else None,
                    calls=calls, writes=writes, output=output)

    original.update(elf_sha256=target['elf'], firmware=target['firmware'], role=target['role'])
    return dict(original=original, elf_path=str(elf_path), constructor=ctor,
                registration_name=name.decode(), compared_constructor_variant=mate,
                app_vtable=app_vtable, core_vtable=core_vtable, cases=[
                    run(item) for item in ((None,) if target_ctor or target_dtor else INPUTS)])


def observe():
    task = json.loads(PACKET.read_text())['task']
    item, = task['review']['evidence']
    evidence = (ROOT / item['path']).read_bytes()
    assert sha(evidence) == item['sha256']
    rows = {row['original']['elf']: row for row in json.loads(evidence)['native']}
    return {'unicorn_version': unicorn.__version__, 'targets': [
        observe_target(target, rows[target['elf']]) for target in task['originals']]}
