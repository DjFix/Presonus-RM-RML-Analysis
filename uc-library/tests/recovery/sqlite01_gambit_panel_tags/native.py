"""Execute the SHA-bound original ARM method on mapped opaque receivers."""
import argparse
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import struct

from elftools.elf.elffile import ELFFile
import unicorn as uc
from unicorn.arm_const import (
    UC_ARM_REG_FP, UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0,
    UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_SP,
)

ELF_PATH = Path("rootfs/RML16AI_Rack_13731/home/root/mixer")
ELF_SHA256 = "9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07"
MANGLED = "_ZNK8Presonus5Panel20GambitPanelRegistrar7getTagsEiRi"
RANGE_SHA256 = "52014dc35dcb0a43c02dfc6dec01fdeeafcc563ba02addaa7295df3a7a57226c"
ADDRESS, SIZE, SECTION, FILE_OFFSET = 508600, 20, 12, 475832
PAGE, STACK, STOP = 0x1000, 0x700000, 0x800000
COUNT = 0xA00040
CASE_GROUPS = (-2147483648, -1, *range(17), 2147483647)
CASE_COUNTS = (-2147483648, -37, 0, 1, 2147483647)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def call(body, group, count, receiver, fill):
    machine = uc.Uc(uc.UC_ARCH_ARM, uc.UC_MODE_ARM)
    machine.mem_map(ADDRESS & -PAGE, PAGE, uc.UC_PROT_READ | uc.UC_PROT_EXEC)
    machine.mem_write(ADDRESS, body)
    machine.mem_map(STACK, PAGE)
    machine.mem_map(receiver, PAGE)
    machine.mem_map(COUNT & -PAGE, PAGE)
    receiver_bytes = bytes([fill]) * 64
    count_bytes = struct.pack("<IiI", 0xCADFBEDA, count, 0xDABEDFAC)
    machine.mem_write(receiver, receiver_bytes)
    machine.mem_write(COUNT - 4, count_bytes)
    sp, fp = STACK + PAGE - 16, 0x12345678
    registers = {
        UC_ARM_REG_R0: receiver, UC_ARM_REG_R1: group & 0xffffffff,
        UC_ARM_REG_R2: COUNT, UC_ARM_REG_SP: sp, UC_ARM_REG_LR: STOP, UC_ARM_REG_FP: fp,
    }
    for register, value in registers.items():
        machine.reg_write(register, value)

    trace, reads, writes = [], [], []

    def record_code(_, address, size, __):
        require(ADDRESS <= address and address + size <= ADDRESS + SIZE,
                "Instruction escaped the exact original method")
        trace.append(address)

    def record_access(_, access, address, size, value, __):
        require(sp - 16 <= address and address + size <= sp,
                "Data access escaped the stack frame")
        (reads if access == uc.UC_MEM_READ else writes).append([address - sp, size])

    machine.hook_add(uc.UC_HOOK_CODE, record_code)
    machine.hook_add(uc.UC_HOOK_MEM_READ | uc.UC_HOOK_MEM_WRITE, record_access)
    machine.emu_start(ADDRESS, STOP, count=16)
    require(machine.reg_read(UC_ARM_REG_PC) == STOP and
            machine.reg_read(UC_ARM_REG_SP) == sp and
            machine.reg_read(UC_ARM_REG_FP) == fp, "Return or frame restoration failed")
    require(trace == list(range(ADDRESS, ADDRESS + SIZE, 4)), "Unexpected ARM path")
    require(machine.mem_read(receiver, len(receiver_bytes)) == receiver_bytes,
            "Receiver bytes changed")
    left, final_count, right = struct.unpack("<IiI", machine.mem_read(COUNT - 4, 12))
    require((left, right) == (0xCADFBEDA, 0xDABEDFAC), "Count canaries changed")
    return dict(group=group, count_before=count, count_after=final_count,
                return_word=machine.reg_read(UC_ARM_REG_R0), receiver=receiver,
                receiver_fill=fill, instruction_trace=trace, stack_reads=reads,
                stack_writes=writes, count_canaries_preserved=True,
                receiver_preserved=True)


def observe(path):
    raw = path.read_bytes()
    require(sha256(raw).hexdigest() == ELF_SHA256, "Original ELF hash mismatch")
    elf = ELFFile(BytesIO(raw))
    require(elf.elfclass == 32 and elf.little_endian and elf["e_machine"] == "EM_ARM",
            "Expected 32-bit little-endian ARM ELF")
    matching = elf.get_section_by_name(".symtab").get_symbol_by_name(MANGLED)
    require(matching and len(matching) == 1, "Original symbol missing or ambiguous")
    symbol = matching[0]
    require((symbol["st_value"], symbol["st_size"], symbol["st_shndx"],
             symbol["st_info"]["type"]) == (ADDRESS, SIZE, SECTION, "STT_FUNC"),
            "Original symbol tuple mismatch")
    section = elf.get_section(SECTION)
    displacement = ADDRESS - section["sh_addr"]
    offset = section["sh_offset"] + displacement
    require(section.name == ".text" and section["sh_flags"] & 4 and
            0 <= displacement <= section["sh_size"] - SIZE and offset == FILE_OFFSET,
            "Original ELF section mapping mismatch")
    body = raw[offset:offset + SIZE]
    require(sha256(body).hexdigest() == RANGE_SHA256, "Original range hash mismatch")
    cases = [call(body, group, count, receiver, fill)
             for group in CASE_GROUPS for count in CASE_COUNTS
             for receiver, fill in ((0x900000, 0x31), (0x901000, 0xA9))]
    return dict(elf_sha256=ELF_SHA256, elf=str(ELF_PATH), firmware="RM/RML mixer 13731",
                role="server", mangled=MANGLED, address=ADDRESS, size=SIZE,
                section=SECTION, section_name=section.name, range_sha256=RANGE_SHA256,
                range_hex=body.hex(), file_offset=offset, unicorn_version=uc.__version__,
                cases=cases)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--elf", type=Path, required=True)
    parser.add_argument("--write", type=Path, required=True)
    arguments = parser.parse_args()
    result = observe(arguments.elf)
    with arguments.write.open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(f"PASS {len(result['cases'])} exact original ARM invocations")
