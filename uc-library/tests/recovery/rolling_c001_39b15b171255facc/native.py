"""Verify an original ELF symbol range and execute its ARM instructions offline."""
import hashlib
import io
import json
import struct
from pathlib import Path

from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE
from unicorn.arm_const import (
    UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_R4,
    UC_ARM_REG_R5, UC_ARM_REG_R6, UC_ARM_REG_R7, UC_ARM_REG_R8, UC_ARM_REG_R9,
    UC_ARM_REG_R10, UC_ARM_REG_FP, UC_ARM_REG_LR, UC_ARM_REG_SP, UC_ARM_REG_PC,
)

ELF = Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling-c001-20261124/packeting/next09/snapshot/rootfs/CS18_v13840/home/root/surface')
ELF_SHA = '304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
NAME = '_ZN8Presonus7Surface20SurfaceRootComponent14networkChangedERKNS_11WIFIManagerE'
ADDRESS = 0xacfac
OFFSET = 0xa4fac
SECTION = 12
SIZE = 16
BODY_SHA = '60cf0e8b51daf6a0ce5a5eea619d9a3e219bccf7fa26c553983e5baf3012cfad'
TABLE_LOCATIONS = (1985456,)
ARGUMENT_KINDS = ['ref']
REGISTERS = (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3,
             UC_ARM_REG_R4, UC_ARM_REG_R5, UC_ARM_REG_R6, UC_ARM_REG_R7,
             UC_ARM_REG_R8, UC_ARM_REG_R9, UC_ARM_REG_R10, UC_ARM_REG_FP,
             UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def execute(body, index):
    uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    stack = 0x100000
    sp, fp, return_pc = stack + 0x800, stack + 0x880, 0x900000
    data = 0x200000
    receiver = data + 0x100 + index * 0x20
    registrar = data + 0x400
    pointer = data + 0x600
    scalar_values = {
        "int": (0, -2147483648, 2147483647),
        "bool": (0, 1, 0),
        "float": (0, 0.5, -2),
        "uchar": (0, 127, 255),
        "ushort": (0, 32768, 65535),
    }
    arguments = [receiver]
    case_inputs = []
    blocks = {"receiver": (receiver, bytes(range(64)))}
    for number, kind in enumerate(ARGUMENT_KINDS):
        if kind == "ref":
            arguments.append(registrar)
            blocks["registrar"] = (registrar, bytes(range(32, 96)))
        elif kind in scalar_values:
            values = scalar_values[kind]
            value = values[0 if index == 0 else 1 + ((index - 1 + number) % 2)]
            case_inputs.append(value)
            if kind == "float":
                arguments.append(int.from_bytes(struct.pack("<f", value), "little"))
            else:
                arguments.append(value & 0xffffffff)
        else:
            present = index != 0
            case_inputs.append(int(present))
            arguments.append(pointer if present else 0)
            if present:
                blocks["pointed"] = (pointer, bytes.fromhex("a51f9842") * 16)
    stack_arguments = arguments[4:]
    register_arguments = (arguments + [0x74121000 + index] * 4)[:4]
    initial = [*register_arguments, *[0x81827300 + ordinal + index * 32 for ordinal in range(7)],
               fp, sp, return_pc, ADDRESS]
    uc.mem_map(ADDRESS & ~0xfff, 0x1000)
    uc.mem_map(return_pc, 0x1000)
    uc.mem_map(stack, 0x1000)
    uc.mem_map(data, 0x1000)
    uc.mem_write(ADDRESS, body)
    for number, value in enumerate(stack_arguments):
        uc.mem_write(sp + 4 * number, value.to_bytes(4, "little"))
    for start, contents in blocks.values():
        uc.mem_write(start, contents)
    for register, value in zip(REGISTERS, initial):
        uc.reg_write(register, value)

    accesses = []

    def record(_uc, kind, address, size, value, _data):
        accesses.append([kind, address, size, value])

    uc.hook_add(UC_HOOK_MEM_READ | UC_HOOK_MEM_WRITE, record)
    uc.emu_start(ADDRESS, return_pc, count=4)
    final = [uc.reg_read(register) for register in REGISTERS]
    assert final == [*initial[:-1], return_pc], final
    assert accesses and all(sp - 16 <= address and address + size <= sp
                            for _, address, size, _ in accesses), accesses
    sentinels = {}
    for label, (start, contents) in blocks.items():
        final_contents = bytes(uc.mem_read(start, len(contents)))
        assert contents == final_contents, label
        sentinels[label] = dict(address=start, before=contents.hex(), after=final_contents.hex())
    return dict(index=index, inputs=case_inputs, stack_arguments=stack_arguments, input_registers=initial,
                output_registers=final, accesses=accesses, sentinels=sentinels)


def verified_table_words(elf):
    return [
        dict(address=address, file_offset=offset, value=int.from_bytes(word, "little"))
        for address in TABLE_LOCATIONS
        for offset in elf.address_offsets(address, 4)
        for word in (elf.stream.getbuffer()[offset:offset + 4],)
    ]


def observations():
    data = ELF.read_bytes()
    assert digest(data) == ELF_SHA
    file = ELFFile(io.BytesIO(data))
    section = file.get_section(SECTION)
    assert file["e_machine"] == "EM_ARM" and file.little_endian and file.elfclass == 32
    assert section.name == ".text" and section["sh_type"] == "SHT_PROGBITS"
    symbols = file.get_section_by_name(".symtab").get_symbol_by_name(NAME)
    matches = [row for row in symbols if row["st_shndx"] == SECTION
               and row["st_value"] == ADDRESS and row["st_size"] == SIZE
               and row["st_info"]["type"] == "STT_FUNC"]
    assert len(matches) == 1
    relative = ADDRESS - section["sh_addr"]
    assert 0 <= relative <= section["sh_size"] - SIZE
    offset = section["sh_offset"] + relative
    body = data[offset:offset + SIZE]
    assert offset == OFFSET and digest(body) == BODY_SHA
    words = verified_table_words(file)
    assert len(words) == len(TABLE_LOCATIONS)
    assert all(word["value"] == ADDRESS for word in words), words
    return dict(elf=str(ELF), elf_sha256=ELF_SHA, mangled=NAME, address=ADDRESS, size=SIZE,
                section=SECTION, firmware='CS18AI surface 13840', role='client', section_name=section.name, file_offset=offset, body_sha256=BODY_SHA,
                body_hex=body.hex(), table_words=words, engine="Unicorn " + unicorn.__version__,
                cases=[execute(body, index) for index in range(3)])


if __name__ == "__main__":
    print(json.dumps(observations(), indent=2))
