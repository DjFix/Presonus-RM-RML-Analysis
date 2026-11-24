"""Observe the bound ARM function in a closed, offline emulator."""
import hashlib
import io
import json
from pathlib import Path

from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import arm_const as arm

ELF = Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling-c001-20261124/packeting/next100-opportunistic02/snapshot/rootfs/RML16AI_Rack_13731/home/root/mixer')
ELF_SHA = '9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
MANGLED = '_ZN8Presonus5Panel19RoguePanelRegistrar16getPanelPortNameEv'
ADDRESS, OFFSET, RETURN_WORD = 0x7944c, 0x7144c, 0x3199e4
BODY_SHA = 'a572376e0ee06bc343b7da8c80c3ad7485494648223905bde63169a725321b0a'
REGISTERS = [getattr(arm, f'UC_ARM_REG_R{i}') for i in range(11)] + [
    arm.UC_ARM_REG_FP, arm.UC_ARM_REG_SP, arm.UC_ARM_REG_LR, arm.UC_ARM_REG_PC,
]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def execute(body, literal, index):
    uc = unicorn.Uc(unicorn.UC_ARCH_ARM, unicorn.UC_MODE_ARM)
    stack, receiver_page, return_pc = 0x100000, 0x200000, 0x900000
    sp, fp = stack + 0x800, stack + 0x880
    receiver = receiver_page + 0x100 + index * 0x80
    sentinel = bytes((value + index) % 256 for value in range(64))
    initial = [receiver, *[0x81827300 + i + index * 32 for i in range(10)],
               fp, sp, return_pc, ADDRESS]
    for page in (ADDRESS & ~0xfff, RETURN_WORD & ~0xfff, stack, receiver_page):
        uc.mem_map(page, 0x1000)
    uc.mem_write(ADDRESS, body)
    uc.mem_write(RETURN_WORD, literal)
    uc.mem_write(receiver, sentinel)
    uc.mem_protect(ADDRESS & ~0xfff, 0x1000, unicorn.UC_PROT_READ | unicorn.UC_PROT_EXEC)
    uc.mem_protect(RETURN_WORD & ~0xfff, 0x1000, unicorn.UC_PROT_READ)
    for register, value in zip(REGISTERS, initial):
        uc.reg_write(register, value)

    trace, accesses = [], []
    uc.hook_add(unicorn.UC_HOOK_CODE,
                lambda _uc, pc, size, _: trace.append([pc, size]))
    uc.hook_add(unicorn.UC_HOOK_MEM_READ | unicorn.UC_HOOK_MEM_WRITE,
                lambda _uc, kind, address, size, value, _: accesses.append(
                    [kind, address, size, value]))
    uc.emu_start(ADDRESS, return_pc, count=5)
    final = [uc.reg_read(register) for register in REGISTERS]
    assert final == [RETURN_WORD, *initial[1:-1], return_pc], final
    assert trace == [[ADDRESS + 4 * i, 4] for i in range(5)], trace
    pool_reads = []
    for kind, address, size, _ in accesses:
        if kind == unicorn.UC_MEM_READ and address == ADDRESS + 20 and size == 4:
            pool_reads.append(address)
        else:
            assert sp - 16 <= address and address + size <= sp, accesses
    assert pool_reads == [ADDRESS + 20], accesses
    after = bytes(uc.mem_read(receiver, len(sentinel)))
    assert after == sentinel
    return dict(input_registers=initial, output_registers=final, return_word=final[0],
                trace=trace, memory_accesses=accesses, receiver_before=sentinel.hex(),
                receiver_after=after.hex())


def observations():
    data = ELF.read_bytes()
    assert digest(data) == ELF_SHA
    elf = ELFFile(io.BytesIO(data))
    assert elf['e_machine'] == 'EM_ARM' and elf.little_endian and elf.elfclass == 32
    section = elf.get_section(12)
    assert section.name == '.text' and section['sh_type'] == 'SHT_PROGBITS'
    symbols = elf.get_section_by_name('.symtab').get_symbol_by_name(MANGLED)
    assert len([row for row in symbols if row['st_shndx'] == 12
                and row['st_value'] == ADDRESS and row['st_size'] == 24
                and row['st_info']['type'] == 'STT_FUNC']) == 1
    relative = ADDRESS - section['sh_addr']
    assert 0 <= relative <= section['sh_size'] - 24
    offset = section['sh_offset'] + relative
    body = data[offset:offset + 24]
    assert offset == OFFSET and digest(body) == BODY_SHA
    assert int.from_bytes(body[20:], 'little') == RETURN_WORD
    rodata = elf.get_section_by_name('.rodata')
    assert rodata['sh_type'] == 'SHT_PROGBITS' and rodata['sh_flags'] & 3 == 2
    relative = RETURN_WORD - rodata['sh_addr']
    assert 0 <= relative < rodata['sh_size']
    literal_offset = rodata['sh_offset'] + relative
    literal_end = data.index(0, literal_offset, rodata['sh_offset'] + rodata['sh_size'])
    literal = data[literal_offset:literal_end + 1]
    assert list(elf.address_offsets(RETURN_WORD, len(literal))) == [literal_offset]
    assert any(seg['p_type'] == 'PT_LOAD' and seg['p_flags'] & 6 == 4
               and seg['p_vaddr'] <= RETURN_WORD
               and RETURN_WORD + len(literal) <= seg['p_vaddr'] + seg['p_filesz']
               for seg in elf.iter_segments())
    return dict(elf=str(ELF), elf_sha256=ELF_SHA, mangled=MANGLED, address=ADDRESS,
                size=len(body), section=12, section_name=section.name, file_offset=offset,
                body_sha256=BODY_SHA, body_hex=body.hex(), return_word=RETURN_WORD,
                literal_file_offset=literal_offset, literal_hex=literal.hex(),
                text=literal[:-1].decode('ascii'), engine='Unicorn ' + unicorn.__version__,
                cases=[execute(body, literal, index) for index in range(3)])


if __name__ == '__main__':
    print(json.dumps(observations(), indent=2))
