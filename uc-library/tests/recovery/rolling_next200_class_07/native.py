"""Replay the sealed ARM close body in isolation and verify its observations."""
import argparse
import hashlib
import json
from pathlib import Path

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import (
    UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3,
    UC_ARM_REG_SP, UC_ARM_REG_FP, UC_ARM_REG_LR, UC_ARM_REG_PC,
)
import unicorn

ELF_SHA = "9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07"
BODY_SHA = "60cf0e8b51daf6a0ce5a5eea619d9a3e219bccf7fa26c553983e5baf3012cfad"
MANGLED = "_ZN8Presonus5Panel16SharedMemoryComm5closeEv"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def observe(path):
    require(hashlib.sha256(path.read_bytes()).hexdigest() == ELF_SHA, "ELF hash mismatch")
    with path.open("rb") as handle:
        elf = ELFFile(handle)
        symbol, = elf.get_section_by_name(".symtab").get_symbol_by_name(MANGLED)
        addr, size, section_id = (symbol[key] for key in ("st_value", "st_size", "st_shndx"))
        require((addr, size, section_id) == (0x95380, 16, 12), "Symbol identity mismatch")
        section = elf.get_section(section_id)
        delta = addr - section["sh_addr"]
        offset = section["sh_offset"] + delta
        require(section.name == ".text" and offset == 0x8D380, "ELF mapping mismatch")
        body = section.data()[delta:delta + size]
        require(hashlib.sha256(body).hexdigest() == BODY_SHA, "Original body mismatch")

    cases = []
    for fill, receiver, stack_top, frame in (
        (0x35, 0x2020, 0x4800, 0x4888),
        (0xC2, 0x2180, 0x4C00, 0x4C98),
    ):
        machine = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        for page in (0x2000, 0x4000, addr & ~0xFFF):
            machine.mem_map(page, 0x1000)
        machine.mem_write(addr, body)
        sentinel = bytes([fill]) * 4096
        machine.mem_write(0x2000, sentinel)
        machine.mem_write(0x4000, sentinel)
        stop = addr + 0x100
        incoming = {
            UC_ARM_REG_R0: receiver, UC_ARM_REG_R1: 0x2030,
            UC_ARM_REG_R2: 0x2090, UC_ARM_REG_R3: fill,
            UC_ARM_REG_FP: frame, UC_ARM_REG_SP: stack_top, UC_ARM_REG_LR: stop,
        }
        for register, value in incoming.items():
            machine.reg_write(register, value)
        writes = []
        trace = []
        machine.hook_add(UC_HOOK_MEM_WRITE, lambda _, access, at, size, value, __:
                         writes.append([at, size, value]))
        machine.hook_add(UC_HOOK_CODE, lambda _, at, size, __: trace.append([at, size]))
        machine.emu_start(addr, stop, count=8)
        require(machine.reg_read(UC_ARM_REG_PC) == stop, "Return branch mismatch")
        require(all(machine.reg_read(reg) == value for reg, value in incoming.items()),
                "Receiver, arguments or saved frame registers changed")
        require(trace == [[address, 4] for address in range(addr, addr + size, 4)],
                "Unexpected execution trace")
        require(len(writes) == 4 and
                {at for at, _, _ in writes} == set(range(stack_top - 16, stack_top, 4)) and
                all(width == 4 for _, width, _ in writes), "Unexpected stack writes")
        unchanged = machine.mem_read(0x2000, len(sentinel)) == sentinel
        require(unchanged, "Receiver page changed")
        stack = machine.mem_read(0x4000, len(sentinel))
        start, end = stack_top - 16 - 0x4000, stack_top - 0x4000
        require(stack[:start] == sentinel[:start] and stack[end:] == sentinel[end:],
                "Stack sentinel changed outside frame")
        cases.append({"fill": fill, "receiver": receiver, "entry_sp": stack_top,
                      "entry_fp": frame, "preserved_incoming_registers": True,
                      "receiver_unchanged": unchanged, "stack_writes": writes,
                      "trace": trace})
    return {"elf_sha256": ELF_SHA, "body_sha256": BODY_SHA, "mangled": MANGLED,
            "address": addr, "size": size, "section": section_id, "file_offset": offset,
            "unicorn_version": unicorn.__version__, "cases": cases}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--elf", type=Path, required=True)
    parser.add_argument("--fixtures", type=Path)
    args = parser.parse_args()
    observations = observe(args.elf)
    if args.fixtures is not None:
        require(observations == json.loads(args.fixtures.read_text()), "Native fixture mismatch")
    print(json.dumps(observations, indent=2))


if __name__ == "__main__":
    main()
