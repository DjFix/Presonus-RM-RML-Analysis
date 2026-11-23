"""Execute the exact offline ARM32 Book entries with guarded synthetic receivers."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import struct

import elftools
from elftools.elf.elffile import ELFFile
import unicorn as uc
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_SP

MANGLED = '_ZN8Presonus5Panel4Book10togglePageEv'
GETTER = False
ORIGINS = (
    ('304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0',
     'CS18AI surface 13840', 'client', 0x20dac, 16,
     '60cf0e8b51daf6a0ce5a5eea619d9a3e219bccf7fa26c553983e5baf3012cfad'),
    ('9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07',
     'RM/RML mixer 13731', 'server', 0x6eb8c, 16,
     '60cf0e8b51daf6a0ce5a5eea619d9a3e219bccf7fa26c553983e5baf3012cfad'),
)
TAGS = (0, 1, -1, 2147483647, -2147483648, 305419896, -123456789)
RECEIVER = 0x400000
STACK = 0x500000
RETURN = 0x600000


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def target(path, origin):
    elf_sha, firmware, role, address, size, range_sha = origin
    image = path.read_bytes()
    require(digest(image) == elf_sha, f"Unexpected ELF hash for {path}")
    elf = ELFFile(io.BytesIO(image))
    require(elf.elfclass == 32 and elf.little_endian
            and elf['e_machine'] == 'EM_ARM', f"Unexpected ELF architecture for {path}")
    sections = getattr(elf.get_section_by_name('.symtab'), 'get_symbol_by_name')
    symbols = sections(MANGLED)
    require(symbols and len(symbols) == 1, f"Expected unique {MANGLED} in {path}")
    symbol = symbols[0]
    section_index = symbol['st_shndx']
    section = elf.get_section(section_index)
    relative = address - section['sh_addr']
    require((symbol['st_value'], symbol['st_size'], section_index, section.name,
             symbol['st_info']['type']) == (address, size, 12, '.text', 'STT_FUNC'),
            f"Unexpected symbol range for {path}")
    require(section['sh_type'] == 'SHT_PROGBITS' and 0 <= relative <= section['sh_size'] - size,
            f"Symbol range falls outside its ELF section in {path}")
    offset = section['sh_offset'] + relative
    body = image[offset:offset + size]
    require(digest(body) == range_sha, f"Unexpected original instruction bytes in {path}")
    return body, dict(original_elf_sha256=elf_sha, firmware=firmware, role=role,
                      mangled=MANGLED, address=address, size=size, section='.text',
                      section_index=section_index, file_offset=offset, range_sha256=range_sha)


def run(address, body, tag, pattern):
    machine = uc.Uc(uc.UC_ARCH_ARM, uc.UC_MODE_ARM)
    machine.mem_map(address & ~0xfff, 0x2000, uc.UC_PROT_READ | uc.UC_PROT_EXEC)
    machine.mem_write(address, body)
    machine.mem_map(RECEIVER, 0x1000, uc.UC_PROT_READ)
    receiver = bytearray((pattern + index * 11) & 0xff for index in range(0x1000))
    struct.pack_into('<i', receiver, 0x8c, tag)
    machine.mem_write(RECEIVER, bytes(receiver))
    machine.mem_map(STACK, 0x1000, uc.UC_PROT_READ | uc.UC_PROT_WRITE)
    machine.mem_map(RETURN, 0x1000, uc.UC_PROT_READ | uc.UC_PROT_EXEC)
    machine.reg_write(UC_ARM_REG_R0, RECEIVER)
    machine.reg_write(UC_ARM_REG_SP, STACK + 0x800)
    machine.reg_write(UC_ARM_REG_LR, RETURN)
    trace = []
    receiver_accesses = []

    def instruction(_, pc, width, __):
        require(address <= pc < address + len(body) and width == 4,
                f"Execution left exact original body at {pc:#x}")
        trace.append(pc)

    def memory(_, access, where, size, __, ___):
        if RECEIVER <= where < RECEIVER + 0x1000:
            receiver_accesses.append([access, where - RECEIVER, size])
        else:
            require(STACK <= where and where + size <= STACK + 0x1000,
                    f"Unexpected external data access at {where:#x}")

    machine.hook_add(uc.UC_HOOK_CODE, instruction)
    machine.hook_add(uc.UC_HOOK_MEM_READ | uc.UC_HOOK_MEM_WRITE, memory)
    machine.emu_start(address, RETURN, count=20)
    require(machine.reg_read(UC_ARM_REG_PC) == RETURN and
            machine.reg_read(UC_ARM_REG_SP) == STACK + 0x800,
            "Original did not return normally with balanced stack")
    require(machine.mem_read(RECEIVER, len(receiver)) == receiver,
            "Original changed receiver bytes")
    expected_accesses = [[uc.UC_MEM_READ, 0x8c, 4]] if GETTER else []
    require(receiver_accesses == expected_accesses, "Unexpected receiver accesses")
    return dict(tag=tag, receiver_pattern=pattern,
                word=machine.reg_read(UC_ARM_REG_R0) if GETTER else None,
                receiver_unchanged=True, receiver_accesses=receiver_accesses,
                trace=trace)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cs18', required=True, type=Path)
    parser.add_argument('--rm', required=True, type=Path)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--write', type=Path)
    action.add_argument('--check', type=Path)
    args = parser.parse_args()
    fixtures = {'unicorn': uc.__version__, 'pyelftools': elftools.__version__, 'originals': []}
    for path, origin in zip((args.cs18, args.rm), ORIGINS, strict=True):
        body, row = target(path, origin)
        row['cases'] = [run(row['address'], body, value, 31 * index)
                        for index, value in enumerate(TAGS)]
        fixtures['originals'].append(row)
    if args.write:
        with args.write.open('x') as output:
            json.dump(fixtures, output, indent=2)
            output.write('\n')
    else:
        require(json.loads(args.check.read_text()) == fixtures,
                "Fresh independent native observations differ from sealed fixtures")
    print(f"{len(TAGS)} exact ARM observations for each of {len(ORIGINS)} ELF identities")


if __name__ == '__main__':
    main()
