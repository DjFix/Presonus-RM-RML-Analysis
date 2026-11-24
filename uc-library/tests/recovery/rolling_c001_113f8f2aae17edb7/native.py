"""Execute only the original ARM callback and record its register/memory effects."""
import argparse
import hashlib
import io
import json
from pathlib import Path

from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import arm_const

ELF_SHA = "9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07"
BODY_SHA = "60cf0e8b51daf6a0ce5a5eea619d9a3e219bccf7fa26c553983e5baf3012cfad"
SYMBOL = "_ZN8Presonus5Mixer17AVBCascadeManager21onNetworkItemAcquiredEPNS_2UC11NetworkItemE"
ADDRESS, SIZE, SECTION, OFFSET = 0x5E9FC, 16, 12, 0x569FC
RECEIVER, ARGUMENT, STACK, RETURN = 0x300000, 0x301000, 0x401000, 0x500000


def require(condition, message):
    if not condition:
        raise ValueError(message)


def observe(body, argument, pattern):
    uc = unicorn.Uc(unicorn.UC_ARCH_ARM, unicorn.UC_MODE_ARM)
    uc.mem_map(ADDRESS & ~0xFFF, 4096)
    uc.mem_write(ADDRESS, body)
    uc.mem_map(RECEIVER, 8192)
    uc.mem_map(STACK - 4096, 4096)
    initial = bytes((i + pattern) & 0xFF for i in range(8192))
    uc.mem_write(RECEIVER, initial)
    registers = [getattr(arm_const, f"UC_ARM_REG_R{i}") for i in range(12)]
    values = [RECEIVER, argument] + [0x12345600 + i for i in range(2, 12)]
    for register, value in zip(registers, values):
        uc.reg_write(register, value)
    uc.reg_write(arm_const.UC_ARM_REG_SP, STACK)
    uc.reg_write(arm_const.UC_ARM_REG_LR, RETURN)
    reads = []
    writes = []
    instructions = []
    uc.hook_add(unicorn.UC_HOOK_MEM_READ,
                lambda uc, access, address, size, value, data: reads.append([address, size]))
    uc.hook_add(unicorn.UC_HOOK_MEM_WRITE,
                lambda uc, access, address, size, value, data: writes.append([address, size]))
    uc.hook_add(unicorn.UC_HOOK_CODE,
                lambda uc, address, size, data: instructions.append(address))
    uc.emu_start(ADDRESS, RETURN, count=8)
    preserved = [uc.reg_read(reg) for reg in registers] == values
    restored = uc.reg_read(arm_const.UC_ARM_REG_SP) == STACK
    returned = uc.reg_read(arm_const.UC_ARM_REG_PC) == RETURN
    untouched = uc.mem_read(RECEIVER, len(initial)) == initial
    require(instructions == list(range(ADDRESS, ADDRESS + SIZE, 4)), "unexpected native execution")
    require(preserved and restored and returned and untouched, "unexpected native state")
    require(len(writes) == 4 and all(STACK - 16 <= addr < addr + size <= STACK
                                    for addr, size in writes), "unexpected writes")
    require(reads and all(STACK - 16 <= addr < addr + size <= STACK
                          for addr, size in reads), "unexpected non-stack reads")
    return {"reads": reads, "arg": argument, "pattern": pattern, "state_unchanged": untouched,
            "registers_preserved_r0_r11": preserved, "stack_restored": restored,
            "returned": returned, "writes": writes, "instructions": instructions}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--elf", type=Path, required=True)
    parser.add_argument("mode", choices=("record", "verify"))
    parser.add_argument("--fixtures", type=Path, required=True)
    args = parser.parse_args()
    data = args.elf.read_bytes()
    require(hashlib.sha256(data).hexdigest() == ELF_SHA, "ELF hash mismatch")
    elf = ELFFile(io.BytesIO(data))
    symtab = elf.get_section_by_name(".symtab")
    symbols = symtab.get_symbol_by_name(SYMBOL)
    require(len(symbols) == 1, "missing or ambiguous exact symbol")
    sym = symbols[0]
    section = elf.get_section(SECTION)
    require((sym["st_value"], sym["st_size"], sym["st_shndx"], sym["st_info"]["type"])
            == (ADDRESS, SIZE, SECTION, "STT_FUNC"), "symbol range mismatch")
    offset = ADDRESS - section["sh_addr"]
    require(section.name == ".text" and 0 <= offset <= section["sh_size"] - SIZE
            and section["sh_offset"] + offset == OFFSET, "unexpected section mapping")
    body = data[OFFSET:OFFSET + SIZE]
    require(hashlib.sha256(body).hexdigest() == BODY_SHA, "body hash mismatch")
    cases = [observe(body, ptr, i * 81) for i, ptr in
             enumerate((0, ARGUMENT, ARGUMENT + 64))]
    result = {"elf_sha256": ELF_SHA, "body_sha256": BODY_SHA, "mangled": SYMBOL,
              "address": ADDRESS, "size": SIZE, "section": SECTION, "offset": OFFSET,
              "engine": f"Unicorn {unicorn.__version__}", "cases": cases}
    if args.mode == "record":
        with args.fixtures.open("x") as stream:
            json.dump(result, stream, indent=2)
            stream.write("\n")
    else:
        require(json.loads(args.fixtures.read_text()) == result, "native replay mismatch")
    print(f"{len(cases)} original ARM cases")


if __name__ == "__main__":
    main()
