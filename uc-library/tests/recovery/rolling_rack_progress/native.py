"""Execute the original ARM callback, float helpers and UART encoder offline."""
import hashlib
import io
import json
from pathlib import Path
import struct

from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE
from unicorn.arm_const import (
    UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_SP,
)

ELF = Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling-c001-20261124/packeting/next09/snapshot/rootfs/RML16AI_Rack_13731/home/root/mixer')
ELF_SHA = '9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
NAME = '_ZN8Presonus5Mixer20RackMixerApplication10onProgressEPKcf'
ADDRESS, OFFSET, SIZE, SECTION = 0x7ca64, 0x74a64, 112, 12
BODY_SHA = '1a05ad440ea45596a36750df4ab03cb63126234671123d4b977648ba7c5dac0c'
PROVIDERS = {'__aeabi_fmul': 0x157550, '__aeabi_f2uiz': 0x1579b4,
             'uart_protocol_encode': None}
RACK, REGISTRAR, PORT, TABLE1, TABLE2, TITLE, WIRE = (0x600000 + i * 256 for i in range(7))
STACK = 0x700800
STOP, GET_PORT, WRITE_MSG = 0x800000, 0x800100, 0x800200


def digest(data):
    return hashlib.sha256(data).hexdigest()


def ranges(elf, name, expected=None):
    symbols = elf.get_section_by_name('.symtab').get_symbol_by_name(name)
    matches = [symbol for symbol in symbols if symbol['st_info']['type'] == 'STT_FUNC'
               and symbol['st_shndx'] == SECTION
               and (expected is None or symbol['st_value'] == expected)]
    assert len(matches) == 1, (name, expected, matches)
    section = elf.get_section(SECTION)
    assert section.name == '.text' and section['sh_type'] == 'SHT_PROGBITS'
    symbol = matches[0]
    address, size = symbol['st_value'], symbol['st_size']
    relative = address - section['sh_addr']
    offset = section['sh_offset'] + relative
    assert 0 <= relative <= section['sh_size'] - size
    body = section.data()[relative:relative + size]
    return dict(mangled=name, address=address, size=size, section=SECTION,
                file_offset=offset, body_sha256=digest(body))


def put_word(cpu, address, number):
    cpu.mem_write(address, struct.pack('<I', number))


def run_case(elf, providers, bits, has_port, title_kind):
    cpu = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    segments = [segment for segment in elf.iter_segments() if segment['p_type'] == 'PT_LOAD']
    low = min(segment['p_vaddr'] for segment in segments) & ~4095
    high = max(segment['p_vaddr'] + segment['p_memsz'] + 4095 for segment in segments) & ~4095
    cpu.mem_map(low, high - low)
    for segment in segments:
        cpu.mem_write(segment['p_vaddr'], segment.data())
    for page in (RACK, STACK & ~4095, STOP):
        cpu.mem_map(page, 4096)
    cpu.mem_write(TITLE, b'synthetic progress title\0')
    put_word(cpu, RACK + 0x1c, REGISTRAR)
    put_word(cpu, REGISTRAR, TABLE1)
    put_word(cpu, PORT, TABLE2)
    put_word(cpu, TABLE1 + 0x50, GET_PORT)
    put_word(cpu, TABLE2 + 4, WRITE_MSG)
    title = (0, TITLE, TITLE + 10)[title_kind]
    for reg, value in ((UC_ARM_REG_SP, STACK), (UC_ARM_REG_LR, STOP), (UC_ARM_REG_R0, RACK),
                       (UC_ARM_REG_R1, title), (UC_ARM_REG_R2, bits)):
        cpu.reg_write(reg, value)

    events, messages, title_reads = [], [], []

    def observe_code(machine, address, _, _user):
        if address == GET_PORT:
            assert machine.reg_read(UC_ARM_REG_R0) == REGISTRAR
            events.append('get')
            machine.reg_write(UC_ARM_REG_R0, PORT if has_port else 0)
        elif address == WRITE_MSG:
            assert machine.reg_read(UC_ARM_REG_R0) == PORT
            message = machine.reg_read(UC_ARM_REG_R1)
            assert STACK - 32 <= message <= STACK - 4
            messages.append(bytes(machine.mem_read(message, 4)))
            events.append('write')
            machine.reg_write(UC_ARM_REG_R0, 1)
        else:
            return
        machine.reg_write(UC_ARM_REG_PC, machine.reg_read(UC_ARM_REG_LR))

    def observe_memory(_machine, _kind, address, size, _value, _user):
        if address < TITLE + 256 and address + size > TITLE:
            title_reads.append(address)

    cpu.hook_add(UC_HOOK_CODE, observe_code, begin=GET_PORT, end=WRITE_MSG)
    cpu.hook_add(UC_HOOK_MEM_READ | UC_HOOK_MEM_WRITE, observe_memory)
    cpu.emu_start(ADDRESS, STOP, count=1000)
    assert cpu.reg_read(UC_ARM_REG_PC) == STOP
    assert cpu.reg_read(UC_ARM_REG_SP) == STACK
    assert events == (['get', 'write'] if has_port else ['get']) and not title_reads

    wire = b''
    if messages:
        message = messages[0]
        assert message[:2] == b'\x67\x0c'
        cpu.mem_write(RACK, message)
        for reg, value in ((UC_ARM_REG_SP, STACK), (UC_ARM_REG_LR, STOP), (UC_ARM_REG_R0, RACK),
                           (UC_ARM_REG_R1, WIRE)):
            cpu.reg_write(reg, value)
        cpu.emu_start(providers['uart_protocol_encode']['address'], STOP, count=1000)
        assert cpu.reg_read(UC_ARM_REG_PC) == STOP
        count = cpu.reg_read(UC_ARM_REG_R0)
        assert 0 < count <= 16
        wire = bytes(cpu.mem_read(WIRE, count))

    return dict(bits=bits, has_port=has_port, title_kind=title_kind, events=events,
                messages=[message.hex() for message in messages], wire=wire.hex())


def observations():
    data = ELF.read_bytes()
    assert digest(data) == ELF_SHA
    elf = ELFFile(io.BytesIO(data))
    assert elf['e_machine'] == 'EM_ARM' and elf.little_endian and elf.elfclass == 32
    original = ranges(elf, NAME, ADDRESS)
    assert (original['file_offset'], original['size'], original['body_sha256']) == (OFFSET, SIZE, BODY_SHA)
    providers = {name: ranges(elf, name, address) for name, address in PROVIDERS.items()}
    # Binary32 values near the 1/16, 1/2 and 1.0 truncation boundaries.
    samples = [0x00000000, 0x80000000, 0x3d7fffff, 0x3d800000, 0x3d800001,
               0x3effffff, 0x3f000000, 0x3f000001, 0x3f7fffff, 0x3f800000]
    cases = [run_case(elf, providers, bits, has_port, (at + has_port) % 3)
             for at, bits in enumerate(samples) for has_port in (False, True)]
    return dict(original, records=providers, elf=str(ELF), elf_sha256=ELF_SHA, engine='Unicorn ' + unicorn.__version__,
                firmware='RM/RML mixer 13731', role='server', cases=cases)


if __name__ == '__main__':
    print(json.dumps(observations(), indent=2))
