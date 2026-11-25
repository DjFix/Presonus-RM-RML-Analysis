"""Execute the sealed RM GEQ label regeneration body at named call boundaries."""
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
from struct import pack, unpack

from elftools.elf.elffile import ELFFile
from unicorn import UC_ARCH_ARM, UC_HOOK_CODE, UC_MODE_ARM, Uc
from unicorn.arm_const import (UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0,
                               UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3,
                               UC_ARM_REG_SP)

TASK = 'sqlite_gequi_name_list'
TEST = Path('uc-library/tests/recovery') / TASK
LOCAL_PACKET = Path('temp/recovery-work/sqlite-issued/packet') / TASK / 'CONTEXT.json'
CANONICAL_PACKET = (Path('temp/recovery-work/rolling-c001-20261124/packeting')
                    / 'sqlite-cycle02/gequi_name_list01/packet/tasks'
                    / TASK / 'CONTEXT.json')
PACKET = LOCAL_PACKET if LOCAL_PACKET.is_file() else CANONICAL_PACKET
PACKET_SHA = '10545435989d592ada331cf6b0059becae43d1edab0e92a7873fe1bb5e17329b'
OBJECT, MIXER, LIST, TABLE = 0x1000000, 0x1001000, 0x1002000, 0x1003000
GET, SET, STOP, STACK = 0x1004000, 0x1004004, 0x1004008, 0x1008000
REMOVE = '_ZN4Core8Portable9ListParam9removeAllEv'
APPEND = '_ZN4Core8Portable9ListParam12appendStringEPKc'
FORMAT = '_ZN4Core20MutableCStringTraitsINS_13CStringBufferILi128EEEE12appendFormatEPKcz'
LINK = '_ZN8Presonus5Panel14GeqUIComponent15isChannelLinkedEj'
INPUTS = [('', 0), ('', 2), ('0', 7), ('0', 0), ('1', 0), ('00', 1), ('11', 1), ('01', 1),
          ('10', 0), ('00111000', 7), ('11000111', 4), ('0101010101010010', 13),
          ('0' * 256 + '11', 256)]


def digest(raw):
    return sha256(raw).hexdigest()


def run():
    context = PACKET.read_bytes()
    assert digest(context) == PACKET_SHA
    original, = (row['original'] for row in json.loads(context)['originals'])
    raw = Path(original['elf_path']).read_bytes()
    assert digest(raw) == original['elf']
    elf = ELFFile(BytesIO(raw))
    section = elf.get_section(original['section'])
    symbols = elf.get_section_by_name('.symtab')
    symbol, = symbols.get_symbol_by_name(original['mangled'])
    address, size = symbol['st_value'], symbol['st_size']
    assert (address, size, symbol['st_shndx'], section.name) == (
        original['address'], original['size'], original['section'], original['section_name'])
    delta = address - section['sh_addr']
    assert 0 <= delta <= section['sh_size'] - size
    offset = section['sh_offset'] + delta
    body = raw[offset:offset + size]
    assert offset == original['file_offset']
    assert body.hex() == original['range_hex'] and digest(body) == original['range_sha256']
    calls = {}
    for expected, name in ((0x11f9a0, REMOVE), (0x11ecd8, APPEND),
                           (0x12af4, FORMAT), (0x70d78, LINK)):
        assert any(sym['st_value'] == expected for sym in symbols.get_symbol_by_name(name)), name
        calls[expected] = name

    rx = next(segment for segment in elf.iter_segments()
              if segment['p_type'] == 'PT_LOAD' and segment['p_flags'] & 1)

    def case(links, selection):
        uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        base = rx['p_vaddr']
        assert base % 4096 == 0
        uc.mem_map(base, (rx['p_memsz'] + 4095) & ~4095)
        uc.mem_write(base, rx.data())
        uc.mem_map(OBJECT, 0x9000)
        for addr, value in ((OBJECT + 0x8c, LIST), (OBJECT + 0x90, MIXER),
                            (MIXER + 0x2b4, len(links)), (LIST, TABLE),
                            (TABLE + 0x44, GET), (TABLE + 0x58, SET)):
            uc.mem_write(addr, pack('<I', value))
        uc.reg_write(UC_ARM_REG_R0, OBJECT)
        uc.reg_write(UC_ARM_REG_SP, STACK)
        uc.reg_write(UC_ARM_REG_LR, STOP)
        reads, labels, trace = [], [], []

        def string(ptr):
            data = bytes(uc.mem_read(ptr, 128))
            assert 0 in data
            return data[:data.index(0)].decode('ascii')

        def handle(engine, ip, size, _):
            if address <= ip < address + len(body) - 20:
                return
            r0, r1, r2, r3 = (engine.reg_read(x) for x in
                              (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3))
            if ip in (GET, SET, 0x11f9a0, 0x11ecd8):
                assert r0 == LIST
            if ip == GET:
                trace.append(['get', selection])
                engine.reg_write(UC_ARM_REG_R0, unpack('<I', pack('<f', selection))[0])
            elif ip == SET:
                trace.append(['set', unpack('<f', pack('<I', r1))[0], r2])
            elif ip == 0x11f9a0:
                trace.append(['remove'])
            elif ip == 0x11ecd8:
                labels.append(string(r1))
                trace.append(['append', labels[-1]])
            elif ip == 0x12af4:
                fmt = string(r1)
                signed = tuple(unpack('<i', pack('<I', word))[0] for word in (r2, r3))
                args = signed[:fmt.count('%d')]
                trace.append(['format', fmt, *args])
                engine.mem_write(r0, (string(r0) + fmt % args).encode('ascii') + b'\0')
            elif ip == 0x70d78:
                assert r0 == OBJECT and r1 < len(links)
                reads.append(r1)
                engine.reg_write(UC_ARM_REG_R0, int(links[r1]))
            else:
                raise AssertionError(f'Unexpected instruction address {ip:#x}')
            engine.reg_write(UC_ARM_REG_PC, engine.reg_read(UC_ARM_REG_LR))

        uc.hook_add(UC_HOOK_CODE, handle)
        uc.emu_start(address, STOP, count=50000)
        assert uc.reg_read(UC_ARM_REG_PC) == STOP
        assert trace[0] == ['get', selection] and trace[1] == ['remove']
        assert trace[-1][0] == 'set'
        return dict(links=links, selection=selection, link_indices=reads, labels=labels,
                    restore=trace[-1][1:], boundary_trace=trace)

    return dict(original=original, direct_calls={hex(ip): name for ip, name in calls.items()},
                cases=[case(*args) for args in INPUTS])


if __name__ == '__main__':
    print(json.dumps(run(), indent=2))
