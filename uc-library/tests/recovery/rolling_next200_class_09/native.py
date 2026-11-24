"""Execute the original ARM callback in an isolated, offline emulator."""
import argparse
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path

from elftools.elf.elffile import ELFFile
import unicorn
from unicorn.arm_const import (
    UC_ARM_REG_CPSR, UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0,
    UC_ARM_REG_R1, UC_ARM_REG_R11, UC_ARM_REG_SP,
)

ELF_HASH = "9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07"
SYMBOL = "_ZN8Presonus5Mixer21NetworkSetupComponent15onServerChangedEPNS_2UC11NetworkItemE"
ADDRESS, SIZE, SECTION = 0x1CF80, 16, 12


def observe(body, has_item, pattern):
    arm = unicorn.Uc(unicorn.UC_ARCH_ARM, unicorn.UC_MODE_ARM)
    arm.mem_map(ADDRESS & ~0xFFF, 0x1000)
    arm.mem_write(ADDRESS, body)
    arm.mem_protect(ADDRESS & ~0xFFF, 0x1000, unicorn.UC_PROT_READ | unicorn.UC_PROT_EXEC)

    stack, receiver, item = 0x200000, 0x300000, 0x301000
    arm.mem_map(stack, 0x1000)
    arm.mem_map(receiver, 0x2000)
    sentinel = bytes([pattern]) * 0x1000
    arm.mem_write(receiver, sentinel)
    arm.mem_write(item, sentinel[::-1])
    sp, fp, stop = stack + 0x800, 0x5AFE, ADDRESS + SIZE
    arg = item if has_item else 0
    arm.reg_write(UC_ARM_REG_CPSR, 0x13)
    for register, value in ((UC_ARM_REG_R0, receiver), (UC_ARM_REG_R1, arg),
                            (UC_ARM_REG_R11, fp), (UC_ARM_REG_LR, stop),
                            (UC_ARM_REG_SP, sp)):
        arm.reg_write(register, value)

    executed, accesses = [], []
    arm.hook_add(unicorn.UC_HOOK_CODE,
                 lambda _, addr, size, user: executed.append(addr))
    arm.hook_add(unicorn.UC_HOOK_MEM_READ | unicorn.UC_HOOK_MEM_WRITE,
                 lambda _, access, addr, size, value, user:
                 accesses.append((access, addr, size)))
    arm.emu_start(ADDRESS, stop, count=8)
    assert arm.reg_read(UC_ARM_REG_PC) == stop
    assert executed == list(range(ADDRESS, stop, 4))
    assert all(sp - 16 <= addr and addr + size <= sp
               for _, addr, size in accesses)
    assert arm.reg_read(UC_ARM_REG_SP) == sp
    assert arm.reg_read(UC_ARM_REG_R11) == fp
    assert arm.reg_read(UC_ARM_REG_R0) == receiver
    assert arm.reg_read(UC_ARM_REG_R1) == arg
    return {
        "has_item": has_item, "sentinel_pattern": pattern,
        "receiver_unchanged": bytes(arm.mem_read(receiver, 0x1000)) == sentinel,
        "item_unchanged": bytes(arm.mem_read(item, 0x1000)) == sentinel[::-1],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--elf", type=Path, required=True)
    output = parser.add_mutually_exclusive_group(required=True)
    output.add_argument("--out", type=Path)
    output.add_argument("--verify", type=Path)
    args = parser.parse_args()
    image = args.elf.read_bytes()
    assert sha256(image).hexdigest() == ELF_HASH
    elf = ELFFile(BytesIO(image))
    symbols = elf.get_section_by_name(".symtab").get_symbol_by_name(SYMBOL)
    assert len(symbols) == 1
    symbol = symbols[0]
    assert (symbol["st_value"], symbol["st_size"], symbol["st_shndx"]) == (
        ADDRESS, SIZE, SECTION)
    section = elf.get_section(SECTION)
    delta = ADDRESS - section["sh_addr"]
    assert section["sh_type"] == "SHT_PROGBITS"
    assert 0 <= delta <= section["sh_size"] - SIZE
    offset = section["sh_offset"] + delta
    body = image[offset:offset + SIZE]
    receipt = {
        "elf_sha256": ELF_HASH, "mangled": SYMBOL, "address": ADDRESS,
        "size": SIZE, "section": SECTION, "file_offset": offset,
        "range_sha256": sha256(body).hexdigest(),
        "native_engine": f"Unicorn {unicorn.__version__}",
        "cases": [observe(body, False, 0x42), observe(body, True, 0x83)],
    }
    if args.out:
        args.out.write_text(json.dumps(receipt, indent=2) + "\n")
    else:
        assert receipt == json.loads(args.verify.read_text())
        print(f"Original ARM replay verified {len(receipt['cases'])} cases")


if __name__ == "__main__":
    main()
