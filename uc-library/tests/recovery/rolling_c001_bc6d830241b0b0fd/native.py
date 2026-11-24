"""Re-observe the sealed RackPanelComponent ARM method offline."""
import argparse
import hashlib
import json
from pathlib import Path

from elftools.elf.elffile import ELFFile
from unicorn import UC_ARCH_ARM, UC_HOOK_MEM_WRITE, UC_MODE_ARM, Uc, __version__
from unicorn.arm_const import (
    UC_ARM_REG_FP, UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_SP,
    UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3,
    UC_ARM_REG_R4, UC_ARM_REG_R5, UC_ARM_REG_R6, UC_ARM_REG_R7,
    UC_ARM_REG_R8, UC_ARM_REG_R9, UC_ARM_REG_R10,
)

ELF_HASH = "9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07"
BODY_HASH = "60cf0e8b51daf6a0ce5a5eea619d9a3e219bccf7fa26c553983e5baf3012cfad"
SYMBOL = "_ZN8Presonus5Panel18RackPanelComponent16processLinkEventERNS_8Intercom9LinkEventE"
ADDRESS = 0x7CEF0
RETURN = ADDRESS + 16
STACK = 0x301000


def observe(body, case, receiver, event, word):
    cpu = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    cpu.mem_map(ADDRESS & ~0xfff, 0x1000)
    cpu.mem_write(ADDRESS, body)
    cpu.mem_map(0x200000, 0x4000)
    cpu.mem_map(STACK - 0x1000, 0x1000)
    objects = {receiver: bytes((0xa5,)) * 64,
               event: word.to_bytes(4, "little") + bytes((0x5a,)) * 60}
    for address, data in objects.items():
        cpu.mem_write(address, data)
    registers = dict(zip(
        (UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_R4, UC_ARM_REG_R5,
         UC_ARM_REG_R6, UC_ARM_REG_R7, UC_ARM_REG_R8, UC_ARM_REG_R9,
         UC_ARM_REG_R10, UC_ARM_REG_FP),
        range(0x1234 + case, 0x123e + case), strict=True,
    ))
    registers.update({UC_ARM_REG_SP: STACK, UC_ARM_REG_LR: RETURN,
                      UC_ARM_REG_R0: receiver, UC_ARM_REG_R1: event})
    for register, value in registers.items():
        cpu.reg_write(register, value)
    writes = []
    cpu.hook_add(UC_HOOK_MEM_WRITE,
                 lambda _, access, address, size, value, data:
                     writes.append((address, size, value)))
    cpu.emu_start(ADDRESS, RETURN, count=4)
    if cpu.reg_read(UC_ARM_REG_PC) != RETURN:
        raise ValueError("Original did not return to LR")
    if any(cpu.reg_read(register) != value for register, value in registers.items()):
        raise ValueError("Unexpected register change")
    if [(address, size) for address, size, _ in writes] != [
        (STACK + offset, 4) for offset in (-16, -12, -8, -4)
    ]:
        raise ValueError("Unexpected native write range")
    if any(bytes(cpu.mem_read(address, len(data))) != data
           for address, data in objects.items()):
        raise ValueError("Receiver or event changed")
    return {"receiver": receiver, "event": event, "sentinel": word,
            "stack_writes": writes, "portable_observation": "unchanged"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--elf", type=Path, required=True)
    parser.add_argument("--verify", type=Path)
    args = parser.parse_args()
    with args.elf.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != ELF_HASH:
            raise ValueError("Unexpected ELF")
        stream.seek(0)
        elf = ELFFile(stream)
        symbols = elf.get_section_by_name(".symtab").get_symbol_by_name(SYMBOL)
        if [tuple(sym[k] for k in ("st_value", "st_size", "st_shndx"))
            for sym in symbols] != [(ADDRESS, 16, 12)]:
            raise ValueError("Unexpected symbol range")
        section = elf.get_section(12)
        offset = ADDRESS - section["sh_addr"]
        if section.name != ".text" or not 0 <= offset <= section["sh_size"] - 16:
            raise ValueError("Unexpected section range")
        body = section.data()[offset:offset + 16]
        if hashlib.sha256(body).hexdigest() != BODY_HASH:
            raise ValueError("Unexpected original body")
    cases = [observe(body, i * 2 + j, 0x200000 + 0x1000 * i,
                     0x202000 + 0x1000 * j, word)
             for i in range(2)
             for j, word in enumerate((0x10203040, 0xfedcba98))]
    receipt = {"elf_sha256": ELF_HASH, "range_sha256": BODY_HASH,
               "file_offset": section["sh_offset"] + offset,
               "mangled": SYMBOL, "section": 12, "address": ADDRESS,
               "size": 16, "unicorn": __version__, "cases": cases}
    result = json.dumps(receipt, indent=2) + "\n"
    if args.verify:
        if result != args.verify.read_text():
            raise ValueError("Fresh ARM observations differ")
        print(f"Verified {len(cases)} original ARM executions")
    else:
        print(result, end="")


if __name__ == "__main__":
    main()
