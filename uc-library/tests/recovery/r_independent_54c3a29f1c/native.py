"""Execute the two original ARM symbol ranges over isolated UART records."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from elftools.elf.elffile import ELFFile
import unicorn
from unicorn.arm_const import (
    UC_ARM_REG_CPSR, UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0,
    UC_ARM_REG_R1, UC_ARM_REG_SP,
)

SYMBOL = "_ZN8Presonus15TouchInputEvent7fromMsgER16Touchscreen_Type"
RANGE_SHA = "91e1e5211cf06fa0441704bc42b9dac0bf60cb2c85be6a3fdaf100f093bfd462"
TARGETS = (
    ("304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0",
     "CS18AI surface 13840", "client", 0x13980, 0xb980),
    ("9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07",
     "RM/RML mixer 13731", "server", 0x8d480, 0x85480),
)


def require(condition, description):
    if not condition:
        raise ValueError(description)


def observe(path, target):
    digest, firmware, role, address, offset = target
    require(hashlib.sha256(path.read_bytes()).hexdigest() == digest, "ELF digest")
    with path.open("rb") as stream:
        elf = ELFFile(stream)
        symtab = elf.get_section_by_name(".symtab")
        matches = symtab.get_symbol_by_name(SYMBOL)
        require(len(matches) == 1, "Original symbol multiplicity")
        symbol = matches[0]
        size = symbol["st_size"]
        section_index = symbol["st_shndx"]
        require((symbol["st_value"], size, section_index) == (address, 116, 12),
                "Original ELF symbol range")
        section = elf.get_section(section_index)
        relative = address - section["sh_addr"]
        require(section.name == ".text" and 0 <= relative <= section["sh_size"] - size
                and section["sh_offset"] + relative == offset, "Actual section mapping")
        code = section.data()[relative:relative + size]
        require(hashlib.sha256(code).hexdigest() == RANGE_SHA, "Range digest")

    vm = unicorn.Uc(unicorn.UC_ARCH_ARM, unicorn.UC_MODE_ARM)
    vm.mem_map(address & ~0xfff, 0x1000)
    vm.mem_write(address, code)
    data, stop = 0x100000, 0x200000
    vm.mem_map(data, 0x1000)
    vm.mem_map(stop, 0x1000)
    output, message, stack = data + 0x104, data + 0x204, data + 0x800
    canary = b"\xa5\xb6\xc7\xd8"
    accesses = []
    vm.hook_add(unicorn.UC_HOOK_MEM_READ | unicorn.UC_HOOK_MEM_WRITE,
                lambda _vm, action, ptr, length, _value, _data:
                    accesses.append((action, ptr, length)))
    cases = []
    for packed in range(256):
        for tag in (0x55, 0x7a, 0x54, packed):
            frame = bytes((tag, (17 * packed + tag) % 256,
                           (29 * packed - tag) % 256, packed))
            vm.mem_write(output - 4, canary + bytes([0xe1]) * 16 + canary)
            vm.mem_write(message - 4, canary + frame + canary)
            vm.reg_write(UC_ARM_REG_CPSR, 0x10)
            for reg, value in ((UC_ARM_REG_R0, output), (UC_ARM_REG_R1, message),
                               (UC_ARM_REG_SP, stack), (UC_ARM_REG_LR, stop)):
                vm.reg_write(reg, value)
            accesses.clear()
            vm.emu_start(address, stop, count=64)
            require(vm.reg_read(UC_ARM_REG_PC) == stop and
                    vm.reg_read(UC_ARM_REG_SP) == stack, "Native return/stack")
            require(vm.mem_read(message - 4, 12) == canary + frame + canary,
                    "Native input and sentinels")
            received = vm.mem_read(output - 4, 24)
            require(received[:4] == received[-4:] == canary, "Native receiver sentinels")
            writes = []
            reads = set()
            for action, ptr, length in accesses:
                if stack - 16 <= ptr <= stack - length:
                    continue
                if action == unicorn.UC_MEM_READ and length == 1:
                    reads.add(ptr - message)
                elif action == unicorn.UC_MEM_WRITE and length == 4:
                    writes.append(ptr - output)
                else:
                    raise ValueError("Unexpected native memory access")
            require(reads == {0, 1, 2, 3} and writes == [4, 8, 12, 0],
                    "Native input and receiver footprints")
            cases.append([list(frame), list(struct.unpack("<4I", received[4:-4]))])
    return {
        "elf_sha256": digest, "firmware": firmware, "role": role, "mangled": SYMBOL,
        "address": address, "size": size, "section": section_index,
        "section_name": ".text", "file_offset": offset, "range_sha256": RANGE_SHA,
        "cases": cases,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--elf", type=Path, action="append", required=True)
    parser.add_argument("--verify", type=Path)
    args = parser.parse_args()
    originals = [observe(path, target) for path, target in zip(args.elf, TARGETS, strict=True)]
    observations = {"unicorn": unicorn.__version__, "originals": originals}
    if args.verify:
        require(observations == json.loads(args.verify.read_text()), "Native replay mismatch")
        print(f"Verified {sum(len(row['cases']) for row in originals)} original executions")
    else:
        print(json.dumps(observations, separators=(",", ":")))


if __name__ == "__main__":
    main()
