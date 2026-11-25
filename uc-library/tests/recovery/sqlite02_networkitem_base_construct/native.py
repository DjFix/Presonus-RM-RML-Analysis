"""Verify original ELF ranges and execute the offline NetworkItem oracle."""
import ctypes
import hashlib
from io import BytesIO
import json
from pathlib import Path
import struct

from capstone import Cs, CS_ARCH_ARM, CS_MODE_ARM
from elftools.elf.elffile import ELFFile
import unicorn
from unicorn.arm_const import (
    UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_SP,
)

TASK = Path(__file__).parent.name
PACKET = Path('temp/recovery-work/sqlite-issued/packet') / TASK / 'CONTEXT.json'
TITLE = TASK.endswith('get_title')
SERVER = '_ZN8Presonus2UC17ServerDescriptionC1Ev'
CORE = '_ZN4Core13CStringBufferILi64EEC1EPKc'
SCALARS = ((4, 4), (8, 4), (0x8c, 2), (0x1d0, 4))
STRING_OFFSETS = (0xc, 0x4c, 0x8e, 0xce, 0x10e, 0x14e, 0x18e)
RECEIVER, OUTPUT, STACK, STOP = 0x20000000, 0x20001000, 0x20003ff0, 0x20004000
LIBC = ctypes.CDLL(None)
LIBC.strlen.argtypes = [ctypes.c_char_p]
LIBC.strlen.restype = ctypes.c_size_t
LIBC.strncat.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_size_t]
LIBC.strncat.restype = ctypes.c_void_p
LIBC.memcpy.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_size_t]
LIBC.memcpy.restype = ctypes.c_void_p

TITLE_CASES = [
    (0, '', '', '', ''),
    (1, '', '', '', ''),
    (0, 'Mixer', '1.23', '192.0.2.17', 'desk'),
    (1, 'Mixer', '1.23', '192.0.2.17', 'desk'),
    (2, 'Mixer', '1.23', '192.0.2.17', ''),
    (1, 'Mixer', '', '', 'desk'),
    (1, '', 'v2', '192.0.2.17', ''),
    (0xffffffff, '', 'unused', '', 'desk'),
    (0, 'a' * 63, '', 'b' * 62, 'tail'),
    (0, 'a' * 63, '', 'b' * 63, 'tail'),
    (1, 'a' * 63, 'v' * 63, 'b' * 63, 'c' * 63),
    (0, 'a' * 63, '', 'b' * 32, 'c' * 63),
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def function(elf, image, name):
    row, = elf.get_section_by_name('.symtab').get_symbol_by_name(name)
    section = elf.get_section(row['st_shndx'])
    address, size = row['st_value'], row['st_size']
    relative = address - section['sh_addr']
    assert row['st_info']['type'] == 'STT_FUNC'
    assert section.name == '.text' and section['sh_type'] == 'SHT_PROGBITS'
    assert 0 <= relative <= section['sh_size'] - size
    offset = section['sh_offset'] + relative
    data = image[offset:offset + size]
    return dict(mangled=name, address=address, size=size, section=row['st_shndx'],
                section_name=section.name, file_offset=offset, range_sha256=sha(data)), data


def execute(elf, image, original, body, evidence):
    code_ranges = [(original, body)]
    for name in (SERVER, CORE):
        code_ranges.append(function(elf, image, name))
    server_body, core_body = (meta for meta, _ in code_ranges[1:])
    libc_calls, literals = {}, {}
    for site in evidence['site_evidence']:
        address = original['address'] + site['code_offset']
        instruction, = Cs(CS_ARCH_ARM, CS_MODE_ARM).disasm(
            body[site['code_offset']:site['code_offset'] + 4], address)
        if site['kind'] == 'literal':
            assert instruction.mnemonic == 'ldr'
            relative = address + 8 + int(instruction.op_str.split('#')[1].rstrip(']'), 16)
            literal, = struct.unpack_from('<I', body, relative - original['address'])
            assert literal == site['value']
            offset, = elf.address_offsets(literal, size=2)
            literals[literal] = image[offset:offset + 2]
            continue
        assert int(instruction.op_str.removeprefix('#'), 16) == site['destination']
        if not site['names']:
            assert original['address'] <= site['destination'] < original['address'] + original['size']
            continue
        name, = site['names']
        if name == SERVER:
            assert site['destination'] == server_body['address']
        else:
            assert name in ('strlen@@GLIBC_2.4', 'memcpy@@GLIBC_2.4', 'strncat@@GLIBC_2.4')
            libc_calls[site['destination']] = name.split('@')[0]

    def run(case):
        machine = unicorn.Uc(unicorn.UC_ARCH_ARM, unicorn.UC_MODE_ARM)
        pages = set()

        def put(address, data):
            for page in range(address & ~4095, ((address + len(data) - 1) & ~4095) + 4096, 4096):
                if page not in pages:
                    machine.mem_map(page, 4096)
                    pages.add(page)
            machine.mem_write(address, data)

        for metadata, code in code_ranges:
            put(metadata['address'], code)
        for address, data in literals.items():
            put(address, data)
        for address in libc_calls:
            put(address, b'\0' * 4)
        for page in range(RECEIVER, STOP + 1, 4096):
            put(page, b'\0' * 4096)
        machine.mem_write(RECEIVER, b'\xa5' * 0x1dc)
        machine.mem_write(OUTPUT, b'\xa5' * 127 + b'\0')
        machine.reg_write(UC_ARM_REG_SP, STACK)
        events, writes = [], []

        def read_c_string(address, limit=128):
            data = bytes(machine.mem_read(address, limit))
            assert b'\0' in data
            return data.split(b'\0', 1)[0]

        def read_number(offset, size=4):
            return int.from_bytes(machine.mem_read(RECEIVER + offset, size), 'little')

        def calls(emu, pc, width, _):
            r0, r1, r2 = (emu.reg_read(reg) for reg in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2))
            if pc == server_body['address'] or pc == core_body['address']:
                metadata = server_body if pc == server_body['address'] else core_body
                events.append([metadata['mangled'], r0 - RECEIVER, r1])
            if pc not in libc_calls:
                assert any(meta['address'] <= pc <= meta['address'] + meta['size'] - width
                           for meta, _ in code_ranges), hex(pc)
                return
            name = libc_calls[pc]
            events.append([name, r0, r1, r2])
            if name == 'strlen':
                result = LIBC.strlen(read_c_string(r0, 64 if r0 < OUTPUT else 128))
            elif name == 'memcpy':
                assert OUTPUT <= r0 and 0 < r2 <= OUTPUT + 128 - r0
                source = bytes(emu.mem_read(r1, r2))
                buffer = ctypes.create_string_buffer(r2)
                LIBC.memcpy(buffer, source, r2)
                emu.mem_write(r0, buffer.raw)
                writes.append(['libc', r0 - OUTPUT, buffer.raw.hex()])
                result = r0
            else:
                assert r0 == OUTPUT and r2 < 128
                before = bytes(emu.mem_read(OUTPUT, 128))
                buffer = ctypes.create_string_buffer(before, 128)
                LIBC.strncat(buffer, read_c_string(r1, 64), r2)
                emu.mem_write(OUTPUT, buffer.raw)
                writes.append(['libc', 0, buffer.raw.hex()])
                result = r0
            emu.reg_write(UC_ARM_REG_R0, result)
            emu.reg_write(UC_ARM_REG_PC, emu.reg_read(UC_ARM_REG_LR))

        def store(_, _access, address, width, value, _context):
            if RECEIVER <= address < OUTPUT + 128:
                writes.append(['arm', address - RECEIVER, width, value])
            else:
                assert OUTPUT + 4096 <= address <= STACK - width, hex(address)

        machine.hook_add(unicorn.UC_HOOK_CODE, calls)
        machine.hook_add(unicorn.UC_HOOK_MEM_WRITE, store)
        if TITLE:
            type_word, app, version, host_address, host_name = case
            machine.mem_write(RECEIVER, bytes(0x1dc))
            machine.mem_write(RECEIVER, struct.pack('<I', type_word))
            for offset, text in zip((0x8e, 0xce, 0xc, 0x4c), (app, version, host_address, host_name)):
                assert len(text) <= 63
                machine.mem_write(RECEIVER + offset, text.encode('ascii') + b'\0')
            r1 = OUTPUT
        else:
            r1 = case
        machine.reg_write(UC_ARM_REG_R0, RECEIVER)
        machine.reg_write(UC_ARM_REG_R1, r1)
        machine.reg_write(UC_ARM_REG_LR, STOP)
        machine.emu_start(original['address'], STOP, count=1000)
        assert machine.reg_read(UC_ARM_REG_PC) == STOP
        assert machine.reg_read(UC_ARM_REG_SP) == STACK
        result = machine.reg_read(UC_ARM_REG_R0)
        if TITLE:
            assert all(write[0] == 'libc' or write[1] >= OUTPUT - RECEIVER for write in writes)
            expected = bytes(machine.mem_read(OUTPUT, 128)).hex()
        else:
            assert result == RECEIVER
            expected = [read_number(0), read_number(0x1d4), read_number(0x1d8),
                        *(read_number(offset, size) for offset, size in SCALARS),
                        *(read_c_string(RECEIVER + offset, 64).decode('ascii') for offset in STRING_OFFSETS)]
            assert events[0][0:2] == [SERVER, 4]
            assert events[1:] == [[CORE, offset, 0] for offset in STRING_OFFSETS]
        return dict(input=list(case) if TITLE else case, expected=expected, arm_r0=result,
                    calls=events, writes=writes)

    cases = TITLE_CASES if TITLE else (0, 1, 2, 0x80000000, 0xffffffff)
    return dict(original=original, call_bodies=[server_body, core_body] if not TITLE else [],
                libc_calls=libc_calls, literals={address: data.hex() for address, data in literals.items()},
                cases=[run(case) for case in cases])


def observe():
    packet = json.loads(PACKET.read_text())
    binding = packet['task']['review']['equivalence']
    direct = Path(binding['path']).read_bytes()
    assert sha(direct) == binding['sha256']
    evidence = json.loads(direct)['native']
    results = []
    for row in packet['originals']:
        target = row['original']
        image = Path(target['elf_path']).read_bytes()
        assert sha(image) == target['elf']
        elf = ELFFile(BytesIO(image))
        original, body = function(elf, image, target['mangled'])
        assert all(target[k] == v for k, v in original.items())
        assert body.hex() == target['range_hex']
        original.update(elf_sha256=target['elf'], role=target['role'], firmware=target['firmware'])
        binding, = [item for item in evidence if item['original']['elf'] == target['elf']]
        assert binding['original'] == target
        results.append(execute(elf, image, original, body, binding))
    return dict(unicorn_version=unicorn.__version__, targets=results)
