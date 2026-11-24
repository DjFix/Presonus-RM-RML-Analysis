"""Execute the exact original ARM symbol offline using synthetic mapped memory."""

import argparse
import hashlib
import io
import json
from pathlib import Path

from elftools.elf.elffile import ELFFile
from unicorn import UC_ARCH_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UC_MODE_ARM, Uc
from unicorn.arm_const import (
    UC_ARM_REG_FP,
    UC_ARM_REG_LR,
    UC_ARM_REG_PC,
    UC_ARM_REG_R0,
    UC_ARM_REG_R1,
    UC_ARM_REG_SP,
)

ELF = Path(
    "/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/"
    "rolling-c001-20261124/packeting/first10/snapshot/"
    "rootfs/RML16AI_Rack_13731/home/root/mixer"
)
SHA = "9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07"
NAME = "_ZN8Presonus3AVB12AvbComponent23handleTalkerStateChangeEPNS0_9AvbTalkerE"
ADDRESS = 0xA853C
SIZE = 16
SECTION = 12
OFFSET = 0xA053C
RANGE_SHA = "60cf0e8b51daf6a0ce5a5eea619d9a3e219bccf7fa26c553983e5baf3012cfad"


def read_original():
    data = ELF.read_bytes()
    assert hashlib.sha256(data).hexdigest() == SHA
    elf = ELFFile(io.BytesIO(data))
    assert elf.header.e_machine == "EM_ARM" and elf.little_endian
    matches = elf.get_section_by_name(".symtab").get_symbol_by_name(NAME)
    assert len(matches) == 1
    symbol = matches[0]
    assert (symbol["st_value"], symbol["st_size"], symbol["st_shndx"]) == (
        ADDRESS, SIZE, SECTION
    )
    assert symbol["st_info"]["type"] == "STT_FUNC"
    section = elf.get_section(SECTION)
    assert section.name == ".text" and section["sh_type"] == "SHT_PROGBITS"
    displacement = ADDRESS - section["sh_addr"]
    assert 0 <= displacement <= section["sh_size"] - SIZE
    assert section["sh_offset"] + displacement == OFFSET
    assert any(
        segment["p_type"] == "PT_LOAD"
        and segment["p_flags"] & 1
        and segment["p_vaddr"] <= ADDRESS
        and ADDRESS + SIZE <= segment["p_vaddr"] + segment["p_filesz"]
        and segment["p_offset"] + ADDRESS - segment["p_vaddr"] == OFFSET
        for segment in elf.iter_segments()
    )
    code = data[OFFSET:OFFSET + SIZE]
    assert hashlib.sha256(code).hexdigest() == RANGE_SHA
    return code


def observe(code, seed, present):
    machine = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    receiver = 0x100000 + seed * 8
    talker = 0x110000 + seed * 8
    stack = 0x120800 - seed
    stack &= ~7
    stop = 0x130000
    for address in (ADDRESS & ~0xFFF, 0x100000, 0x110000, 0x120000, stop):
        machine.mem_map(address, 0x1000)
    machine.mem_write(ADDRESS, code)
    receiver_page = bytes((seed + i) % 256 for i in range(4096))
    talker_page = receiver_page[::-1]
    stack_page = bytes([0xC2]) * 4096
    for address, data in (
        (0x100000, receiver_page),
        (0x110000, talker_page),
        (0x120000, stack_page),
    ):
        machine.mem_write(address, data)
    regs = {
        UC_ARM_REG_R0: receiver,
        UC_ARM_REG_R1: talker if present else 0,
        UC_ARM_REG_SP: stack,
        UC_ARM_REG_FP: 0x120950 + seed * 4,
        UC_ARM_REG_LR: stop,
    }
    for register, value in regs.items():
        machine.reg_write(register, value)

    trace = []
    writes = []
    machine.hook_add(UC_HOOK_CODE, lambda _, address, size, __: trace.append([address, size]))
    machine.hook_add(
        UC_HOOK_MEM_WRITE,
        lambda _, __, address, size, value, ___: writes.append([address, size, value]),
    )
    machine.emu_start(ADDRESS, stop, count=8)
    assert machine.reg_read(UC_ARM_REG_PC) == stop
    assert all(machine.reg_read(register) == value for register, value in regs.items())
    assert trace == [[address, 4] for address in range(ADDRESS, ADDRESS + SIZE, 4)]
    assert sorted((address, size) for address, size, _ in writes) == [
        (address, 4) for address in range(stack - 16, stack, 4)
    ]
    assert bytes(machine.mem_read(0x120000, stack - 16 - 0x120000)) == stack_page[:stack - 16 - 0x120000]
    assert bytes(machine.mem_read(stack, 0x121000 - stack)) == stack_page[stack - 0x120000:]
    return {
        "seed": seed,
        "present": present,
        "receiver_unchanged": bytes(machine.mem_read(0x100000, 4096)) == receiver_page,
        "talker_unchanged": bytes(machine.mem_read(0x110000, 4096)) == talker_page,
        "receiver_register": machine.reg_read(UC_ARM_REG_R0),
        "argument_register": machine.reg_read(UC_ARM_REG_R1),
        "stack_pointer": machine.reg_read(UC_ARM_REG_SP),
        "frame_pointer": machine.reg_read(UC_ARM_REG_FP),
        "return_pc": machine.reg_read(UC_ARM_REG_PC),
        "instruction_trace": trace,
        "stack_writes": writes,
    }


def generate():
    code = read_original()
    cases = [
        observe(code, seed, present)
        for seed in (0, 1, 17, 63, 127, 240)
        for present in (0, 1)
    ]
    assert all(case["receiver_unchanged"] and case["talker_unchanged"] for case in cases)
    return {
        "range": {
            "elf_path": str(ELF),
            "elf_sha256": SHA,
            "firmware": "RM/RML mixer 13731",
            "role": "server",
            "mangled": NAME,
            "address": ADDRESS,
            "size": SIZE,
            "section": ".text",
            "section_index": SECTION,
            "file_offset": OFFSET,
            "range_sha256": RANGE_SHA,
        },
        "cases": cases,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--verify", type=Path)
    group.add_argument("--write", type=Path)
    args = parser.parse_args()
    observed = generate()
    if args.write:
        with args.write.open("x") as output:
            output.write(json.dumps(observed, indent=2) + "\n")
    else:
        assert json.loads(args.verify.read_text()) == observed, "Original replay differs"
    print(f"{len(observed['cases'])} fresh original ARM executions passed")


if __name__ == "__main__":
    main()
