"""Replay one exact ARM destructor range offline against guarded synthetic state."""
import argparse
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
from struct import pack

from elftools.elf.elffile import ELFFile
from unicorn import UC_ARCH_ARM, UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE
from unicorn import UC_MODE_ARM, UC_PROT_EXEC, UC_PROT_READ, Uc, __version__
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0
from unicorn.arm_const import UC_ARM_REG_SP, UC_ARM_REG_R11

RANGE_HASH = "60cf0e8b51daf6a0ce5a5eea619d9a3e219bccf7fa26c553983e5baf3012cfad"


def observe(body, address, borrowed, identity):
    machine = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    code_page = address & ~0xfff
    machine.mem_map(code_page, 4096, UC_PROT_READ | UC_PROT_EXEC)
    machine.mem_write(address, body)
    receiver, pointee, stack, end = 0x10000100, 0x10001100, 0x10002800, 0x10003000
    machine.mem_map(0x10000000, 0x3000)
    # These bytes exercise non-interference. No native field offset is assumed.
    receiver_region = b"leading!" + pack("<I", pointee if borrowed else 0)
    receiver_region += identity.encode("ascii").ljust(128, b"\0") + b"trailing"
    pointee_region = b"borrowed-pointee-canary"
    machine.mem_write(receiver - 8, receiver_region)
    machine.mem_write(pointee, pointee_region)
    machine.reg_write(UC_ARM_REG_R0, receiver)
    machine.reg_write(UC_ARM_REG_SP, stack)
    machine.reg_write(UC_ARM_REG_R11, 0xfefe)
    machine.reg_write(UC_ARM_REG_LR, end)
    call_trace, reads, writes = [], [], []
    machine.hook_add(UC_HOOK_CODE, lambda uc, pc, size, data: call_trace.append(pc))
    machine.hook_add(UC_HOOK_MEM_READ, lambda uc, access, at, size, val, data: reads.append([at, size]))
    machine.hook_add(UC_HOOK_MEM_WRITE, lambda uc, access, at, size, val, data: writes.append([at, size]))
    machine.emu_start(address, end, count=12)

    result = {
        "returned": machine.reg_read(UC_ARM_REG_PC) == end,
        "receiver_unchanged": machine.mem_read(receiver - 8, len(receiver_region)) == receiver_region,
        "pointee_unchanged": machine.mem_read(pointee, len(pointee_region)) == pointee_region,
        "frame_restored": machine.reg_read(UC_ARM_REG_SP) == stack and machine.reg_read(UC_ARM_REG_R11) == 0xfefe,
        "frame_only": all(stack - 16 <= at and at + size <= stack for at, size in reads + writes),
        "executed_only_original_frame": call_trace == list(range(address, address + len(body), 4)),
    }
    if not all(result.values()):
        raise ValueError(f"Unexpected ARM behavior: {result}")
    return {
        "borrowed": borrowed,
        "identity": identity,
        "observation": result,
        "trace": {"instruction_addresses": call_trace, "reads": reads, "writes": writes},
    }


def capture(path, original):
    data = path.read_bytes()
    if sha256(data).hexdigest() != original["elf_sha256"]:
        raise ValueError("Original ELF hash mismatch")
    elf = ELFFile(BytesIO(data))
    if elf["e_machine"] != "EM_ARM" or elf.elfclass != 32 or not elf.little_endian:
        raise ValueError("Expected little-endian ARM32 ELF")
    symbols = elf.get_section_by_name(".symtab").get_symbol_by_name(original["mangled"])
    if len(symbols) != 1:
        raise ValueError("Expected a unique ELF symbol table entry")
    symbol = symbols[0].entry
    address, size, section_index = (
        original[key] for key in ("address", "size", "section")
    )
    if (symbol.st_value, symbol.st_size, symbol.st_shndx) != (address, size, section_index):
        raise ValueError("ELF symbol table identity mismatch")
    section = elf.get_section(section_index)
    delta = address - section["sh_addr"]
    if section.name != ".text" or delta < 0 or delta + size > section["sh_size"]:
        raise ValueError("Original symbol lies outside the expected section")
    offset = section["sh_offset"] + delta
    body = data[offset : offset + size]
    if sha256(body).hexdigest() != RANGE_HASH:
        raise ValueError("Bound ARM symbol bytes differ")
    return {
        "original": original,
        "range": {"section": section.name, "file_offset": offset, "sha256": RANGE_HASH},
        "unicorn_version": __version__,
        "cases": [
            observe(body, address, borrowed, identity)
            for borrowed in (False, True)
            for identity in ("surface", "rm-" * 36)
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--elf", type=Path, required=True)
    parser.add_argument("--fixture", type=Path, required=True)
    args = parser.parse_args()
    expected = json.loads(args.fixture.read_text())
    if capture(args.elf, expected["original"]) != expected:
        parser.exit(1, "Fresh native observations differ from sealed fixture\n")
    print(f"Verified {len(expected['cases'])} offline ARM cases for {expected['original']['mangled']}")


if __name__ == "__main__":
    main()
