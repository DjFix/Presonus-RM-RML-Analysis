"""Execute the exact original ARM instructions in an offline sandbox."""
import hashlib
import io
import json
from pathlib import Path

from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import (
    Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE,
    UC_MEM_WRITE, UC_PROT_READ,
)
from unicorn.arm_const import (
    UC_ARM_REG_FP, UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_SP,
)

ELF = Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling-c001-20261124/packeting/next100-opportunistic02/snapshot/rootfs/RML16AI_Rack_13731/home/root/mixer')
ELF_SHA = '9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
NAME = '_ZN8Presonus5Panel14PanelRegistrar14getLcdPortNameEv'
ADDRESS, OFFSET, SECTION, SIZE = 0x52C24, 0x4AC24, 12, 24
BODY_SHA = 'a572376e0ee06bc343b7da8c80c3ad7485494648223905bde63169a725321b0a'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def execute(body, literal_address, literal, index):
    uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    receiver = 0x200100 + index * 0x40
    stack = 0x100000
    sp, fp, stop = stack + 0x800, stack + 0x880, 0x900000
    original_bytes = bytes((index + i) % 256 for i in range(64))
    for address in (ADDRESS, literal_address, receiver, stack, stop):
        uc.mem_map(address & ~0xfff, 0x1000)
    uc.mem_write(ADDRESS, body)
    uc.mem_write(literal_address, literal)
    uc.mem_protect(literal_address & ~0xfff, 0x1000, UC_PROT_READ)
    uc.mem_write(receiver, original_bytes)
    for register, value in ((UC_ARM_REG_SP, sp), (UC_ARM_REG_FP, fp),
                            (UC_ARM_REG_LR, stop), (UC_ARM_REG_R0, receiver)):
        uc.reg_write(register, value)
    accesses = []

    def trace(_uc, kind, address, size, value, _data):
        accesses.append([kind, address, size, value])

    uc.hook_add(UC_HOOK_MEM_READ | UC_HOOK_MEM_WRITE, trace)
    uc.emu_start(ADDRESS, stop, count=5)
    return_word = uc.reg_read(UC_ARM_REG_R0)
    assert return_word == literal_address
    assert uc.reg_read(UC_ARM_REG_PC) == stop
    assert uc.reg_read(UC_ARM_REG_SP) == sp and uc.reg_read(UC_ARM_REG_FP) == fp
    assert any(address == ADDRESS + 20 and size == 4 and kind != UC_MEM_WRITE
               for kind, address, size, _ in accesses)
    assert all(sp - 16 <= address and address + size <= sp or
               (kind != UC_MEM_WRITE and address == ADDRESS + 20 and size == 4)
               for kind, address, size, _ in accesses), accesses
    preserved = bytes(uc.mem_read(receiver, len(original_bytes))) == original_bytes
    assert preserved
    return dict(input=[0, -2147483648, 2147483647][index], receiver=receiver,
                r0=return_word, literal=bytes(uc.mem_read(return_word, len(literal))).hex(),
                receiver_preserved=preserved, accesses=accesses,
                registers=dict(sp=sp, fp=fp, lr=stop, return_pc=uc.reg_read(UC_ARM_REG_PC)))


def observations():
    data = ELF.read_bytes()
    assert digest(data) == ELF_SHA
    image = ELFFile(io.BytesIO(data))
    assert image['e_machine'] == 'EM_ARM' and image.little_endian and image.elfclass == 32
    section = image.get_section(SECTION)
    assert section.name == '.text' and section['sh_type'] == 'SHT_PROGBITS'
    symbols = image.get_section_by_name('.symtab').get_symbol_by_name(NAME)
    assert len([entry for entry in symbols if entry['st_shndx'] == SECTION
                and entry['st_value'] == ADDRESS and entry['st_size'] == SIZE
                and entry['st_info']['type'] == 'STT_FUNC']) == 1
    relative = ADDRESS - section['sh_addr']
    assert 0 <= relative <= section['sh_size'] - SIZE
    offset = section['sh_offset'] + relative
    body = data[offset:offset + SIZE]
    assert offset == OFFSET and digest(body) == BODY_SHA
    literal_address = int.from_bytes(body[-4:], 'little')
    containing = [s for s in image.iter_sections()
                  if s['sh_addr'] <= literal_address < s['sh_addr'] + s['sh_size']
                  and s['sh_flags'] & 2 and not s['sh_flags'] & 1
                  and s['sh_type'] == 'SHT_PROGBITS']
    assert len(containing) == 1 and containing[0].name == '.rodata'
    literal_section = containing[0]
    literal_offset = literal_section['sh_offset'] + literal_address - literal_section['sh_addr']
    limit = literal_section['sh_offset'] + literal_section['sh_size']
    end = data.index(b'\0', literal_offset, min(limit, literal_offset + 64))
    literal = data[literal_offset:end + 1]
    assert list(image.address_offsets(literal_address, len(literal))) == [literal_offset]
    cases = [execute(body, literal_address, literal, index) for index in range(3)]
    return dict(elf=str(ELF), elf_sha256=ELF_SHA, mangled=NAME, address=ADDRESS,
                size=SIZE, section=SECTION, section_name=section.name, file_offset=offset,
                firmware='RM/RML mixer 13731', role='server', body_sha256=BODY_SHA,
                body_hex=body.hex(), literal_offset=literal_offset,
                engine='Unicorn ' + unicorn.__version__, cases=cases)


if __name__ == '__main__':
    print(json.dumps(observations(), indent=2))
