"""Execute the exact RM/RML ARM meter hook offline from its frozen ELF."""
import argparse
import hashlib
import io
import json
from pathlib import Path

import elftools
import unicorn
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UC_MODE_ARM
from unicorn.arm_const import (
    UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_FP, UC_ARM_REG_SP,
    UC_ARM_REG_LR, UC_ARM_REG_PC,
)

IDENTITY = {
    "elf_sha256": "9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07",
    "firmware": "RM/RML mixer 13731",
    "role": "server",
    "mangled": "_ZN8Presonus5Panel19FrontPanelComponent16doFatMeterUpdateERNS_5Mixer16ChannelComponentE",
    "address": 0x69D0C,
    "size": 16,
    "section": 12,
}
RANGE_SHA256 = "60cf0e8b51daf6a0ce5a5eea619d9a3e219bccf7fa26c553983e5baf3012cfad"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def run_case(address, code, name, receiver, channel, sp, fp, seed):
    arm = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    arm.mem_map(address & ~0xFFF, 0x1000)
    arm.mem_write(address, code)
    sentinel = 0x300000
    arm.mem_map(sentinel, 0x1000)
    for ptr in (receiver, channel, sp):
        arm.mem_map(ptr & ~0xFFF, 0x1000)
    receiver_bytes = bytes((i + seed) % 256 for i in range(512))
    channel_bytes = bytes((i ^ seed) % 256 for i in range(512))
    arm.mem_write(receiver, receiver_bytes)
    arm.mem_write(channel, channel_bytes)
    registers = {
        UC_ARM_REG_R0: receiver,
        UC_ARM_REG_R1: channel,
        UC_ARM_REG_FP: fp,
        UC_ARM_REG_SP: sp,
        UC_ARM_REG_LR: sentinel,
    }
    for register, value in registers.items():
        arm.reg_write(register, value)
    instruction_trace = []
    writes = []
    arm.hook_add(UC_HOOK_CODE, lambda _, pc, size, userdata: instruction_trace.append(pc))
    arm.hook_add(
        UC_HOOK_MEM_WRITE,
        lambda _, access, ptr, size, value, userdata: writes.append([ptr, size, value]),
    )
    arm.emu_start(address, sentinel, count=8)
    assert arm.reg_read(UC_ARM_REG_PC) == sentinel
    assert all(arm.reg_read(reg) == value for reg, value in registers.items())
    assert instruction_trace == list(range(address, address + len(code), 4))
    assert sorted(writes) == [
        [sp - 16, 4, fp], [sp - 12, 4, sp],
        [sp - 8, 4, sentinel], [sp - 4, 4, address + 12],
    ]
    unchanged = (
        bytes(arm.mem_read(receiver, len(receiver_bytes))) == receiver_bytes
        and bytes(arm.mem_read(channel, len(channel_bytes))) == channel_bytes
    )
    assert unchanged
    return {
        "name": name, "receiver": receiver, "channel": channel, "stack": sp,
        "frame": fp, "seed": seed, "receiver_sha256": digest(receiver_bytes),
        "channel_sha256": digest(channel_bytes), "return_pc": sentinel,
        "restored_registers": ["r0", "r1", "fp", "sp", "lr"],
        "instruction_trace": instruction_trace, "writes": writes,
        "external_calls": [], "objects_unchanged": unchanged,
    }


def observe(path):
    data = path.read_bytes()
    assert digest(data) == IDENTITY["elf_sha256"]
    elf = ELFFile(io.BytesIO(data))
    assert elf.little_endian and elf.elfclass == 32 and elf["e_machine"] == "EM_ARM"
    symbol, = elf.get_section_by_name(".symtab").get_symbol_by_name(IDENTITY["mangled"])
    address, size, index = (IDENTITY[key] for key in ("address", "size", "section"))
    assert (symbol["st_value"], symbol["st_size"], symbol["st_shndx"]) == (address, size, index)
    assert symbol["st_info"]["type"] == "STT_FUNC"
    section = elf.get_section(index)
    displacement = address - section["sh_addr"]
    assert section.name == ".text" and section["sh_flags"] & 4
    assert 0 <= displacement <= displacement + size <= section["sh_size"]
    offset = section["sh_offset"] + displacement
    assert offset == 0x61D0C
    code = data[offset:offset + size]
    assert digest(code) == RANGE_SHA256
    cases = [
        run_case(address, code, "idle", 0x100040, 0x110080, 0x200FF0, 0x12340, 0),
        run_case(address, code, "active", 0x120080, 0x130040, 0x210FC0, 0x7330, 165),
    ]
    return {
        "original": IDENTITY | {
            "file_offset": offset, "section_name": section.name,
            "range_sha256": RANGE_SHA256, "range_hex": code.hex(),
        },
        "unicorn_version": unicorn.__version__,
        "pyelftools_version": elftools.__version__,
        "cases": cases,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--elf", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = observe(args.elf)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(f"Executed {len(result['cases'])} native ARM cases")


if __name__ == "__main__":
    main()
